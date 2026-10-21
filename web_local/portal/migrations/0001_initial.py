# Migración inicial para el catálogo y la trazabilidad de experimentos
import django.core.validators
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial=True
    dependencies=[migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[
        migrations.CreateModel(
            name='Dataset',
            fields=[
                ('id',models.BigAutoField(primary_key=True,serialize=False)),
                ('nombre',models.CharField(max_length=120)),
                ('escenario',models.CharField(choices=[('S5','S5'),('S6','S6'),('S7','S7')],max_length=2)),
                ('receptor',models.CharField(choices=[('a','a'),('b','b'),('c','c')],default='a',max_length=1)),
                ('ruta_relativa',models.CharField(help_text='Archivo NPZ relativo a datos_locales; nunca una ruta absoluta',max_length=220)),
                ('revisado',models.BooleanField(default=False,help_text='Verificado manualmente tras auditoría, NO equivale a resultados válidos')),
                ('creado',models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Experimento',
            fields=[
                ('id',models.BigAutoField(primary_key=True,serialize=False)),
                ('nombre',models.CharField(max_length=120)),
                ('semilla',models.PositiveIntegerField(default=42)),
                ('estado',models.CharField(default='PENDIENTE',max_length=30)),
                ('naturaleza',models.CharField(default='SIN_EJECUTAR',max_length=80)),
                ('creado',models.DateTimeField(auto_now_add=True)),
                ('origen',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='experimentos_origen',to='portal.dataset')),
                ('destino',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='experimentos_destino',to='portal.dataset')),
                ('propietario',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='experimentos',to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Resultado',
            fields=[
                ('id',models.BigAutoField(primary_key=True,serialize=False)),
                ('k',models.PositiveSmallIntegerField(choices=[(0,'0'),(1,'1'),(5,'5'),(10,'10')])),
                ('accuracy',models.FloatField(validators=[django.core.validators.MinValueValidator(0),django.core.validators.MaxValueValidator(1)])),
                ('precision_macro',models.FloatField(validators=[django.core.validators.MinValueValidator(0),django.core.validators.MaxValueValidator(1)])),
                ('recall_macro',models.FloatField(validators=[django.core.validators.MinValueValidator(0),django.core.validators.MaxValueValidator(1)])),
                ('f1_macro',models.FloatField(validators=[django.core.validators.MinValueValidator(0),django.core.validators.MaxValueValidator(1)])),
                ('experimento',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='resultados',to='portal.experimento')),
            ],
            options={'constraints':[models.UniqueConstraint(fields=('experimento','k'),name='unico_experimento_k')]},
        ),
    ]
