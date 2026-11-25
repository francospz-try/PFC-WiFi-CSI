"""Recalcula las métricas desde los CSV y verifica la separación de roles."""

import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
from statistics import mean


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('salida', type=Path, help='Directorio de salida de evaluar_fewshot_c6.py')
salida = parser.parse_args().salida
informe = json.loads((salida / 'evaluacion.json').read_text(encoding='utf-8'))
clases = informe['clases']
adquisiciones = informe['adquisiciones']
consultas = {r['sesion'] for r in adquisiciones if r['rol'] == 'consulta'}
soportes = {r['sesion'] for r in adquisiciones if r['rol'] == 'soporte'}
assert len(consultas) == len(soportes) == 4 and consultas.isdisjoint(soportes)


def leer(nombre):
    with (salida / nombre).open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def matriz(predicciones):
    c = Counter((r['declarada'], r['predicha']) for r in predicciones)
    return [[c[a, b] for b in clases] for a in clases]


def comprobar_metricas(m, registradas):
    assert m == registradas['confusion']
    total = sum(sum(fila) for fila in m)
    exactitud = sum(m[i][i] for i in range(len(clases))) / total
    f1s = []
    for i, clase in enumerate(clases):
        pos_real = sum(m[i])
        pos_predicha = sum(fila[i] for fila in m)
        tp = m[i][i]
        p = tp / pos_predicha if pos_predicha else 0
        r = tp / pos_real if pos_real else 0
        f1 = 2 * tp / (pos_predicha + pos_real) if pos_predicha + pos_real else 0
        f1s.append(f1)
        assert abs(registradas['por_clase'][clase]['precision'] - p) < 1e-12
        assert abs(registradas['por_clase'][clase]['recall'] - r) < 1e-12
    assert abs(registradas['accuracy'] - exactitud) < 1e-12
    assert abs(registradas['macro_f1'] - mean(f1s)) < 1e-12


def agrupar(filas):
    grupos = defaultdict(list)
    for r in filas:
        grupos[r['metodo'], r['k'], r['primer_soporte']].append(r)
    return grupos


ventanas = agrupar(leer('predicciones_ventanas.csv'))
sesiones = agrupar(leer('predicciones_sesiones.csv'))
config_base = ('historico', '0', '0')
configuraciones = {config_base: informe['historico']}
selecciones = {}
for r in informe['comparaciones']:
    k = r['k']
    n = r['primer_soporte']
    configuraciones[r['metodo'], str(k), str(n)] = r['metricas']
    seleccion = {(w['clase'], w['sesion'], w['inicio_s']) for w in r['soporte']}
    assert len(seleccion) == k * len(clases)
    assert {s for _, s, _ in seleccion} <= soportes
    assert all(sum(c == clase for c, _, _ in seleccion) == k for clase in clases)
    if (k, n) in selecciones:
        assert selecciones[k, n] == seleccion
    selecciones[k, n] = seleccion
    for nivel, metricas in r['metricas'].items():
        for m in ('accuracy', 'macro_f1'):
            assert abs(r['cambio_vs_historico'][nivel][m] - metricas[m] + informe['historico'][nivel][m]) < 1e-12
for n in (1, 2):
    orden = [selecciones[k, n] for k in (1, 5, 10) if (k, n) in selecciones]
    assert all(a < b for a, b in zip(orden, orden[1:]))

assert set(ventanas) == set(sesiones) == set(configuraciones)
intervalos = {(r['sesion'], r['inicio_s'], r['fin_s'], r['declarada']) for r in ventanas[config_base]}
for cfg, resultados in configuraciones.items():
    assert len(ventanas[cfg]) == len(intervalos)
    assert {(r['sesion'], r['inicio_s'], r['fin_s'], r['declarada']) for r in ventanas[cfg]} == intervalos
    assert len(sesiones[cfg]) == 4 and {r['sesion'] for r in sesiones[cfg]} == consultas
    comprobar_metricas(matriz(ventanas[cfg]), resultados['ventanas'])
    comprobar_metricas(matriz(sesiones[cfg]), resultados['sesiones'])
    for r in sesiones[cfg]:
        votos = Counter(w['predicha'] for w in ventanas[cfg] if w['sesion'] == r['sesion'])
        assert r['predicha'] == max(clases, key=votos.__getitem__)
        assert all(int(r[clase]) == votos[clase] for clase in clases)
        assert int(r['ventanas']) == sum(votos.values())

filas = []
for k in (1, 5, 10):
    for metodo in ('destino', 'regularizado'):
        selectas = [r for r in informe['comparaciones'] if r['k'] == k and r['metodo'] == metodo]
        if not selectas:
            continue
        for nivel in ('ventanas', 'sesiones'):
            resumen = {m: mean(r['metricas'][nivel][m] for r in selectas)
                       for m in ('accuracy', 'macro_precision', 'macro_recall', 'macro_f1')}
            filas.append(dict(k=k, metodo=metodo, nivel=nivel, **resumen,
                              delta_accuracy_pp=100*(resumen['accuracy']-informe['historico'][nivel]['accuracy']),
                              delta_macro_f1_pp=100*(resumen['macro_f1']-informe['historico'][nivel]['macro_f1'])))
with (salida / 'medias_por_presupuesto.csv').open('w', encoding='utf-8', newline='') as f:
    columnas = 'k metodo nivel accuracy macro_precision macro_recall macro_f1 delta_accuracy_pp delta_macro_f1_pp'.split()
    writer = csv.DictWriter(f, fieldnames=columnas)
    writer.writeheader()
    writer.writerows(filas)
print(f'{len(configuraciones)} configuraciones verificadas, {len(intervalos)} ventanas de consulta y cuatro sesiones por configuración.')
