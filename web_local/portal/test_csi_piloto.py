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

    def test_capture_recovers_physical_setup_but_requires_activity_and_use(self):
        p=self.project/'datos_locales'/'csi_piloto'/'prueba_b'/'metadata.json'
        meta=json.loads(p.read_text());meta.update(start_utc='2026-11-12T10:00:00Z',dataset='feria',room='sala',seconds=45,distance_m=2.1,height_tx_m=1.2,height_rx_m=.9,declared_activity='caminar',capture_use='reconocer')
        p.write_text(json.dumps(meta))
        response=self.client.get(reverse('csi_panel'))
        form=response.context['form']
        self.assertEqual(form['dataset'].value(),'feria')
        self.assertEqual(form['room'].value(),'sala')
        self.assertEqual(form['seconds'].value(),45)
        self.assertEqual(form['distance'].value(),2.1)
        self.assertEqual(form['tx_height'].value(),1.2)
        self.assertEqual(form['rx_height'].value(),.9)
        self.assertEqual(form.fields['activity'].choices[0][0],'')
        self.assertEqual(form.fields['capture_use'].choices[0][0],'')
        self.assertContains(response,'Resumen por dataset')
        self.assertEqual(response.context['dataset_summary'][0]['reconocer'],1)

    def test_recognition_error_preserves_selected_session_and_mode(self):
        response=self.client.post(reverse('csi_predict'),{'mode':'posturas','session':'prueba_b'},follow=True)
        self.assertEqual(response.context.get('selected_session'),'prueba_b')
        self.assertEqual(response.context.get('selected_mode'),'posturas')
        self.assertContains(response,'value="posturas" selected',count=2)
        self.assertContains(response,'value="prueba_b" selected')

    def test_training_error_preserves_dataset_and_mode(self):
        response=self.client.post(reverse('csi_train'),{'mode':'posturas','dataset':'campana_z'},follow=True)
        self.assertEqual(response.context.get('selected_dataset'),'campana_z')
        self.assertEqual(response.context.get('selected_mode'),'posturas')
        self.assertContains(response,'value="posturas" selected',count=2)

    def test_recognition_lists_corrupt_metadata_as_error(self):
        p=self.project/'datos_locales'/'csi_piloto'/'prueba_b'/'metadata.json';p.write_text('{')
        response=self.client.get(reverse('csi_recognize'))
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'No se pudieron leer')

    def test_successful_prediction_keeps_older_selection_and_shows_model_evaluation(self):
        import hashlib
        from src.pfc07.csi_reconocimiento import train
        root=self.project/'datos_locales'/'csi_piloto'
        for name,label,start in [('prueba_a','quieto','01'),('prueba_b','caminar','02'),('prueba_c','quieto','03'),('prueba_d','caminar','04'),('reserved_old','sin_etiquetar','05'),('reserved_new','sin_etiquetar','06')]:
            folder=root/name;folder.mkdir(exist_ok=True)
            meta=dict(session=name,label=label,dataset='campana',room='prueba',start_utc=f'2026-11-12T10:00:{start}Z',declared_activity='sentado',quality=dict(valid_csi=900,observed_hz=90,sequence_gaps=0,malformed_csi=0))
            (folder/'metadata.json').write_text(json.dumps(meta))
            lines=[f'CSI_DATA,{i},mac,-74,0,0,0,0,11,{i*11000},0,0,256,0,"{[20+i%3,3]*128}"' for i in range(900)]
            (folder/'raw.log').write_text('\n'.join(lines))
        out=self.project/'outputs'/'csi_reconocimiento'
        train(root,out,'binario','campana')
        response=self.client.post(reverse('csi_predict'),{'mode':'binario','session':'reserved_old'},follow=True)
        self.assertEqual(response.context['prediction']['session'],'reserved_old')
        self.assertContains(response,'value="reserved_old" selected')
        self.assertContains(response,'<p>Actividad declarada por el operador: <strong>sentado</strong>.</p>',html=True)
        self.assertContains(response,'Actividad inferida:')
        self.assertContains(response,'campana')
        self.assertContains(response,hashlib.sha256((out/'binario.npz').read_bytes()).hexdigest())
        self.assertContains(response,'Evaluacion interna: filas = actividad real')
        self.assertEqual(len(response.context['models'][0]['confusion_rows']),2)
        # A failed subsequent attempt must not display the previous successful result.
        response=self.client.post(reverse('csi_predict'),{'mode':'binario','session':'prueba_a'},follow=True)
        self.assertIsNone(response.context['prediction'])
        self.assertEqual(response.context['selected_session'],'prueba_a')

        p=root/'reserved_old'/'metadata.json'
        meta=json.loads(p.read_text());meta['dataset']='otro_dataset';p.write_text(json.dumps(meta))
        response=self.client.post(reverse('csi_predict'),{'mode':'binario','session':'reserved_old'},follow=True)
        self.assertIsNone(response.context['prediction'])
        self.assertEqual(response.context['selected_session'],'reserved_old')
        self.assertContains(response,'mismo dataset del modelo')
