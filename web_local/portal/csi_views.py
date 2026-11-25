from .csi_fechas import con_fechas
import json
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

_capture_lock=threading.Lock()

def root():
    return settings.PROJECT_DIR/'datos_locales'/'csi_piloto'

def session(name):
    if not name or Path(name).name != name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in name):
        raise Http404('Sesion invalida')
    p=root()/name
    if not (p/'metadata.json').is_file(): raise Http404('Sesion no disponible')
    return p

class CaptureForm(forms.Form):
    activity=forms.ChoiceField(label='Actividad que realizaras',choices=[('','Selecciona la actividad'),('de_pie','Persona quieta de pie'),('sentado','Persona quieta sentada'),('caminar','Persona caminando por un recorrido lateral'),('no_controlada','Actividad no controlada / solo comprobar enlace')],help_text='Es tu anotacion de lo que haras; no una prediccion del sistema. Mantén la misma actividad durante toda la grabacion.')
    capture_use=forms.ChoiceField(label='Uso de esta captura',choices=[('','Selecciona el uso'),('aprender','Enseñar al modelo con actividad etiquetada'),('reconocer','Probar reconocimiento con una grabacion nueva'),('enlace','Comprobar recepcion, sin etiqueta de actividad')],help_text='Las pruebas de reconocimiento se reservan: no se usan para enseñar al modelo.')
    dataset=forms.CharField(label='Dataset propio',initial='casa_habitacion',max_length=80,help_text='Usa el mismo nombre para agrupar las grabaciones de tu campaña.')
    room=forms.CharField(label='Ambiente',initial='habitacion',max_length=80)
    seconds=forms.IntegerField(label='Duracion (segundos)',initial=60,min_value=5,max_value=60)
    distance=forms.FloatField(label='Separacion (m)',initial=1.4,min_value=.1,max_value=20)
    tx_height=forms.FloatField(label='Altura TX (m)',initial=1.4,min_value=.1,max_value=5)
    rx_height=forms.FloatField(label='Altura RX (m)',initial=.8,min_value=.1,max_value=5)
    notes=forms.CharField(label='Observaciones',required=False,max_length=600,widget=forms.Textarea(attrs={'rows':2}))

    def clean(self):
        d=super().clean()
        activities={'de_pie':('quieto','de_pie_lateral'),'sentado':('quieto','sentado'),'caminar':('caminar','caminata_lateral'),'no_controlada':('sin_etiquetar','otro')}
        if d.get('activity') in activities:
            label,posture=activities[d['activity']]
            if d.get('capture_use')=='aprender' and d['activity']=='no_controlada':
                raise forms.ValidationError('Para enseñar selecciona una actividad concreta.')
            d['label']=label if d.get('capture_use')=='aprender' else 'sin_etiquetar'
            d['posture']=posture
        return d

@staff_member_required(login_url='login')
def panel(request):
    sessions=[]; errors=[]
    if root().exists():
        for p in sorted(root().glob('*/metadata.json'),reverse=True):
            try:
                d=con_fechas(json.loads(p.read_text(encoding='utf-8')));d['folder']=p.parent.name;sessions.append(d)
            except (ValueError,OSError): errors.append(p.parent.name)
    sessions.sort(key=lambda d:d.get('start_utc',''),reverse=True)
    a=request.GET.get('a','piloto_20261030_quieto_pie_01')
    b=request.GET.get('b','piloto_20261030_caminar_lateral_01')
    summary=[]
    if a and b:
        try:
            from src.pfc07.csi_piloto import comparar
            fig,summary=comparar(session(a),session(b));fig.clear()
        except (ValueError,OSError,KeyError,Http404): pass
    initial={}
    if sessions:
        latest=sessions[0]
        for field,key in [('dataset','dataset'),('room','room'),('seconds','seconds'),('distance','distance_m'),('tx_height','height_tx_m'),('rx_height','height_rx_m')]:
            if latest.get(key) is not None: initial[field]=latest[key]
    groups={}
    for item in sessions:
        dataset=item.get('dataset','piloto_inicial')
        group=groups.setdefault(dataset,dict(dataset=dataset,total=0,aprender=0,reconocer=0,enlace=0,legacy=0))
        group['total']+=1
        purpose=item.get('capture_use')
        group[purpose if purpose in ('aprender','reconocer','enlace') else 'legacy']+=1
    return render(request,'csi_piloto.html',dict(sessions=sessions,errors=errors,form=CaptureForm(initial=initial),a=a,b=b,summary=summary,dataset_summary=[groups[k] for k in sorted(groups)]))

@staff_member_required(login_url='login')
def graph(request):
    from src.pfc07.csi_piloto import comparar
    from src.pfc07.graficos import exportar_figura
    try: fig,_=comparar(session(request.GET.get('a')),session(request.GET.get('b')))
    except (ValueError,OSError,KeyError) as e: return HttpResponse(str(e),status=400)
    return HttpResponse(exportar_figura(fig,'png'),content_type='image/png')

@staff_member_required(login_url='login')
def download(request,name):
    return FileResponse((session(name)/'raw.log').open('rb'),as_attachment=True,filename=name+'.log')

@staff_member_required(login_url='login')
@require_POST
def capture(request):
    form=CaptureForm(request.POST)
    if not form.is_valid():
        messages.error(request,'Revisa los datos de captura: '+str(form.errors.as_text()))
        return redirect('csi_panel')
    if not _capture_lock.acquire(blocking=False):
        messages.error(request,'Ya hay una captura en curso. Espera a que termine.')
        return redirect('csi_panel')
    try:
        d=form.cleaned_data
        name=datetime.now(timezone.utc).strftime('web_%Y%m%dT%H%M%S_%f')+'_'+d['label']
        cmd=[sys.executable,str(settings.PROJECT_DIR/'herramientas'/'captura_sesion.py'),
             '--port','COM7','--seconds',str(d['seconds']),'--root',str(root()),
             '--capture-use',d['capture_use'],'--declared-activity',d['activity'],'--posture',d['posture'],'--dataset',d['dataset'],'--session',name,'--room',d['room'],'--label',d['label'],
             '--distance-m',str(d['distance']),'--height-tx-m',str(d['tx_height']),
             '--height-rx-m',str(d['rx_height']),
             '--notes',f"Operador web: {request.user.pk}. Postura/recorrido declarado: {d['posture']}. "+d['notes']]
        result=subprocess.run(cmd,capture_output=True,text=True,timeout=d['seconds']+20)
        if result.returncode:
            messages.error(request,'La captura fallo o no recibio CSI. Comprueba COM7 y que ningun otro programa lo tenga abierto.')
        else: messages.success(request,'Captura terminada: '+name+'. Ya puedes moverte.')
    except (OSError,subprocess.TimeoutExpired):
        messages.error(request,'No se pudo completar la captura. Revisa conexion y dependencias.')
    finally: _capture_lock.release()
    return redirect('csi_panel')

@staff_member_required(login_url='login')
def firmware(request):
    base=settings.PROJECT_DIR/'firmware'/'esp32c6'
    code={name:(base/name).read_text(encoding='utf-8') for name in ['tx_app_main.c','rx_app_main.c']}
    return render(request,'csi_firmware.html',{'code':code})
