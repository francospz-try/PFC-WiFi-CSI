from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
class AdminDisenoTest(TestCase):
    def setUp(self):
        self.admin=get_user_model().objects.create_superuser(username='admin_prueba',email='')
        self.investigador=get_user_model().objects.create_user(username='investigador_prueba')
    def test_resumen_y_formularios_admin(self):
        self.client.force_login(self.admin)
        for ruta in ('/admin/','/admin/auth/user/','/admin/auth/user/add/',f'/admin/auth/user/{self.investigador.pk}/change/'):
            r=self.client.get(ruta)
            self.assertEqual(r.status_code,200)
            self.assertContains(r,'portal/admin-pfc.css')
        self.assertContains(self.client.get('/admin/'),'Cuentas registradas')
    def test_restringido_a_administracion(self):
        self.assertEqual(self.client.get('/admin/').status_code,302)
        self.client.force_login(self.investigador)
        self.assertEqual(self.client.get('/admin/').status_code,302)
    def test_staff_sin_permiso_no_lista_cuentas(self):
        self.investigador.is_staff=True;self.investigador.save()
        self.client.force_login(self.investigador)
        r=self.client.get('/admin/')
        self.assertEqual(r.status_code,200)
        self.assertNotContains(r,'admin_prueba')
    def test_estilos_disponibles(self):
        self.assertIsNotNone(finders.find('admin/css/base.css'))
        self.assertIsNotNone(finders.find('portal/admin-pfc.css'))
