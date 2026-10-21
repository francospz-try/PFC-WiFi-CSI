import json
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from portal.models import Dataset
class Command(BaseCommand):
    help='Registra características CSI reales después de verificar sus metadatos'
    def handle(self,*args,**kwargs):
        for escenario in ('S5','S6','S7'):
            ruta=settings.DATA_DIR/f'{escenario}_real.npz'
            if not ruta.exists():raise CommandError(f'Falta {ruta}')
            meta=json.loads(ruta.with_suffix('.json').read_text(encoding='utf-8'))
            if meta.get('naturaleza')!='CSI_REAL_BASELINE_EXPLORATORIO':raise CommandError('Procedencia incompatible')
            Dataset.objects.update_or_create(nombre=f'CSI REAL {escenario} · receptor a · antena 0',defaults={'escenario':escenario,'receptor':'a','ruta_relativa':ruta.name,'revisado':True})
            self.stdout.write(f'{escenario}: registrado (estructura revisada; protocolo exploratorio)')
