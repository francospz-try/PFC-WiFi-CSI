from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import Dataset,Experimento
U=get_user_model()
class SeguridadTest(TestCase):
    def setUp(self):
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
