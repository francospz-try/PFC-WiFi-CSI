import os, secrets, subprocess, sys
os.environ['DJANGO_SECRET_KEY'] = secrets.token_urlsafe(50)
subprocess.run([sys.executable, 'web_local/manage.py', 'test', 'portal'], check=True)
