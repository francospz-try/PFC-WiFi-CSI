import csv
from contextlib import closing
import json
import os
import secrets
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from serial.tools.list_ports import comports

root = Path(__file__).resolve().parent.parent
os.chdir(root)
salida = root / 'outputs/cierre_20261125/verificacion'
salida.mkdir(parents=True, exist_ok=True)
sys.path[:0] = [str(root), str(root / 'web_local')]
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['DJANGO_SECRET_KEY'] = secrets.token_urlsafe(48)
from django.conf import settings
import django

with tempfile.TemporaryDirectory(prefix='pfc_cierre_recuperacion_') as nombre:
    temp = Path(nombre)
    settings.DATABASES['default']['NAME'] = str(temp / 'cierre.sqlite3')
    settings.OUTPUT_DIR = temp / 'outputs'
    django.setup()
    from django.core.management import call_command
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    from django.contrib.auth import get_user_model
    from portal.models import Experimento, Resultado
    call_command('migrate', 'auth', interactive=False, verbosity=0)
    call_command('migrate', 'portal', '0001', interactive=False, verbosity=0)
    call_command('seed_demo', verbosity=0)
    migrador = MigrationExecutor(connection)
    apps = migrador.loader.project_state([('portal','0001_initial')]).apps
    user = get_user_model().objects.create_user('verificacion_temporal')
    origen, destino = list(apps.get_model('portal','Dataset').objects.order_by('escenario'))
    exp = apps.get_model('portal','Experimento').objects.create(
        nombre='Experimento anterior', propietario_id=user.pk, origen=origen, destino=destino)
    apps.get_model('portal','Resultado').objects.create(
        experimento=exp, k=0, accuracy=.25, precision_macro=.2, recall_macro=.25, f1_macro=.21)
    connection.close()
    with closing(sqlite3.connect(temp / 'cierre.sqlite3')) as original, closing(sqlite3.connect(temp / 'respaldo.sqlite3')) as respaldo:
        original.backup(respaldo)
        assert respaldo.execute('PRAGMA integrity_check').fetchone() == ('ok',)
    call_command('migrate', interactive=False, verbosity=0)
    assert Experimento.objects.get(pk=exp.pk).ajuste_id is None
    assert Resultado.objects.get(experimento_id=exp.pk).f1_macro == .21
    call_command('migrate', 'portal', '0001', interactive=False, verbosity=0)
    connection.close()
    with closing(sqlite3.connect(temp / 'respaldo.sqlite3')) as respaldo, closing(sqlite3.connect(temp / 'restaurado.sqlite3')) as restaurado:
        respaldo.backup(restaurado)
        assert restaurado.execute('PRAGMA integrity_check').fetchone() == ('ok',)
        assert restaurado.execute('SELECT f1_macro FROM portal_resultado').fetchone() == (.21,)
    call_command('check', verbosity=0)
subprocess.run([sys.executable, '-m', 'pip', 'check'], check=True)
record = {'requisitos':'pip check sin incidencias', 'migracion_desde_0001':'conserva experimento y F1',
          'reversion_0002':'ejecutada en SQLite temporal', 'backup_restaurado':'integrity_check ok y fila conservada',
          'puertos_seriales_visibles':[p.device for p in comports()],
          'hardware':'enumeración únicamente; validación física requiere operador'}
(salida / 'instalacion_recuperacion.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(record, ensure_ascii=False), flush=True)

with socket.socket() as test:
    if test.connect_ex(('127.0.0.1', 8768)) == 0:
        raise RuntimeError('Puerto 8768 ya ocupado; se conservó la instancia preexistente')
entorno = {**os.environ, 'PFC_LAB08_PASSWORD': secrets.token_urlsafe(24)}
with (salida / 'servidor_http.log').open('w', encoding='utf-8') as log:
    proc = subprocess.Popen([sys.executable, '-B', 'servidor_lab08.py'],
                            stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW, env=entorno)
    try:
        for intento in range(60):
            with socket.socket() as cliente:
                activo = cliente.connect_ex(('127.0.0.1', 8768)) == 0
            if activo:
                break
            if proc.poll() is not None:
                raise RuntimeError('No inició el servidor descartable')
            time.sleep(.2)
        else:
            raise RuntimeError('Tiempo agotado al iniciar servidor descartable')
        subprocess.run([sys.executable, '-B', 'verificar_http08.py', '--salida', str(salida)], check=True, env=entorno)
    finally:
        proc.terminate()
        proc.wait(timeout=10)

with (salida / 'http_carga.csv').open(encoding='utf-8-sig', newline='') as archivo:
    filas = list(csv.DictReader(archivo))
por_hilos = {}
for hilos in ('1', '4', '8'):
    muestras = sorted(float(f['ms']) for f in filas if f['concurrencia']==hilos)
    por_hilos[hilos] = {'n': len(muestras), 'p95_ms': round(muestras[28], 3)}
(salida / 'http_latencia.json').write_text(json.dumps(por_hilos, indent=2), encoding='utf-8')
print(por_hilos, flush=True)
