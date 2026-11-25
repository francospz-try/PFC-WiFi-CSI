"""Evalúa las sesiones separadas de soporte y consulta del piloto ESP32-C6."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.pfc07.csi_piloto import leer_captura
from src.pfc07.csi_reconocimiento import MODES, actividad, features, infer


CLASES = MODES['binario']
ROLES = {'soporte': 'aprender', 'consulta': 'reconocer'}
DECLARADAS = {'quietud': 'investigador_sentado_inmovil', 'caminar': 'investigador_caminar_tramo_lateral'}
PATRON = re.compile(r'fs_(soporte|consulta)_(quietud|caminar)_([12])_\d{8}T\d{6}Z')
PESOS_ORIGEN = (('destino', 0), ('regularizado', 1))
PRESUPUESTOS = (1, 5, 10)
HASH_MODELO = '1834cd62268f8da966eb409975865827dfb9bae28279085209d3adba3f178cc7'
HASH_REPORTE = '8ba9ad618759cd90745824186fc09602a4ed4a27198127cedc34c9104b45fe51'


def huella(ruta):
    with ruta.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def cargar_sesion(ruta):
    match = PATRON.fullmatch(ruta.name)
    if not match:
        raise ValueError(f'Identificador de sesión inválido: {ruta.name}')
    rol, clase, repeticion = match.groups()
    meta = json.loads((ruta / 'metadata.json').read_text(encoding='utf-8'))
    esperado = {
        'dataset': 'fewshot_salon_20261125', 'status': 'completa', 'session': ruta.name,
        'capture_use': ROLES[rol], 'declared_activity': DECLARADAS[clase],
        'room': 'salon_10x8_ocupado', 'participant': 'P01', 'seconds': 60,
        'distance_m': 1.2, 'height_tx_m': 0.4, 'height_rx_m': 0.6,
    }
    if any(meta.get(k) != v for k, v in esperado.items()):
        raise ValueError(f'Metadatos inconsistentes en {ruta.name}')
    etiqueta_correcta = actividad(meta, 'binario') == clase if rol == 'soporte' else meta['label'] == 'sin_etiquetar'
    if not etiqueta_correcta or meta['quality']['channels'] != [11] or meta['quality']['value_lengths'] != [256]:
        raise ValueError(f'Etiqueta, canal o dimensiones inesperadas en {ruta.name}')
    if huella(ruta / 'raw.log') != meta['raw_sha256']:
        raise ValueError(f'SHA-256 de captura incorrecto en {ruta.name}')
    _, x = features(ruta)
    _, tiempo, _ = leer_captura(ruta)
    segundos = []
    for segundo in range(2, int(tiempo[-1]) - 2):
        muestras = tiempo[(tiempo >= segundo) & (tiempo < segundo + 1)]
        if len(muestras) >= 60 and np.max(np.diff(muestras)) <= .1:
            segundos.append(segundo)
    if len(segundos) != len(x):
        raise RuntimeError(f'Los intervalos y el extractor discrepan en {ruta.name}')
    return (rol, clase, int(repeticion)), meta, segundos, x


def ordenar_ventanas(segundos):
    pendientes = set(range(len(segundos)))
    primera = min(pendientes, key=lambda i: (abs(segundos[i] + .5 - 30), segundos[i]))
    orden = [primera]
    pendientes.remove(primera)
    while pendientes and len(orden) < 5:
        siguiente = max(pendientes, key=lambda i: (min(abs(segundos[i] - segundos[j]) for j in orden), -segundos[i]))
        orden.append(siguiente)
        pendientes.remove(siguiente)
    return orden


def centros_destino(soportes, k, primero, media, escala):
    centros, elegidas = [], []
    cuotas = ((k + 1) // 2, k // 2)
    for clase in CLASES:
        seleccionadas = []
        for numero, cuota in zip((primero, 3 - primero), cuotas):
            meta, segundos, x = soportes['soporte', clase, numero]
            orden = ordenar_ventanas(segundos)
            if len(orden) < cuota:
                return None, []
            for i in orden[:cuota]:
                seleccionadas.append(x[i])
                elegidas.append(dict(clase=clase, sesion=meta['session'], inicio_s=segundos[i]))
        centros.append(((np.asarray(seleccionadas) - media) / escala).mean(axis=0))
    return np.asarray(centros), elegidas


def metricas(matriz):
    def dividir(a, b):
        return a / b if b else 0.0

    por_clase = {}
    for i, clase in enumerate(CLASES):
        tp = int(matriz[i, i])
        precision = dividir(tp, int(matriz[:, i].sum()))
        recall = dividir(tp, int(matriz[i, :].sum()))
        por_clase[clase] = dict(precision=precision, recall=recall, f1=dividir(2 * precision * recall, precision + recall))
    return dict(confusion=matriz.tolist(), accuracy=dividir(int(matriz.trace()), int(matriz.sum())),
                macro_precision=sum(m['precision'] for m in por_clase.values()) / len(CLASES),
                macro_recall=sum(m['recall'] for m in por_clase.values()) / len(CLASES),
                macro_f1=sum(m['f1'] for m in por_clase.values()) / len(CLASES), por_clase=por_clase)


def evaluar(modelo, consultas, metodo, k, primero, csv_windows, csv_sessions):
    ventanas = np.zeros((len(CLASES), len(CLASES)), dtype=int)
    sesiones = np.zeros_like(ventanas)
    for (_, clase, _), (meta, segundos, x) in consultas.items():
        y = infer(x, modelo, CLASES)
        fila = CLASES.index(clase)
        votos = [int(np.count_nonzero(y == c)) for c in CLASES]
        ganador = int(np.argmax(votos))
        ventanas[fila, :] += votos
        sesiones[fila, ganador] += 1
        prefijo = [metodo, k, primero, meta['session'], clase]
        csv_windows.writerows([*prefijo, s, s + 1, p] for s, p in zip(segundos, y))
        csv_sessions.writerow([*prefijo, len(segundos), *votos, CLASES[ganador]])
    return {'ventanas': metricas(ventanas), 'sesiones': metricas(sesiones)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sesiones', nargs='+', type=Path)
    parser.add_argument('--check', action='store_true', help='Verifica calidad y huella, sin generar predicciones.')
    parser.add_argument('--modelo', type=Path, default=Path('outputs/validacion_fisica_20261125/modelo_historico'))
    parser.add_argument('--salida', type=Path, default=Path('outputs/fewshot_c6_20261125'))
    args = parser.parse_args()
    registros = {}
    for path in args.sesiones:
        slot, meta, segundos, x = cargar_sesion(path)
        if slot in registros:
            parser.error(f'Rol, clase y repetición duplicados: {slot}')
        registros[slot] = meta, segundos, x
        print(f'{meta["session"]}: {len(segundos)} ventanas elegibles; SHA-256 verificado', flush=True)
    if args.check:
        return
    slots = {(r, c, n) for r in ROLES for c in CLASES for n in (1, 2)}
    if set(registros) != slots or len({m['raw_sha256'] for m, _, _ in registros.values()}) != len(slots):
        parser.error('Se requieren ocho registros crudos distintos, dos por actividad y rol.')
    binario = args.modelo / 'binario.npz'
    reporte = args.modelo / 'binario.json'
    if huella(binario) != HASH_MODELO or huella(reporte) != HASH_REPORTE:
        parser.error('El modelo y su manifiesto deben coincidir con la copia congelada.')
    origen = json.loads(reporte.read_text(encoding='utf-8'))
    if tuple(origen['classes']) != CLASES or set(origen['sessions']) & {m['session'] for m, _, _ in registros.values()}:
        parser.error('Clases incompatibles o adquisición compartida con el modelo de origen.')
    with np.load(binario, allow_pickle=False) as z:
        media, escala, centros = (z[n] for n in ('mean', 'scale', 'centers'))
    consultas = {s: registros[s] for s in sorted(registros) if s[0] == 'consulta'}
    soportes = {s: registros[s] for s in sorted(registros) if s[0] == 'soporte'}
    args.salida.mkdir(parents=True, exist_ok=True)
    comparaciones, omitidos = [], []
    prefijo = ['metodo', 'k', 'primer_soporte', 'sesion', 'declarada']
    with (args.salida / 'predicciones_ventanas.csv').open('w', encoding='utf-8', newline='') as fw, \
            (args.salida / 'predicciones_sesiones.csv').open('w', encoding='utf-8', newline='') as fs:
        cw, cs = csv.writer(fw), csv.writer(fs)
        cw.writerow([*prefijo, 'inicio_s', 'fin_s', 'predicha'])
        cs.writerow([*prefijo, 'ventanas', *CLASES, 'predicha'])
        base = evaluar((media, escala, centros), consultas, 'historico', 0, 0, cw, cs)
        for k in PRESUPUESTOS:
            asignaciones = [centros_destino(soportes, k, n, media, escala) for n in (1, 2)]
            if any(destino is None for destino, _ in asignaciones):
                omitidos.append(k)
                continue
            for n, (destino, seleccion) in enumerate(asignaciones, start=1):
                for metodo, peso in PESOS_ORIGEN:
                    centro = (k * destino + peso * centros) / (k + peso)
                    resultado = evaluar((media, escala, centro), consultas, metodo, k, n, cw, cs)
                    cambio = {nivel: {m: resultado[nivel][m] - base[nivel][m] for m in ('accuracy', 'macro_f1')}
                              for nivel in base}
                    comparaciones.append(dict(k=k, primer_soporte=n, metodo=metodo, peso_origen=peso,
                                               soporte=seleccion, metricas=resultado, cambio_vs_historico=cambio))
    resumen = dict(clases=CLASES, modelo_sha256=HASH_MODELO, modelo_reporte_sha256=HASH_REPORTE,
                   adquisiciones=[dict(rol=s[0], clase=s[1], repeticion=s[2], sesion=m['session'],
                                       raw_sha256=m['raw_sha256'], calidad=m['quality'], ventanas=len(t))
                                   for s, (m, t, _) in sorted(registros.items())],
                   historico=base, comparaciones=comparaciones, presupuestos_omitidos=omitidos)
    (args.salida / 'evaluacion.json').write_text(json.dumps(resumen, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
