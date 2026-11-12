"""Instancia descartable de la aplicación para evidencias visuales y HTTP."""
import os
import sys
import tempfile
from pathlib import Path
root=Path(__file__).resolve().parent
sys.path[:0]=[str(root),str(root/'web_local')]
os.environ['DJANGO_SECRET_KEY']='lab08-instancia-temporal-no-usar-en-produccion'
os.environ['DJANGO_SETTINGS_MODULE']='config.settings'
from django.conf import settings
with tempfile.TemporaryDirectory(prefix='pfc08_capturas_') as temp:
    settings.DATABASES['default']['NAME']=str(Path(temp)/'pruebas.sqlite3')
    settings.OUTPUT_DIR=Path(temp)/'salidas'
    import django
    django.setup()
    from django.core.management import call_command
    call_command('migrate',verbosity=0,interactive=False)
    from django.contrib.auth import get_user_model
    from portal.models import Dataset,Experimento
    user=get_user_model().objects.create_user('investigador_lab08',password='Lab08_temporal_2026!')
    otro=get_user_model().objects.create_user('otro_investigador')
    datasets={s:Dataset.objects.create(nombre=f'CSI REAL {s} - receptor a - antena 0',escenario=s,receptor='a',ruta_relativa=f'{s}_real.npz',revisado=True) for s in ('S5','S6','S7')}
    Experimento.objects.create(nombre='Experimento de otro investigador',propietario=otro,origen=datasets['S5'],destino=datasets['S7'])
    print('Instancia aislada disponible: http://127.0.0.1:8768/login/',flush=True)
    call_command('runserver','127.0.0.1:8768',use_reloader=False,insecure_serving=True)
