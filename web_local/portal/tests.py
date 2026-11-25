from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from pathlib import Path
from tempfile import TemporaryDirectory
from django.test import override_settings
from .models import Dataset,Experimento
U=get_user_model()
class SeguridadTest(TestCase):
    def setUp(self):
        temporal = TemporaryDirectory(prefix='pfc_web_test_')
        self.addCleanup(temporal.cleanup)
        self.raiz_pruebas = Path(temporal.name)
        ajuste = override_settings(OUTPUT_DIR=self.raiz_pruebas / 'outputs',
                                   DATA_DIR=self.raiz_pruebas / 'datos')
        ajuste.enable()
        self.addCleanup(ajuste.disable)
        self.a=U.objects.create_user(username='investigador_a',password='MuySegura_A_2026!')
        self.b=U.objects.create_user(username='investigador_b',password='MuySegura_B_2026!')
        self.admin=U.objects.create_superuser(username='administrador',password='MuySegura_Admin_2026!',email='a@example.org')
        self.s5=Dataset.objects.create(nombre='S5 prueba',escenario='S5',ruta_relativa='s5.npz')
        self.s7=Dataset.objects.create(nombre='S7 prueba',escenario='S7',ruta_relativa='s7.npz')
        self.exp=Experimento.objects.create(nombre='Experimento A',propietario=self.a,origen=self.s5,destino=self.s7)
    def test_sin_sesion_redirecciona(self):
        self.assertEqual(self.client.get(reverse('dashboard')).status_code,302)
        self.assertEqual(self.client.get(reverse('detalle',args=[self.exp.pk])).status_code,302)
    def test_propietario_y_otro_usuario(self):
        self.client.force_login(self.b)
        self.assertEqual(self.client.get(reverse('detalle',args=[self.exp.pk])).status_code,404)
        self.assertEqual(self.client.post(reverse('demo',args=[self.exp.pk])).status_code,404)
        self.client.force_login(self.a)
        self.assertEqual(self.client.get(reverse('detalle',args=[self.exp.pk])).status_code,200)
    def test_admin_ve_experimento(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('detalle',args=[self.exp.pk])).status_code,200)
    def test_sin_get_para_modificar(self):
        self.client.force_login(self.a)
        self.assertEqual(self.client.get(reverse('demo',args=[self.exp.pk])).status_code,405)
    def test_investigador_no_accede_admin(self):
        self.client.force_login(self.a)
        self.assertEqual(self.client.get('/admin/').status_code,302)

    def test_demo_completa_exportacion(self):
        self.client.force_login(self.a)
        response=self.client.post(reverse('demo',args=[self.exp.pk]))
        self.assertEqual(response.status_code,302)
        self.exp.refresh_from_db()
        self.assertEqual(self.exp.estado,'DEMO_COMPLETADA')
        self.assertEqual(list(self.exp.resultados.order_by('k').values_list('k',flat=True)),[0,1,5,10])
        response=self.client.get(reverse('exportar',args=[self.exp.pk]))
        self.assertEqual(response.status_code,200)
        self.assertIn(b'SINTETICO',response.content)
        self.client.force_login(self.b)
        self.assertEqual(self.client.get(reverse('exportar',args=[self.exp.pk])).status_code,404)

    def test_post_requiere_csrf(self):
        from django.test import Client
        client=Client(enforce_csrf_checks=True)
        client.force_login(self.a)
        self.assertEqual(client.post(reverse('demo',args=[self.exp.pk])).status_code,403)

    def test_real_requiere_propietario_y_post(self):
        self.client.force_login(self.b)
        self.assertEqual(self.client.post(reverse('ejecutar_real',args=[self.exp.pk])).status_code,404)
        self.client.force_login(self.a)
        self.assertEqual(self.client.get(reverse('ejecutar_real',args=[self.exp.pk])).status_code,405)
        self.client.post(reverse('ejecutar_real',args=[self.exp.pk]))
        self.assertEqual(self.exp.resultados.count(),0)

    def test_graficos_y_autorizacion(self):
        self.client.force_login(self.a)
        self.client.post(reverse('demo',args=[self.exp.pk]))
        url=reverse('grafico',args=[self.exp.pk])
        for query in ('', '?tipo=confusion&k=0', '?tipo=confusion&k=10'):
            response=self.client.get(url+query)
            self.assertEqual(response.status_code,200)
            self.assertIn('image/svg+xml',response['Content-Type'])
            self.assertIn(b'<svg',response.content)
        self.assertEqual(self.client.get(url+'?tipo=confusion&k=2').status_code,404)
        self.client.force_login(self.b)
        self.assertEqual(self.client.get(url).status_code,404)

    def test_real_publica_comparador_y_protege_sus_artefactos(self):
        import json
        from django.conf import settings
        from src.pfc07.sintetico import generar_ejemplo

        generar_ejemplo(settings.DATA_DIR, n_por_clase=35)
        for dataset in (self.s5, self.s7):
            dataset.ruta_relativa = f'{dataset.escenario}_SINTETICO.npz'
            dataset.revisado = True
            dataset.save()
            meta = {'naturaleza': 'CSI_REAL_BASELINE_EXPLORATORIO', 'antena': 0,
                    'receptor': 'a', 'longitud_paquetes': 128, 'salto_paquetes': 128, 'bins': 8}
            (settings.DATA_DIR / dataset.ruta_relativa).with_suffix('.json').write_text(json.dumps(meta))
        self.client.force_login(self.a)
        self.assertEqual(self.client.post(reverse('ejecutar_real', args=[self.exp.pk])).status_code, 302)
        self.assertContains(self.client.get(reverse('detalle', args=[self.exp.pk])), 'Ajuste convencional')
        consulta = '?metodo=ajuste_convencional'
        csv = reverse('exportar', args=[self.exp.pk]) + consulta
        matriz = reverse('grafico', args=[self.exp.pk]) + consulta + '&tipo=confusion&k=5'
        self.assertContains(self.client.get(csv), 'ajuste_convencional')
        self.assertContains(self.client.get(matriz), '<svg')
        from unittest.mock import patch
        from src.pfc07.evaluacion import ejecutar_experimento

        url_real = reverse('ejecutar_real', args=[self.exp.pk])
        url_base = reverse('grafico', args=[self.exp.pk]) + '?tipo=confusion&k=5'
        self.exp.refresh_from_db()
        ajuste_previo = self.exp.ajuste_id

        def fallar_despues_de_escribir(*args, **kwargs):
            ruta = args[2]
            ejecutar_experimento(*args, **kwargs)
            if kwargs.get('metodo') != 'ajuste_convencional':
                (ruta / 'confusion_5shot.csv').unlink()
                raise OSError('falla de escritura simulada')

        with patch('src.pfc07.evaluacion.ejecutar_experimento', side_effect=fallar_despues_de_escribir):
            self.assertEqual(self.client.post(url_real).status_code, 302)
        siguiente = self.client.get(url_base)
        self.assertContains(siguiente, '<svg')
        self.exp.refresh_from_db()
        self.assertEqual(self.exp.ajuste_id, ajuste_previo)
        self.assertEqual(self.exp.naturaleza, 'CSI_REAL_BASELINE_EXPLORATORIO')

        self.client.force_login(self.b)
        self.assertEqual(self.client.get(csv).status_code, 404)
        self.assertEqual(self.client.get(matriz).status_code, 404)
        self.client.force_login(self.a)
        self.client.post(reverse('demo', args=[self.exp.pk]))
        self.assertEqual(self.client.get(csv).status_code, 404)
