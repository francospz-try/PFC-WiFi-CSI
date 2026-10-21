from django.contrib import admin
from django.contrib.auth import get_user_model
from django.shortcuts import render
from .models import Dataset, Experimento

def inicio_admin(request):
    usuarios = get_user_model().objects.order_by('-is_superuser', 'username') if request.user.has_perm('auth.view_user') else get_user_model().objects.none()
    context = {**admin.site.each_context(request), 'title': 'Administración', 'cuentas': usuarios[:50], 'total_usuarios': usuarios.count(), 'total_datasets': Dataset.objects.count() if request.user.has_perm('portal.view_dataset') else None, 'total_experimentos': Experimento.objects.count() if request.user.has_perm('portal.view_experimento') else None}
    return render(request, 'admin/inicio_pfc.html', context)
