from django.contrib import admin
from .models import Dataset,Experimento,Resultado
@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display=('nombre','escenario','receptor','revisado','creado')
@admin.register(Experimento)
class ExperimentoAdmin(admin.ModelAdmin):
    list_display=('nombre','propietario','origen','destino','estado','naturaleza')
    readonly_fields=('propietario','estado','naturaleza')
    def save_model(self,request,obj,form,change):
        if not change: obj.propietario=request.user
        obj.full_clean()
        super().save_model(request,obj,form,change)
@admin.register(Resultado)
class ResultadoAdmin(admin.ModelAdmin):
    list_display=('experimento','k','f1_macro','accuracy')
    def has_add_permission(self,request): return False
    def has_change_permission(self,request,obj=None): return False


admin.site.site_header = 'WiFi CSI HAR'
admin.site.site_title = 'Administración · WiFi CSI HAR'
admin.site.index_title = 'Administración'
admin.site.enable_nav_sidebar = False

from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html

@admin.display(description='Rol')
def rol_cuenta(obj):
    return 'Administrador' if obj.is_superuser else ('Personal autorizado' if obj.is_staff else 'Investigador')

@admin.display(description='Nombre completo')
def nombre_cuenta(obj):
    return obj.get_full_name() or 'Sin nombre registrado'

class CuentaAdmin(UserAdmin):
    list_display = ('username', nombre_cuenta, rol_cuenta, 'is_active', 'last_login')
    list_filter = ('is_active', 'is_superuser', 'is_staff')
    search_fields = ('username', 'first_name', 'last_name', 'email')

admin.site.unregister(get_user_model())
admin.site.register(get_user_model(), CuentaAdmin)
