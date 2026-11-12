from django.test import SimpleTestCase
from .csi_views import CaptureForm

class CaptureLabelsTest(SimpleTestCase):
    def form(self,**kwargs):
        data=dict(activity='sentado',capture_use='aprender',dataset='prueba',room='habitacion',seconds=60,distance=1.4,tx_height=1.4,rx_height=.8)
        data.update(kwargs)
        return CaptureForm(data)
    def test_posturas_precisas_y_duracion(self):
        for activity,label,posture in [('sentado','quieto','sentado'),('de_pie','quieto','de_pie_lateral'),('caminar','caminar','caminata_lateral')]:
            form=self.form(activity=activity)
            self.assertTrue(form.is_valid(),form.errors)
            self.assertEqual(form.cleaned_data['label'],label)
            self.assertEqual(form.cleaned_data['posture'],posture)
        self.assertFalse(self.form(seconds=61).is_valid())
    def test_prueba_se_reserva_y_enlace_no_se_etiqueta(self):
        for use in ['reconocer','enlace']:
            form=self.form(capture_use=use)
            self.assertTrue(form.is_valid(),form.errors)
            self.assertEqual(form.cleaned_data['label'],'sin_etiquetar')
        self.assertFalse(self.form(activity='no_controlada').is_valid())
