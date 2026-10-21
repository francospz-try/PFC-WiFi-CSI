"""Portal con autorizaciones en servidor. Demo claramente SINTÃƒâ€°TICA."""
import csv, hashlib
from pathlib import Path
from django.views.generic import FormView
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseForbidden
from django.conf import settings
from django.views.decorators.http import require_POST
from .models import Dataset, Experimento, Resultado
from .forms import ExperimentoForm

class LoginLimitView(LoginView):
    # Contador de intentos por IP + usuario. Solo recomendado para localhost.
    def dispatch(self, request, *args, **kwargs):
        if request.method=='POST':
            user=request.POST.get('username','')[:150].strip().lower()
            ip=request.META.get('REMOTE_ADDR','')
            self.rate_key='intentos_'+hashlib.sha256((ip+'|'+user).encode()).hexdigest()
            if cache.get(self.rate_key,0)>=5:
                return HttpResponse('Demasiados intentos. Espera 15 minutos.',status=429)
            cache.set(self.rate_key,cache.get(self.rate_key,0)+1,900)
        return super().dispatch(request,*args,**kwargs)
    def form_valid(self,form):
        if hasattr(self,'rate_key'): cache.delete(self.rate_key)
        return super().form_valid(form)

def visibles(request):
    q=Experimento.objects.select_related('origen','destino','propietario')
    return q if request.user.is_staff else q.filter(propietario=request.user)

@login_required
def dashboard(request):
    return render(request,'dashboard.html',{'total':visibles(request).count(),'datasets':Dataset.objects.count(),'experimentos':visibles(request).order_by('-creado')[:10]})

@login_required
def datasets(request):
    return render(request,'datasets.html',{'datasets':Dataset.objects.order_by('escenario','nombre')})

@login_required
def experimentos(request):
    return render(request,'experimentos.html',{'experimentos':visibles(request).order_by('-creado')})

@login_required
def nuevo_experimento(request):
    form=ExperimentoForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        exp=form.save(commit=False)
        exp.propietario=request.user
        exp.full_clean()
        exp.save()
        messages.success(request,'Experimento registrado; sin entrenamiento ejecutado.')
        return redirect('detalle',pk=exp.pk)
    return render(request,'form.html',{'form':form})

@login_required
def detalle(request,pk):
    exp=get_object_or_404(visibles(request),pk=pk)
    carpeta = settings.OUTPUT_DIR / f'experimento_{pk}_real' if exp.naturaleza == 'CSI_REAL_BASELINE_EXPLORATORIO' else settings.OUTPUT_DIR / f'experimento_{pk}_simulado' / 'resultados'
    matrices = [k for k in (0, 1, 5, 10) if (carpeta / f'confusion_{k}shot.csv').is_file()]
    return render(request,'detalle.html',{'exp':exp,'resultados':exp.resultados.order_by('k'), 'matrices': matrices})

@login_required
@require_POST
def demo(request,pk):
    exp=get_object_or_404(visibles(request),pk=pk)
    # DemostraciÃƒÂ³n controlada de Python; no se usan archivos arbitrarios ni datos reales.
    from src.pfc07.sintetico import generar_ejemplo
    from src.pfc07.procesamiento import leer_features
    from src.pfc07.evaluacion import ejecutar_experimento
    base=settings.OUTPUT_DIR / f'experimento_{exp.pk}_simulado'
    generar_ejemplo(base/'datos')
    origen=leer_features(base/'datos'/'S5_SINTETICO.npz')
    destino=leer_features(base/'datos'/'S7_SINTETICO.npz')
    filas=ejecutar_experimento(origen,destino,base/'resultados',semilla=exp.semilla,
         etiqueta='SINTETICO_PRUEBA_SOFTWARE_NO_CSI_REAL')
    for r in filas:
        Resultado.objects.update_or_create(experimento=exp,k=r['shots_por_clase'],defaults={k:r[k] for k in ('accuracy','precision_macro','recall_macro','f1_macro')})
    exp.estado='DEMO_COMPLETADA';exp.naturaleza='SINTETICO_PRUEBA_SOFTWARE';exp.save(update_fields=['estado','naturaleza'])
    messages.warning(request,'EvaluaciÃƒÂ³n SINTÃƒâ€°TICA. No es evidencia de HAR sobre Wi-Fi CSI real.')
    return redirect('detalle',pk=exp.pk)

@login_required
def exportar(request,pk):
    exp=get_object_or_404(visibles(request),pk=pk)
    resp=HttpResponse(content_type='text/csv')
    resp['Content-Disposition']=f'attachment; filename="experimento_{exp.pk}_resultados.csv"'
    w=csv.writer(resp)
    w.writerow(['naturaleza','k','accuracy','precision_macro','recall_macro','f1_macro'])
    for r in exp.resultados.order_by('k'):
        w.writerow([exp.naturaleza,r.k,r.accuracy,r.precision_macro,r.recall_macro,r.f1_macro])
    return resp

@login_required
@require_POST
def ejecutar_real(request,pk):
    import json
    from django.db import transaction
    from src.pfc07.procesamiento import leer_features
    from src.pfc07.evaluacion import ejecutar_experimento
    exp=get_object_or_404(visibles(request),pk=pk)
    try:
        datos=[];metadatos=[]
        for dataset in (exp.origen,exp.destino):
            if not dataset.revisado:raise ValueError('Dataset pendiente de revisiÃƒÂ³n')
            ruta=(settings.DATA_DIR/dataset.ruta_relativa).resolve()
            if not ruta.is_relative_to(settings.DATA_DIR) or ruta.suffix!='.npz':raise ValueError('Ruta no permitida')
            meta=json.loads(ruta.with_suffix('.json').read_text(encoding='utf-8'))
            if meta.get('naturaleza')!='CSI_REAL_BASELINE_EXPLORATORIO':raise ValueError('No es un dataset real preparado')
            d=leer_features(ruta)
            if str(d['escenario'])!=dataset.escenario or str(d['receptor'])!=dataset.receptor:raise ValueError('Metadatos incompatibles')
            datos.append(d);metadatos.append(meta)
        for campo in ('antena','receptor','longitud_paquetes','salto_paquetes','bins'):
            if metadatos[0][campo]!=metadatos[1][campo]:raise ValueError('Preprocesamiento incompatible')
        filas=ejecutar_experimento(*datos,settings.OUTPUT_DIR/f'experimento_{pk}_real',semilla=exp.semilla,etiqueta='CSI_REAL_BASELINE_EXPLORATORIO_BLOQUES_TEMPORALES')
        with transaction.atomic():
            for fila in filas:
                Resultado.objects.update_or_create(experimento=exp,k=fila['shots_por_clase'],defaults={c:fila[c] for c in ('accuracy','precision_macro','recall_macro','f1_macro')})
            exp.estado='REAL_COMPLETADO';exp.naturaleza='CSI_REAL_BASELINE_EXPLORATORIO';exp.save(update_fields=['estado','naturaleza'])
        messages.success(request,'EvaluaciÃƒÂ³n real completada. Protocolo exploratorio por bloques temporales.')
    except (ValueError,OSError,KeyError) as exc:
        messages.error(request,f'No se pudo ejecutar: {exc}')
    return redirect('detalle',pk=pk)


@login_required
def grafico(request, pk):
    from django.http import Http404
    import numpy as np
    from src.pfc07.graficos import figura_metricas, figura_confusion, exportar_figura
    exp = get_object_or_404(visibles(request), pk=pk)
    filas = list(exp.resultados.order_by('k').values('k', 'accuracy', 'precision_macro', 'recall_macro', 'f1_macro'))
    if not filas:
        raise Http404('TodavÃ­a no hay resultados')
    tipo = request.GET.get('tipo', 'metricas')
    if tipo == 'metricas':
        fig = figura_metricas(filas, f'{exp.origen.escenario} â†’ {exp.destino.escenario} Â· {exp.naturaleza}')
    elif tipo == 'confusion':
        try:
            k = int(request.GET.get('k', '0'))
        except ValueError:
            raise Http404('ConfiguraciÃ³n invÃ¡lida')
        if k not in (0, 1, 5, 10):
            raise Http404('ConfiguraciÃ³n invÃ¡lida')
        if exp.naturaleza == 'CSI_REAL_BASELINE_EXPLORATORIO':
            carpeta = settings.OUTPUT_DIR / f'experimento_{pk}_real'
        elif exp.naturaleza == 'SINTETICO_PRUEBA_SOFTWARE':
            carpeta = settings.OUTPUT_DIR / f'experimento_{pk}_simulado' / 'resultados'
        else:
            raise Http404('Sin artefactos de esta ejecuciÃ³n')
        ruta = carpeta / f'confusion_{k}shot.csv'
        if not ruta.is_file():
            raise Http404('La matriz no estÃ¡ disponible; vuelve a ejecutar el experimento')
        fig = figura_confusion(np.loadtxt(ruta, delimiter=','), k)
    else:
        raise Http404('GrÃ¡fico desconocido')
    response = HttpResponse(exportar_figura(fig), content_type='image/svg+xml')
    response['Cache-Control'] = 'private, no-store'
    if request.GET.get('descargar') == '1':
        response['Content-Disposition'] = f'attachment; filename="experimento_{pk}_{tipo}.svg"'
    return response
