from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError

class Dataset(models.Model):
    nombre=models.CharField(max_length=120)
    escenario=models.CharField(max_length=2,choices=[(v,v) for v in ('S5','S6','S7')])
    receptor=models.CharField(max_length=1,choices=[(v,v) for v in 'abc'],default='a')
    ruta_relativa=models.CharField(max_length=220,help_text='Archivo NPZ relativo a datos_locales; nunca una ruta absoluta')
    revisado=models.BooleanField(default=False,help_text='Verificado manualmente tras auditoría, NO equivale a resultados válidos')
    creado=models.DateTimeField(auto_now_add=True)
    def __str__(self): return f'{self.nombre} ({self.escenario})'
    def clean(self):
        if self.ruta_relativa and (self.ruta_relativa.startswith('/') or '..' in self.ruta_relativa.replace('\\','/').split('/') or not self.ruta_relativa.lower().endswith('.npz')):
            raise ValidationError('Usa una ruta relativa NPZ dentro de datos_locales, sin ..')

class Experimento(models.Model):
    nombre=models.CharField(max_length=120)
    propietario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='experimentos')
    origen=models.ForeignKey(Dataset,on_delete=models.PROTECT,related_name='experimentos_origen')
    destino=models.ForeignKey(Dataset,on_delete=models.PROTECT,related_name='experimentos_destino')
    semilla=models.PositiveIntegerField(default=42)
    estado=models.CharField(max_length=30,default='PENDIENTE')
    naturaleza=models.CharField(max_length=80,default='SIN_EJECUTAR')
    creado=models.DateTimeField(auto_now_add=True)
    def clean(self):
        if self.origen_id and self.destino_id and self.origen.escenario == self.destino.escenario:
            raise ValidationError('El origen y el destino deben ser ambientes distintos')
    def __str__(self):return self.nombre

class Resultado(models.Model):
    experimento=models.ForeignKey(Experimento,on_delete=models.CASCADE,related_name='resultados')
    k=models.PositiveSmallIntegerField(choices=[(k,str(k)) for k in (0,1,5,10)])
    accuracy=models.FloatField(validators=[MinValueValidator(0),MaxValueValidator(1)])
    precision_macro=models.FloatField(validators=[MinValueValidator(0),MaxValueValidator(1)])
    recall_macro=models.FloatField(validators=[MinValueValidator(0),MaxValueValidator(1)])
    f1_macro=models.FloatField(validators=[MinValueValidator(0),MaxValueValidator(1)])
    class Meta:
        constraints=[models.UniqueConstraint(fields=['experimento','k'],name='unico_experimento_k')]
