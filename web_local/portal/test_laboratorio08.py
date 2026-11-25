"""Integración real opcional y seguridad, con base y salidas aisladas."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import skipUnless
from django.test import TestCase, override_settings, Client
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from .models import Dataset, Experimento


class Laboratorio08Test(TestCase):
    def setUp(self):
        temp=TemporaryDirectory(prefix='lab08_web_');self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        override=override_settings(DATA_DIR=self.root/'datos',OUTPUT_DIR=self.root/'salidas')
        override.enable();self.addCleanup(override.disable)
        cache.clear();self.addCleanup(cache.clear)
        self.user=get_user_model().objects.create_user('lab08',password='Prueba_temporal_2026!')
        self.client.force_login(self.user)
        self.ds=[Dataset.objects.create(nombre=s,escenario=s,receptor='a',ruta_relativa=f'{s}_real.npz',revisado=True) for s in ('S5','S7')]
        self.exp=Experimento.objects.create(nombre='lab08',propietario=self.user,origen=self.ds[0],destino=self.ds[1])

    def test_archivo_ausente_controlado(self):
        r=self.client.post(reverse('ejecutar_real',args=[self.exp.pk]),follow=True)
        self.assertEqual(r.status_code,200)
        self.assertContains(r,'No se pudo ejecutar')
        self.assertFalse(self.exp.resultados.exists())
        self.assertFalse((self.root/'salidas').exists())

    def test_ruta_fuera_del_catalogo(self):
        self.ds[0].ruta_relativa='../fuera.npz';self.ds[0].save()
        r=self.client.post(reverse('ejecutar_real',args=[self.exp.pk]),follow=True)
        self.assertContains(r,'Ruta no permitida')
        self.assertFalse(self.exp.resultados.exists())

    def test_real_csrf(self):
        c=Client(enforce_csrf_checks=True);c.force_login(self.user)
        self.assertEqual(c.post(reverse('ejecutar_real',args=[self.exp.pk])).status_code,403)

    def test_limite_login(self):
        c=Client()
        for _ in range(5):
            self.assertEqual(c.post(reverse('login'),{'username':'lab08','password':'incorrecta'}).status_code,200)
        self.assertEqual(c.post(reverse('login'),{'username':'lab08','password':'incorrecta'}).status_code,429)

    @skipUnless(os.environ.get('PFC_TEST_REAL_DATA'), 'Definir PFC_TEST_REAL_DATA para integración con NPZ reales')
    def test_csi_real_integracion_completa(self):
        ruta=Path(os.environ['PFC_TEST_REAL_DATA']).resolve()
        with override_settings(DATA_DIR=ruta):
            r=self.client.post(reverse('ejecutar_real',args=[self.exp.pk]))
        self.assertEqual(r.status_code,302)
        self.exp.refresh_from_db();self.assertEqual(self.exp.estado,'REAL_COMPLETADO')
        self.assertEqual(list(self.exp.resultados.order_by('k').values_list('k',flat=True)),[0,1,5,10])
        for nombre in ('detalle','exportar','grafico'):
            self.assertEqual(self.client.get(reverse(nombre,args=[self.exp.pk])).status_code,200)
        from .views import carpeta_resultado_real
        p=json.loads((carpeta_resultado_real(self.exp) / 'protocolo.json').read_text(encoding='utf-8'))
        self.assertIn('CSI_REAL',p['naturaleza'])
