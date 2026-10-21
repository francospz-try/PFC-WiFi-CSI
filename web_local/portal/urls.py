from django.urls import path
from . import views
urlpatterns=[path('',views.dashboard,name='dashboard'),path('datasets/',views.datasets,name='datasets'),path('experimentos/',views.experimentos,name='experimentos'),path('experimentos/nuevo/',views.nuevo_experimento,name='nuevo_experimento'),path('experimentos/<int:pk>/',views.detalle,name='detalle'),path('experimentos/<int:pk>/demo/',views.demo,name='demo'),path('experimentos/<int:pk>/exportar/',views.exportar,name='exportar')]

urlpatterns += [path('experimentos/<int:pk>/real/',views.ejecutar_real,name='ejecutar_real')]

urlpatterns += [path('experimentos/<int:pk>/grafico/', views.grafico, name='grafico')]
