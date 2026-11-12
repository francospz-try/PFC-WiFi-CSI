import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse

class CSIPilotoTest(TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.project=Path(self.tmp.name)
        cfg=override_settings(PROJECT_DIR=self.project);cfg.enable();self.addCleanup(cfg.disable)
        user=get_user_model().objects.create_user(username='operador_csi',is_staff=True)
        self.client.force_login(user)
        for name,label in [('prueba_a','quieto'),('prueba_b','caminar')]:
            folder=self.project/'datos_locales'/'csi_piloto'/name;folder.mkdir(parents=True)
            meta=dict(session=name,label=label,quality={},room='prueba',status='completa')
            (folder/'metadata.json').write_text(json.dumps(meta))
            lines=[]
            for i in range(200):
                vals=[1+(i%3),3]*128
                lines.append(f'CSI_DATA,{i},1a:00:00:00:00:00,-74,0,0,0,0,11,{i*11000},0,0,256,0,"{vals}"')
            (folder/'raw.log').write_text('\n'.join(lines))
    def test_panel_y_grafico_real(self):
        response=self.client.get(reverse('csi_panel'),{'a':'prueba_a','b':'prueba_b'})
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'prueba_a')
        response=self.client.get(reverse('csi_graph'),{'a':'prueba_a','b':'prueba_b'})
        self.assertEqual(response.status_code,200)
        self.assertTrue(response.content.startswith(b'\x89PNG'))
    def test_ruta_fuera_de_sesiones_rechazada(self):
        self.assertEqual(self.client.get(reverse('csi_graph'),{'a':'../secreto','b':'prueba_b'}).status_code,404)
    def test_solo_staff_y_captura_solo_post(self):
        self.assertEqual(self.client.get(reverse('csi_capture')).status_code,405)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('csi_panel')).status_code,302)
        user=get_user_model().objects.create_user(username='investigador_csi')
        self.client.force_login(user)
        self.assertEqual(self.client.post(reverse('csi_capture')).status_code,302)
    @patch('portal.csi_views.subprocess.run')
    def test_parametros_invalidos_no_abren_puerto(self,run):
        self.client.post(reverse('csi_capture'),{'seconds':10000})
        run.assert_not_called()
