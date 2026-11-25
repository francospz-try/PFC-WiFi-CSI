from django.urls import path
from . import views
urlpatterns=[path('',views.dashboard,name='dashboard'),path('datasets/',views.datasets,name='datasets'),path('experimentos/',views.experimentos,name='experimentos'),path('experimentos/nuevo/',views.nuevo_experimento,name='nuevo_experimento'),path('experimentos/<int:pk>/',views.detalle,name='detalle'),path('experimentos/<int:pk>/demo/',views.demo,name='demo'),path('experimentos/<int:pk>/exportar/',views.exportar,name='exportar')]

urlpatterns += [path('experimentos/<int:pk>/real/',views.ejecutar_real,name='ejecutar_real')]

urlpatterns += [path('experimentos/<int:pk>/grafico/', views.grafico, name='grafico')]

from . import csi_views
urlpatterns += [
path('captura-csi/',csi_views.panel,name='csi_panel'),
path('captura-csi/grafico/',csi_views.graph,name='csi_graph'),
path('captura-csi/capturar/',csi_views.capture,name='csi_capture'),
path('captura-csi/firmware/',csi_views.firmware,name='csi_firmware'),
path('captura-csi/datos/<str:name>/',csi_views.download,name='csi_download'),
]

from . import reconocer_views
urlpatterns += [path('captura-csi/reconocer/',reconocer_views.panel,name='csi_recognize'),path('captura-csi/ensenar/',reconocer_views.train,name='csi_train'),path('captura-csi/predecir/',reconocer_views.predict,name='csi_predict')]

from . import avance_views
urlpatterns += [path('avance-entregable/',avance_views.panel,name='avance_panel'),path('avance-entregable/ejecutar/',avance_views.run,name='avance_run'),path('avance-entregable/archivo/<str:name>/',avance_views.asset,name='avance_asset')]
