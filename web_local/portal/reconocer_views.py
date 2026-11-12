from .csi_fechas import con_fechas
import json
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render,redirect
from django.views.decorators.http import require_POST
from .csi_views import root,session

def modelroot(): return settings.PROJECT_DIR/'outputs'/'csi_reconocimiento'

@staff_member_required(login_url='login')
def panel(request):
    sessions=[];datasets=set();models=[];prediction=None
    if root().exists():
        for p in sorted(root().glob('*/metadata.json')):
            d=con_fechas(json.loads(p.read_text(encoding='utf-8')));d['folder']=p.parent.name;sessions.append(d);datasets.add(d.get('dataset','piloto_inicial'))
    sessions.sort(key=lambda d:d.get('start_utc',''),reverse=True)
    for mode in ['binario','posturas']:
        p=modelroot()/(mode+'.json')
        if p.exists(): models.append(json.loads(p.read_text(encoding='utf-8')))
    return render(request,'csi_reconocer.html',dict(sessions=sessions,datasets=sorted(datasets),models=models,prediction=request.session.pop('csi_prediction',None)))

@staff_member_required(login_url='login')
@require_POST
def train(request):
    from src.pfc07.csi_reconocimiento import train as fit
    mode=request.POST.get('mode')
    if mode not in ['binario','posturas']: return redirect('csi_recognize')
    try:
        report=fit(root(),modelroot(),mode,request.POST.get('dataset',''))
        messages.success(request,'Modelo piloto preparado. '+('Hay evaluacion por grabaciones reservadas.' if report['evaluation'] else 'Aun sin evaluacion: falta una segunda grabacion por clase.'))
    except (ValueError,OSError) as exc: messages.error(request,str(exc))
    return redirect('csi_recognize')

@staff_member_required(login_url='login')
@require_POST
def predict(request):
    from src.pfc07.csi_reconocimiento import predict as classify
    mode=request.POST.get('mode')
    if mode not in ['binario','posturas']: return redirect('csi_recognize')
    try: request.session['csi_prediction']=classify(session(request.POST.get('session')),modelroot(),mode)
    except (ValueError,OSError) as exc: messages.error(request,str(exc))
    return redirect('csi_recognize')
