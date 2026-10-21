from django.contrib import admin
from django.urls import path, include
from portal.views import LoginLimitView
from portal.admin_ui import inicio_admin
from django.contrib.auth.views import LogoutView
urlpatterns=[path('admin/',admin.site.admin_view(inicio_admin),name='inicio_admin'),path('admin/',admin.site.urls),path('login/',LoginLimitView.as_view(template_name='login.html'),name='login'),path('logout/',LogoutView.as_view(),name='logout'),path('',include('portal.urls'))]
