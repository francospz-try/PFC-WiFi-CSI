import json,hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from django.test import TestCase,override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from unittest.mock import patch

class AvanceTest(TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.project=Path(self.tmp.name)
        ctx=override_settings(PROJECT_DIR=self.project);ctx.enable();self.addCleanup(ctx.disable)
        user=get_user_model().objects.create_user(username='docente_demo',is_staff=True)
        self.client.force_login(user)
        a=self.project/'outputs/auditoria_publicos_20261030';a.mkdir(parents=True)
        (a/'auditoria.json').write_text(json.dumps(dict(archives=[],selected=[dict(member='S5/S5a_A.mat')])))
        (a/'resumen_lectura_15.json').write_text(json.dumps(dict(files=15,all_crc_verified=True,nonfinite_components=0)))
    def test_progress_depends_on_evidence(self):
        r=self.client.get(reverse('avance_panel'));self.assertEqual(r.status_code,200)
        self.assertEqual(r.context['progress'],15)
        d=self.project/'outputs/entregable_30/demo';d.mkdir(parents=True)
        (d/'ventanas_demo.npz').write_bytes(b'artefacto_fixture')
        (self.project/'script').write_bytes(b'codigo_fixture')
        (d/'manifest.json').write_text(json.dumps(dict(crc_verified=True,finite=True,npz_sha256=hashlib.sha256(b'artefacto_fixture').hexdigest(),script_hashes={'script':hashlib.sha256(b'codigo_fixture').hexdigest()})))
        r=self.client.get(reverse('avance_panel'));self.assertEqual(r.context['progress'],35)
        self.assertEqual(sum(x['weight'] for x in r.context['criteria']),100)
        (d/'ventanas_demo.npz').write_bytes(b'modificado')
        self.assertEqual(self.client.get(reverse('avance_panel')).context['progress'],30)
    @patch('portal.avance_views.subprocess.run')
    def test_no_arbitrary_input_or_get_mutation(self,run):
        self.assertEqual(self.client.get(reverse('avance_run')).status_code,405)
        self.client.post(reverse('avance_run'),{'member':'../../secreto'})
        run.assert_not_called()
        self.assertEqual(self.client.get(reverse('avance_asset',args=['otro'])).status_code,404)
    def test_staff_required(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('avance_panel')).status_code,302)

    @patch('portal.avance_views.subprocess.run')
    def test_installation_without_public_audit(self,run):
        (self.project/'outputs/auditoria_publicos_20261030/auditoria.json').unlink()
        r=self.client.post(reverse('avance_run'),follow=True)
        self.assertContains(r,'Primero genera el inventario')
        run.assert_not_called()
