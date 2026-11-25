import json,subprocess,sys,threading,hashlib
from pathlib import Path
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse,Http404
from django.shortcuts import render,redirect
from django.views.decorators.http import require_POST

_lock=threading.Lock()
def auditroot():return settings.PROJECT_DIR/'outputs'/'auditoria_publicos_20261030'
def output():return settings.PROJECT_DIR/'outputs'/'entregable_30'/'demo'
def read(p):return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None

@staff_member_required(login_url='login')
def panel(request):
    audit=read(auditroot()/'auditoria.json');complete=read(auditroot()/'resumen_lectura_15.json');manifest=read(output()/'manifest.json')
    artifact=output()/'ventanas_demo.npz'
    trace_ok=False
    if manifest and artifact.is_file() and manifest.get('script_hashes'):
        try:
            trace_ok=hashlib.sha256(artifact.read_bytes()).hexdigest()==manifest.get('npz_sha256') and all(hashlib.sha256((settings.PROJECT_DIR/name).read_bytes()).hexdigest()==digest for name,digest in manifest['script_hashes'].items())
        except OSError:trace_ok=False
    # Peso total 100. Solo se acreditan aqui componentes con criterio entero cumplido.
    criteria=[dict(name='Auditoria del conjunto seleccionado',weight=15,done=bool(complete and complete['files']==15 and complete['all_crc_verified'] and complete['nonfinite_components']==0)),
      dict(name='Lectura de CSI real y visualizacion',weight=15,done=bool(manifest and artifact.is_file() and manifest['crc_verified'] and manifest['finite'])),
      dict(name='Preprocesamiento definitivo de tesis',weight=15,done=False),
      dict(name='Modelo base de tesis',weight=15,done=False),dict(name='Adaptacion few-shot comparativa',weight=15,done=False),
      dict(name='Evaluacion y sensibilidad',weight=10,done=False),dict(name='Validacion propia ESP32',weight=10,done=False),
      dict(name='Trazabilidad de la demostracion',weight=5,done=trace_ok)]
    progress=sum(x['weight'] for x in criteria if x['done'])
    return render(request,'avance_entregable.html',dict(audit=audit,complete=complete,manifest=manifest,criteria=criteria,progress=progress))

@staff_member_required(login_url='login')
@require_POST
def run(request):
    if not _lock.acquire(False):
        messages.warning(request,'La lectura ya esta en curso.');return redirect('avance_panel')
    try:
        member=request.POST.get('member','S5/S5a_A.mat')
        audit=read(auditroot()/'auditoria.json')
        if audit is None:
            raise ValueError('Primero genera el inventario con herramientas/auditar_publicos.py; consulta DATOS_REALES.md.')
        allowed={r['member'] for r in audit['selected']}
        if member not in allowed:raise ValueError('Seleccion no permitida')
        result=subprocess.run([sys.executable,str(settings.PROJECT_DIR/'herramientas/demo_entregable.py'),'--member',member],capture_output=True,text=True,timeout=120)
        if result.returncode:raise ValueError('No se pudo completar la lectura; comprueba la ubicación de los ZIP configurada en PFC_PUBLIC_CSI_DIR.')
        messages.success(request,'Lectura real terminada; ventana, grafico y manifiesto regenerados.')
    except (ValueError,OSError,subprocess.TimeoutExpired) as exc:messages.error(request,str(exc))
    finally:_lock.release()
    return redirect('avance_panel')

@staff_member_required(login_url='login')
def asset(request,name):
    allowed={'grafico':'lectura_y_ventanas.png','ventanas':'ventanas_demo.npz','manifest':'manifest.json'}
    if name not in allowed:raise Http404()
    p=output()/allowed[name]
    if not p.is_file():raise Http404()
    return FileResponse(p.open('rb'),as_attachment=name!='grafico',filename=p.name)
