"""Arranque local con clave persistente y creaciÃ³n interactiva de administrador."""
import os, secrets, subprocess, sys, webbrowser
from pathlib import Path
ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
key = ROOT / '.django-secret'
if not key.exists():
    key.write_text(secrets.token_urlsafe(64), encoding='utf-8')
os.environ['DJANGO_SECRET_KEY'] = key.read_text(encoding='utf-8').strip()
os.environ['DJANGO_DEBUG'] = '0'
python = ROOT / '.venv' / 'Scripts' / 'python.exe'
def manage(*args):
    subprocess.run([str(python), str(ROOT/'web_local'/'manage.py'), *args], check=True)
manage('migrate', '--noinput')
probe = subprocess.run([str(python), str(ROOT/'web_local'/'manage.py'), 'shell', '-c',
    'from django.contrib.auth import get_user_model; import sys; sys.exit(0 if get_user_model().objects.filter(is_superuser=True).exists() else 3)'])
if probe.returncode == 3:
    print('Crea tu cuenta de administrador (la contraseÃ±a no se muestra al escribir).')
    manage('createsuperuser')
elif probe.returncode:
    raise SystemExit(probe.returncode)
manage('seed_demo')
print('AplicaciÃ³n disponible en http://127.0.0.1:8000/login/ . Cierra con Ctrl+C.')
manage('runserver', '127.0.0.1:8000', '--noreload', '--insecure')
