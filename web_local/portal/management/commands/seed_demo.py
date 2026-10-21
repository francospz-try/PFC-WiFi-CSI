"""Registra sólo metadatos sintéticos para explorar la UI sin CSI descargado."""
from django.core.management.base import BaseCommand
from portal.models import Dataset

class Command(BaseCommand):
    help = 'Registra dos entradas de catálogo DEMO (no archivos ni señales reales)'

    def handle(self, *args, **options):
        for escenario in ('S5', 'S7'):
            obj, creado = Dataset.objects.get_or_create(
                nombre=f'DEMO SINTÉTICA {escenario} (NO CSI REAL)',
                escenario=escenario,
                defaults={
                    'receptor': 'a',
                    'ruta_relativa': f'demo/no_existe_{escenario.lower()}.npz',
                    'revisado': False,
                },
            )
            self.stdout.write(f'{obj}: {"creado" if creado else "ya existente"}')
        self.stdout.write(self.style.WARNING('SOLO DEMO: NO EXISTEN ARCHIVOS CSI DESCARGADOS'))
