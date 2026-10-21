from django import forms
from .models import Experimento
class ExperimentoForm(forms.ModelForm):
    class Meta:
        model=Experimento
        fields=['nombre','origen','destino','semilla']
