"""EvaluaciÃ³n cross-environment, soporte y consulta disjuntos."""
import csv
import json
import hashlib
import platform
import shutil
import uuid
from datetime import datetime, timezone
import joblib
import sklearn
from pathlib import Path
import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, confusion_matrix
from .config import CLASES, SHOT_VALUES
from .modelos import entrenar_base, prediccion_fewshot


def dividir_soporte_consulta(y, orden, clases=CLASES, max_shot=10, guardia=4,
                             minimo_consulta=5):
    """Reservar primeras ventanas de cada clase para soporte, luego purga y consulta.

    Ventanas son NO superpuestas; la separaciÃ³n no crea sesiones independientes.
    Para mayor rigor, usar grabaciones independientes, si estÃ¡n disponibles.
    """
    y, orden = np.asarray(y), np.asarray(orden)
    if len(y) != len(orden):
        raise ValueError('y y orden deben tener igual longitud')
    elegibles, consulta = {}, []
    for c in clases:
        idx = np.where(y == c)[0]
        idx = idx[np.argsort(orden[idx], kind='stable')]
        if len(idx) < max_shot + guardia + minimo_consulta:
            raise ValueError(f'Clase {c}: faltan ventanas para 10-shot + purga + consulta')
        elegibles[c] = idx[:max_shot].tolist()
        consulta.extend(idx[max_shot+guardia:].tolist())
    return elegibles, np.array(sorted(consulta), dtype=int)


def ejecutar_experimento(origen, destino, salida, semilla=42, shots=SHOT_VALUES,
                           etiqueta='DATOS_REALES_NO_AUDITADOS'):
    """Realiza evaluaciÃ³n verificando separaciÃ³n de ambientes y coincidencia de clases."""
    for datos in (origen, destino):
        for campo in ('X', 'y', 'orden', 'escenario', 'receptor'):
            if campo not in datos:
                raise ValueError(f'Falta campo {campo} en archivo de caracterÃ­sticas')
    if str(origen['escenario']) == str(destino['escenario']):
        raise ValueError('La evaluaciÃ³n cross-environment requiere ambientes diferentes')
    if str(origen['receptor']) != str(destino['receptor']):
        raise ValueError('Mantener receptor consistente entre ambientes')
    if not np.isfinite(origen['X']).all() or not np.isfinite(destino['X']).all():
        raise ValueError('CaracterÃ­sticas con NaN o Inf')
    if origen['X'].shape[1] != destino['X'].shape[1]:
        raise ValueError('Dimensiones de caracterÃ­sticas incompatibles')
    if set(origen['y']) != set(CLASES) or set(destino['y']) != set(CLASES):
        raise ValueError('Faltan clases A,B,C,G,K')
    escala, modelo = entrenar_base(origen['X'], origen['y'], semilla)
    soporte, indice_consulta = dividir_soporte_consulta(destino['y'], destino['orden'])
    sal = Path(salida)
    sal.mkdir(parents=True, exist_ok=True)
    if (sal / 'protocolo.json').exists():
        archivo = sal / 'historial' / uuid.uuid4().hex
        archivo.mkdir(parents=True)
        for anterior in sal.iterdir():
            if anterior.is_file():
                shutil.copy2(anterior, archivo / anterior.name)
    joblib.dump({'escalador': escala, 'modelo_base': modelo}, sal / 'modelo_base.joblib')
    Xq = destino['X'][indice_consulta]
    yq = destino['y'][indice_consulta]
    datos_metricas = []
    rng = np.random.default_rng(semilla)
    permutaciones = {c: rng.permutation(indices).tolist() for c, indices in soporte.items()}
    for k in shots:
        if k not in SHOT_VALUES:
            raise ValueError(f'Shot invÃ¡lido: {k}')
        if k:
            indices = [i for c in CLASES for i in permutaciones[c][:k]]
            yp = prediccion_fewshot(escala, modelo, Xq, destino['X'][indices], destino['y'][indices])
        else:
            indices = []
            yp = prediccion_fewshot(escala, modelo, Xq)
        fila = {
            'shots_por_clase': int(k),
            'accuracy': float(accuracy_score(yq, yp)),
            'precision_macro': float(precision_score(yq, yp, labels=CLASES, average='macro', zero_division=0)),
            'recall_macro': float(recall_score(yq, yp, labels=CLASES, average='macro', zero_division=0)),
            'f1_macro': float(f1_score(yq, yp, labels=CLASES, average='macro', zero_division=0)),
            'muestras_soporte': len(indices), 'muestras_consulta': len(yq)
        }
        datos_metricas.append(fila)
        with (sal / f'predicciones_{k}shot.csv').open('w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['indice_consulta', 'actividad_real', 'prediccion'])
            writer.writerows(zip(indice_consulta.tolist(), yq.tolist(), yp.tolist()))
        matriz = confusion_matrix(yq, yp, labels=CLASES)
        np.savetxt(sal / f'confusion_{k}shot.csv', matriz, delimiter=',', fmt='%d')
    with (sal / 'metricas.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(datos_metricas[0]))
        writer.writeheader()
        writer.writerows(datos_metricas)
    metadatos = {'id_ejecucion': uuid.uuid4().hex, 'fecha_utc': datetime.now(timezone.utc).isoformat(),
                 'versiones': {'python': platform.python_version(), 'numpy': np.__version__, 'sklearn': sklearn.__version__},
                 'sha256_caracteristicas': {n: hashlib.sha256(np.ascontiguousarray(d['X']).tobytes()).hexdigest() for n, d in [('origen', origen), ('destino', destino)]},
                 'sha256_modelo': hashlib.sha256((sal / 'modelo_base.joblib').read_bytes()).hexdigest(),
                 'naturaleza': etiqueta, 'ambiente_origen': str(origen['escenario']),
                 'ambiente_destino': str(destino['escenario']),
                 'receptor': str(destino['receptor']), 'semilla': semilla,
                 'clases': list(CLASES), 'consultas_compartidas': True,
                 'indices_consulta': indice_consulta.tolist(),
                 'seleccion_soporte': {c: permutaciones[c] for c in CLASES},
                 'guardia_ventanas': 4, 'criterio': 'bloques temporales; no sesiones independientes',
                 'hiperparametros': {'base': 'Regresion logistica / StandardScaler',
                                    'fewshot': 'prototipos + probabilidad base, alpha=0.5 fijo'}}
    (sal / 'protocolo.json').write_text(json.dumps(metadatos, ensure_ascii=False, indent=2), encoding='utf-8')
    return datos_metricas
