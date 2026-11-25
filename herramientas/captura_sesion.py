"""Captura CSI C6 con metadatos y control de calidad, sin sobrescribir registros."""
import argparse
import ast
import csv
import hashlib
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
import serial


def parse_csi(text):
    row = next(csv.reader([text]))
    if len(row) != 15 or row[0] != 'CSI_DATA':
        raise ValueError('Esquema CSI C6 inesperado')
    values = ast.literal_eval(row[14])
    if not isinstance(values, list) or len(values) != int(row[12]):
        raise ValueError('Longitud CSI inconsistente')
    if len(values) % 2 or not all(type(x) is int for x in values):
        raise ValueError('Componentes CSI invalidos')
    return dict(seq=int(row[1]), timestamp=int(row[9]), rssi=int(row[3]),
                channel=int(row[8]), invalid=int(row[13]), values=values)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port', default='COM7')
    p.add_argument('--seconds', type=float, default=30)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1] / 'datos_locales/csi_piloto')
    p.add_argument('--session', required=True)
    p.add_argument('--room', required=True)
    p.add_argument('--capture-use', default='no_especificado')
    p.add_argument('--declared-activity', default='no_especificada')
    p.add_argument('--posture', default='no_especificada')
    p.add_argument('--dataset', default='piloto_inicial')
    p.add_argument('--participant', default='P01')
    p.add_argument('--label', choices=['sin_etiquetar', 'quieto', 'caminar'], required=True)
    p.add_argument('--distance-m', type=float, required=True)
    p.add_argument('--height-tx-m', type=float, required=True)
    p.add_argument('--height-rx-m', type=float, required=True)
    p.add_argument('--notes', default='')
    a = p.parse_args()
    if a.seconds <= 0 or min(a.distance_m, a.height_tx_m, a.height_rx_m) <= 0:
        p.error('Duraciones y medidas deben ser positivas')
    if any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in a.session):
        p.error('Usa letras, numeros, guion o guion bajo para session')
    folder = Path(a.root) / a.session
    folder.mkdir(parents=True, exist_ok=False)
    raw = folder / 'raw.log'
    packets = []
    malformed = 0
    status = 'completa'
    metadata = vars(a).copy()
    metadata['root'] = str(a.root)
    metadata.update(start_utc=datetime.now(timezone.utc).isoformat(),
                    purpose='piloto_adquisicion_no_evaluacion_HAR', schema='esp-csi-C6-15-columnas',
                    label_source='operador', status='iniciada')
    meta_path = folder / 'metadata.json'
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding='utf-8')
    start = time.monotonic()
    try:
        with serial.Serial(a.port, 921600, timeout=.05) as s, raw.open('xb') as f:
            s.reset_input_buffer()
            start = time.monotonic()
            print('CAPTURANDO', a.label, a.seconds, 'segundos', flush=True)
            while time.monotonic() - start < a.seconds:
                block = s.read(min(max(s.in_waiting, 1), 65536))
                if block:
                    f.write(block)
    except KeyboardInterrupt:
        status = 'interrumpida'
    except (OSError, serial.SerialException) as exc:
        status = 'error'
        metadata['error'] = str(exc)
    elapsed = time.monotonic() - start
    # La adquisicion no analiza componentes ni realiza una operacion USB por byte.
    # Procesar despues de cerrar el puerto reduce la presion sobre la recepcion.
    if raw.exists():
        for line in raw.read_bytes().splitlines():
            text = line.decode('utf-8', errors='replace').strip()
            if not text.startswith('CSI_DATA,'):
                continue
            try:
                packets.append(parse_csi(text))
            except (ValueError, SyntaxError, TypeError, IndexError, csv.Error):
                malformed += 1
    times = [x['timestamp'] for x in packets]
    deltas = [b-a for a,b in zip(times, times[1:])]
    seqs = [x['seq'] for x in packets]
    resets = sum(b <= a for a,b in zip(seqs, seqs[1:]))
    quality = dict(valid_csi=len(packets), malformed_csi=malformed,
                   elapsed_seconds=elapsed, observed_hz=len(packets)/max(elapsed, 1e-9),
                   median_interval_ms=statistics.median(deltas)/1000 if deltas else None,
                   max_interval_ms=max(deltas)/1000 if deltas else None,
                   nonincreasing_timestamps=sum(x <= 0 for x in deltas),
                   nonincreasing_sequences=resets,
                   sequence_gaps=sum(max(0,b-a-1) for a,b in zip(seqs, seqs[1:])),
                   first_word_invalid=sum(x['invalid'] != 0 for x in packets),
                   channels=sorted(set(x['channel'] for x in packets)),
                   value_lengths=sorted(set(len(x['values']) for x in packets)),
                   median_rssi=statistics.median(x['rssi'] for x in packets) if packets else None,
                   note='Calidad de adquisicion; no mide precision de reconocimiento. Saltos no distinguen perdida radio de perdida USB.')
    metadata.update(acquisition_method='USB por bloques; analisis posterior',status=status, end_utc=datetime.now(timezone.utc).isoformat(), quality=quality,
                    raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest() if raw.exists() else None)
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(metadata, indent=2, ensure_ascii=False))
    if status != 'completa' or not packets:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
