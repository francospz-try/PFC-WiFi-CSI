"""Auditoria reproducible, solo lectura de capturas/modelo; no abre puerto ni entrena modelo operativo.

Ejecutar con .venv/Scripts/python.exe herramientas/auditar_har_piloto.py
Las etiquetas reservadas son declaraciones del operador, no verdad sincronizada por ventana.
"""
import argparse
import ast
import csv
import hashlib
import json
import math
import sys
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

RESERVED = {
    'web_20261112T051105_835471_sin_etiquetar': 'caminar',
    'web_20261112T050341_476851_sin_etiquetar': 'quietud',
}
FEATURES = ['std_p25', 'std_p50', 'std_p75', 'std_p90', 'absdiff_p50', 'absdiff_p90']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')


def parse_raw(path, meta):
    packets, malformed, ignored = [], 0, 0
    for line in path.read_bytes().splitlines():
        text = line.decode('utf-8', errors='replace').strip()
        if not text.startswith('CSI_DATA,'):
            ignored += 1
            continue
        try:
            row = next(csv.reader([text]))
            if len(row) != 15:
                raise ValueError('schema')
            v = ast.literal_eval(row[14])
            if not isinstance(v, list) or len(v) != int(row[12]) or len(v) % 2 or not all(type(x) is int for x in v):
                raise ValueError('components')
            packets.append(dict(seq=int(row[1]), timestamp=int(row[9]), rssi=int(row[3]),
                                channel=int(row[8]), invalid=int(row[13]), values=v))
        except (ValueError, SyntaxError, TypeError, IndexError, csv.Error):
            malformed += 1
    ts = np.array([p['timestamp'] for p in packets], dtype=np.int64)
    seq = np.array([p['seq'] for p in packets], dtype=np.int64)
    dt = np.diff(ts)
    gaps = int(np.maximum(np.diff(seq)-1, 0).sum())
    q = dict(valid_csi=len(packets), malformed_csi=malformed,
             observed_hz=len(packets)/meta['quality']['elapsed_seconds'],
             median_interval_ms=float(np.median(dt)/1000), max_interval_ms=float(dt.max()/1000),
             nonincreasing_timestamps=int((dt <= 0).sum()), nonincreasing_sequences=int((np.diff(seq) <= 0).sum()),
             sequence_gaps=gaps, first_word_invalid=sum(p['invalid'] != 0 for p in packets),
             channels=sorted(set(p['channel'] for p in packets)),
             value_lengths=sorted(set(len(p['values']) for p in packets)),
             median_rssi=float(np.median([p['rssi'] for p in packets])))
    extra = dict(ignored_non_csi_lines=ignored, nominal_gap_fraction=gaps/(len(packets)+gaps),
                 device_span_s=float((ts[-1]-ts[0])/1e6),
                 device_rate_hz=float((len(ts)-1)*1e6/(ts[-1]-ts[0])),
                 note='observed_hz reutiliza elapsed_seconds del metadata: el reloj host no puede reconstruirse del raw')
    # Independent reproduction of the production reader: CSV across all lines, 256 components, invalid=0.
    usable_t, usable_v = [], []
    for row in csv.reader(path.read_text(encoding='utf-8', errors='replace').splitlines()):
        if not row or row[0] != 'CSI_DATA':
            continue
        try:
            if len(row) != 15 or int(row[13]):
                continue
            v = ast.literal_eval(row[14])
            if not isinstance(v, list) or len(v) != int(row[12]) or len(v) != 256 or not all(type(x) is int for x in v):
                continue
            usable_t.append(int(row[9])); usable_v.append(v)
        except (ValueError, SyntaxError, TypeError):
            continue
    ts = np.asarray(usable_t, dtype=np.int64)
    assert len(ts) >= 30 and np.all(np.diff(ts) > 0)
    iq = np.asarray(usable_v, dtype=float)
    return q, extra, (ts-ts[0])/1e6, np.hypot(iq[:, ::2], iq[:, 1::2])


def reconstruct(t, amp):
    x, rows, windows = np.log1p(amp), [], []
    for second in range(2, int(t[-1])-2):
        idx = np.flatnonzero((t >= second) & (t < second+1))
        gap = float(np.diff(t[idx]).max()) if len(idx) > 1 else None
        accepted = len(idx) >= 60 and gap <= .1
        w = dict(start_s=second, end_s=second+1, samples=len(idx), max_gap_s=gap, accepted=accepted)
        if accepted:
            z = x[idx]
            f = np.array([*np.percentile(np.std(z, axis=0), [25, 50, 75, 90]),
                          np.median(np.abs(np.diff(z, axis=0))), np.percentile(np.abs(np.diff(z, axis=0)), 90)])
            rows.append(f); w.update(dict(zip(FEATURES, f.tolist())))
        windows.append(w)
    return np.asarray(rows), windows


def refit(records, classes):
    # In-memory reconstruction, never calls train() or writes an npz.
    allx = np.vstack([r['x'] for r in records])
    mean = allx.mean(axis=0)
    scale = np.maximum(allx.std(axis=0), 1e-6)
    centers = np.array([np.mean([((r['x']-mean)/scale).mean(axis=0) for r in records if r['label'] == c], axis=0) for c in classes])
    return mean, scale, centers


def classify(x, model):
    mean, scale, centers = model
    d = np.sum((((x-mean)/scale)[:, None, :]-centers[None, :, :])**2, axis=2)
    return d.argmin(axis=1), d


def wilson(k, n):
    z = 1.959963984540054
    p, d = k/n, 1+z*z/n
    middle, half = (p+z*z/(2*n))/d, z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [middle-half, middle+half]


def evaluation(records, model, classes):
    matrix = np.zeros((len(classes), len(classes)), dtype=int)
    sessions = []
    for r in records:
        pred, d = classify(r['x'], model)
        truth = classes.index(r['label'])
        count = np.bincount(pred, minlength=len(classes))
        matrix[truth] += count
        sessions.append(dict(session=r['name'], true=r['label'], windows=len(pred),
                             counts=dict(zip(classes, count.tolist())), result=classes[int(count.argmax())],
                             accuracy=float(np.mean(pred == truth))))
    recall = np.diag(matrix)/matrix.sum(axis=1)
    precision = np.divide(np.diag(matrix), matrix.sum(axis=0), out=np.zeros(len(classes), dtype=float), where=matrix.sum(axis=0) != 0)
    f1 = np.divide(2*precision*recall, precision+recall, out=np.zeros(len(classes), dtype=float), where=precision+recall != 0)
    correct = int(np.trace(matrix)); n = int(matrix.sum())
    sc = sum(s['true'] == s['result'] for s in sessions)
    return dict(confusion=matrix.tolist(), accuracy=correct/n, balanced_accuracy=float(recall.mean()),
                precision=dict(zip(classes, precision.tolist())), recall=dict(zip(classes, recall.tolist())),
                f1=dict(zip(classes, f1.tolist())), macro_f1=float(f1.mean()), windows=n, sessions=sessions,
                session_accuracy=sc/len(sessions), session_correct=sc, session_total=len(sessions),
                window_wilson95_naive=wilson(correct, n), session_wilson95_descriptive=wilson(sc, len(sessions)),
                interval_warning='Wilson por ventana supone independencia inexistente; descriptivo, no inferencia poblacional. Dos sesiones tampoco sustentan generalizacion.')


def distribution(x):
    return {f: dict(zip(['min', 'p25', 'median', 'p75', 'max'], np.percentile(x[:, i], [0, 25, 50, 75, 100]).tolist())) for i, f in enumerate(FEATURES)}


def error_intervals(rows, prediction_key):
    runs = []
    for row in rows:
        if prediction_key not in row or row['true'] == row[prediction_key]:
            continue
        if runs and runs[-1]['session'] == row['session'] and runs[-1]['end_s'] == row['start_s'] and runs[-1]['predicted'] == row[prediction_key]:
            runs[-1]['end_s'] = row['end_s']
            runs[-1]['windows'] += 1
        else:
            runs.append(dict(session=row['session'], true=row['true'], predicted=row[prediction_key],
                             start_s=row['start_s'], end_s=row['end_s'], windows=1))
    return runs


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--out', type=Path, default=None)
    a = p.parse_args(); repo = a.repo.resolve()
    out = a.out or repo/'outputs/feria_2026/auditoria'
    out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(repo))
    from src.pfc07.csi_reconocimiento import features, infer
    report_path = repo/'outputs/csi_reconocimiento/binario.json'
    npz_path = report_path.with_suffix('.npz')
    report = json.loads(report_path.read_text(encoding='utf-8'))
    classes = report['classes']
    names = report['sessions']+list(RESERVED)
    paths = [report_path, npz_path]
    for name in names:
        folder = repo/'datos_locales/csi_piloto'/name
        paths.extend(sorted(p for p in folder.iterdir() if p.is_file()))
    baseline = {str(p.relative_to(repo)): digest(p) for p in paths}
    baseline_path = out/'sha256_baseline.json'
    if baseline_path.exists():
        old = json.loads(baseline_path.read_text(encoding='utf-8'))
        assert old == baseline, 'Datos/modelo difieren de la linea base; no reemplazar silenciosamente'
    else:
        dump(baseline_path, baseline)
    for source in ['csi_reconocimiento.py', 'csi_piloto.py']:
        target = out/('snapshot_'+source)
        if not target.exists():
            target.write_bytes((repo/'src/pfc07'/source).read_bytes())
        original = subprocess.check_output(['git', '--git-dir='+str(repo/'.git'), '--work-tree='+str(repo),
                                            'show', '95358a6:src/pfc07/'+source])
        (out/('original_95358a6_'+source)).write_bytes(original)
    with np.load(npz_path, allow_pickle=False) as z:
        model = tuple(z[k] for k in ['mean', 'scale', 'centers'])
    records, quality, window_rows, latency = [], [], [], []
    for name in names:
        folder = repo/'datos_locales/csi_piloto'/name
        meta = json.loads((folder/'metadata.json').read_text(encoding='utf-8'))
        q, extra, t, amp = parse_raw(folder/'raw.log', meta)
        x, windows = reconstruct(t, amp)
        tick = time.perf_counter()
        _, production_x = features(folder)
        feature_ms = (time.perf_counter()-tick)*1000
        assert np.array_equal(x, production_x), name+' features'
        pred, d = classify(x, model)
        assert np.array_equal(np.array(classes)[pred], infer(x, model, classes))
        tick = time.perf_counter()
        for _ in range(1000):
            infer(x, model, classes)
        infer_ms = (time.perf_counter()-tick)
        latency.append(dict(session=name, features_ms_single_run=feature_ms,
                            inference_ms_mean_1000_runs=infer_ms,
                            note='Offline: features incluye lectura y parseo de archivo; inferencia lote de ventanas. No mide captura serial ni latencia online.'))
        label = RESERVED.get(name, 'quietud' if meta['label'] == 'quieto' else meta['label'])
        records.append(dict(name=name, label=label, x=x, windows=windows))
        diff = {k: dict(stored=meta['quality'].get(k), calculated=v) for k, v in q.items() if meta['quality'].get(k) != v}
        assert digest(folder/'raw.log') == meta['raw_sha256'], name+' raw hash'
        quality.append(dict(session=name, label=label, label_source='declaracion operador por sesion',
                            stored_label=meta['label'], declared_activity=meta.get('declared_activity'),
                            posture=meta.get('posture'), room=meta.get('room'), dataset=meta.get('dataset'),
                            participant=meta.get('participant'), capture_use=meta.get('capture_use'), notes=meta.get('notes'),
                            distance_m=meta.get('distance_m'), heights_m=[meta.get('height_tx_m'), meta.get('height_rx_m')],
                            recalculated=q, supplemental=extra, metadata_differences=diff,
                            raw_hash_matches=True, reader_packets=len(t), positions=amp.shape[1],
                            all_zero_positions=np.flatnonzero(~np.any(amp, axis=0)).tolist(),
                            accepted_windows=len(x), rejected_candidate_windows=sum(not w['accepted'] for w in windows),
                            start_device_s=float(t[0]), end_device_s=float(t[-1]), features=distribution(x)))
        i = 0
        for w in windows:
            row = dict(session=name, true=label, partition='reserved' if name in RESERVED else 'training_final', **w)
            if w['accepted']:
                row.update(predicted_final=classes[int(pred[i])], distance_quietud=float(d[i, 0]), distance_caminar=float(d[i, 1]),
                           signed_margin_caminar=float(d[i, 0]-d[i, 1]), correct=bool(classes[int(pred[i])] == label))
                i += 1
            window_rows.append(row)
    train = records[:len(report['sessions'])]
    ordered = sorted(train, key=lambda r: r['name'])
    internal_test = [next(r for r in reversed(ordered) if r['label'] == c) for c in classes]
    test_names = {r['name'] for r in internal_test}
    internal_train = [r for r in ordered if r['name'] not in test_names]
    assert sorted(test_names) == sorted(report['evaluation']['test'])
    assert [r['name'] for r in internal_train] == report['evaluation']['training']
    reconstructed = refit(train, classes)
    equality = {k: dict(array_equal=bool(np.array_equal(v, model[i])), max_abs_error=float(np.max(np.abs(v-model[i])))) for i, (k, v) in enumerate(zip(['mean', 'scale', 'centers'], reconstructed))}
    assert all(v['array_equal'] for v in equality.values())
    internal_model = refit(internal_train, classes)
    internal = evaluation(internal_test, internal_model, classes)
    assert internal['confusion'] == report['evaluation']['confusion']
    assert abs(internal['accuracy']*100-report['evaluation']['accuracy_percent']) < 1e-12
    # Export internal-test decisions separately, never conflated with all-six refit.
    internal_rows = []
    for r in internal_test:
        pred, d = classify(r['x'], internal_model)
        for w, pr, dist in zip([w for w in r['windows'] if w['accepted']], pred, d):
            internal_rows.append(dict(session=r['name'], start_s=w['start_s'], end_s=w['end_s'], true=r['label'],
                                      predicted=classes[int(pr)], distance_quietud=float(dist[0]), distance_caminar=float(dist[1])))
    result = dict(created_utc=datetime.now(timezone.utc).isoformat(), classes=classes,
                  source_provenance='original_95358a6_* proviene de git show 95358a6; snapshot_* es copia de trabajo al primer arranque, potencialmente con mejoras concurrentes. Matematica verificada equivalente.',
                  independent_features_exact=True, inference_exact=True, final_model_reconstruction=equality,
                  internal_holdout=internal, reserved_final=evaluation(records[len(train):], model, classes),
                  training_resubstitution=evaluation(train, model, classes),
                  training_feature_distributions={c: distribution(np.vstack([r['x'] for r in train if r['label'] == c])) for c in classes},
                  model_arrays={k: v.tolist() for k, v in zip(['mean', 'scale', 'centers'], model)},
                  confusion_intervals_final=error_intervals(window_rows, 'predicted_final'),
                  confusion_intervals_internal=error_intervals(internal_rows, 'predicted'),
                  quality=quality, latency_offline=latency,
                  data_and_model_unchanged=baseline == {str(p.relative_to(repo)): digest(p) for p in paths})
    assert result['data_and_model_unchanged']
    dump(out/'resultados.json', result)
    dump(out/'ventanas_evaluacion_interna.json', internal_rows)
    dump(out/'sha256_final.json', {str(p.relative_to(repo)): digest(p) for p in paths})
    fields = list(dict.fromkeys(k for row in window_rows for k in row))
    with (out/'ventanas.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(window_rows)
    lines = ['# Auditoria numerica HAR local', '',
             'Las etiquetas reservadas provienen de la declaracion del operador por sesion. No hay anotacion temporal independiente.',
             'Se reconstruyeron features, split interno y parametros finales en memoria; no se llamo train ni se escribio el modelo operativo.',
             'Reproduccion: `.venv\\Scripts\\python.exe herramientas\\auditar_har_piloto.py`.', '',
             '| Evaluacion | Matriz (quietud, caminar) | Ventanas | Exactitud | Balanceada | Macro F1 | Sesiones correctas |',
             '|---|---|---:|---:|---:|---:|---:|']
    for key in ['internal_holdout', 'reserved_final', 'training_resubstitution']:
        e = result[key]
        lines.append(f"| {key} | {e['confusion']} | {e['windows']} | {e['accuracy']:.4%} | {e['balanced_accuracy']:.4%} | {e['macro_f1']:.6f} | {e['session_correct']}/{e['session_total']} |")
    lines += ['', 'Resustitucion no es validacion. Holdout interno usa cuatro sesiones; modelo final usa las seis. Reservadas no entran en ninguno de los ajustes.', '',
              '| Sesion | Etiqueta | Paquetes | Hz host | Saltos | Perdida nominal | RSSI mediano | Ventanas |',
              '|---|---|---:|---:|---:|---:|---:|---:|']
    for q in quality:
        v = q['recalculated']
        lines.append(f"| {q['session']} | {q['label']} | {v['valid_csi']} | {v['observed_hz']:.3f} | {v['sequence_gaps']} | {q['supplemental']['nominal_gap_fraction']:.3%} | {v['median_rssi']} | {q['accepted_windows']} |")
    lines += ['', '## Evidencia y limites', '',
              '- Matrices: filas verdaderas, columnas predichas; orden quietud, caminar. CSV contiene inicio/fin, seis indicadores, distancias cuadraticas y margen.',
              '- features independientes e inferencia coinciden exactamente; mean/scale/centers del reajuste con seis sesiones coinciden bit a bit con NPZ.',
              '- Todos los hashes raw coinciden con metadata; hashes de archivos relevantes antes/despues estan en los manifiestos. No se modificaron originales.',
              '- observed_hz usa la duracion host almacenada; el raw permite verificar tasa por reloj del dispositivo, no reconstruir esa duracion host.',
              '- Saltos de secuencia no distinguen radio/USB; lineas no CSI incluyen fragmentos de inicio y logs, no se cuentan automaticamente como paquetes perdidos.',
              '- Se usan las 128 amplitudes, incluidas posiciones siempre nulas; no se hizo seleccion de subportadoras ni calibracion de probabilidad.',
              '- Los intervalos Wilson en JSON son descriptivos. Ventanas contiguas autocorrelacionadas y dos sesiones reservadas no prueban rendimiento poblacional.',
              '- Una captura unica por clase reservada confunde actividad con sesion, posicion, RSSI y condiciones del canal; no permite atribuir causalidad.',
              '- Comparar distribuciones de indicadores en JSON y margenes en CSV permite localizar solapamiento/desplazamiento; una hipotesis de cambio de canal requiere nuevas repeticiones controladas.',
              '- Los porcentajes son fracciones de ventanas asignadas, no confianza calibrada; el voto mayoritario de sesion puede ocultar errores temporales.',
              '- Ventanas son [s,s+1), s=2..int(t_final)-3; int trunca fraccion final. No hay interpolacion ni ventanas aleatorias entre particiones.', '']
    (out/'hallazgos_numericos.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({k: result[k] for k in ['internal_holdout', 'reserved_final', 'training_resubstitution', 'final_model_reconstruction', 'data_and_model_unchanged']}, indent=2))


if __name__ == '__main__':
    main()
