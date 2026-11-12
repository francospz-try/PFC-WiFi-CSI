"""Prototipos exploratorios. Validacion por grabacion completa, nunca por ventanas aleatorias."""
import hashlib
from io import BytesIO
import json
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
from .csi_piloto import leer_captura

MODES={'binario':('quietud','caminar'), 'posturas':('quieto_de_pie','sentado','caminar')}

def actividad(meta,mode):
    label=meta.get('label'); posture=meta.get('posture','')
    notes=meta.get('notes','').lower()
    if label=='caminar': return 'caminar'
    if label!='quieto': return None
    if mode=='binario': return 'quietud'
    if posture=='sentado' or 'declarado: sentado.' in notes: return 'sentado'
    if posture=='de_pie_lateral' or 'de pie quieto' in notes or 'declarado: de_pie_lateral.' in notes: return 'quieto_de_pie'
    return None

def features(folder):
    meta,t,amp=leer_captura(folder)
    q=meta.get('quality',{})
    n=q.get('valid_csi',0);gaps=q.get('sequence_gaps',0)
    # Umbrales de ingenieria iniciales, no optimizados para maximizar exactitud.
    if q.get('observed_hz',0)<60 or gaps/max(1,n+gaps)>.10:
        raise ValueError('Recepcion insuficiente: se requieren >=60 registros/s y <=10% de saltos nominales.')
    if q.get('malformed_csi',0)/max(1,n)>.01:
        raise ValueError('Mas del 1% de registros incompletos.')
    x=np.log1p(amp); rows=[]
    for second in range(2,int(t[-1])-2):
        idx=np.flatnonzero((t>=second)&(t<second+1))
        if len(idx)<60 or np.max(np.diff(t[idx]))>.1: continue
        z=x[idx]; variation=np.std(z,axis=0)
        diff=np.abs(np.diff(z,axis=0))
        rows.append([*np.percentile(variation,[25,50,75,90]),float(np.median(diff)),float(np.percentile(diff,90))])
    if len(rows)<3: raise ValueError('Menos de tres ventanas utilizables tras excluir transiciones y huecos.')
    return meta,np.asarray(rows)

def fit(records,classes):
    allx=np.vstack([r['x'] for r in records])
    mean=allx.mean(axis=0);scale=np.maximum(allx.std(axis=0),1e-6)
    # Igual peso por grabacion al formar cada centro de clase.
    centers=np.array([np.mean([((r['x']-mean)/scale).mean(axis=0) for r in records if r['label']==c],axis=0) for c in classes])
    return mean,scale,centers

def infer(x,model,classes):
    mean,scale,centers=model
    distances=np.sum((((x-mean)/scale)[:,None,:]-centers[None,:,:])**2,axis=2)
    return np.asarray(classes)[distances.argmin(axis=1)]

def train(root,out,mode,dataset):
    classes=MODES[mode];records=[];excluded=[]
    for folder in sorted(Path(root).iterdir()):
        if not (folder/'metadata.json').exists(): continue
        meta=json.loads((folder/'metadata.json').read_text(encoding='utf-8'))
        if meta.get('dataset','piloto_inicial') != dataset: continue
        # Legacy sessions without a purpose retain their original label semantics.
        if meta.get('capture_use') in ('reconocer','enlace'):
            excluded.append(dict(session=folder.name,reason='Reservada por uso: '+meta['capture_use']))
            continue
        label=actividad(meta,mode)
        if not label: continue
        try:
            meta,x=features(folder)
            records.append(dict(name=folder.name,label=label,x=x,meta=meta))
        except (ValueError,OSError) as exc: excluded.append(dict(session=folder.name,reason=str(exc)))
    counts={c:sum(r['label']==c for r in records) for c in classes}
    if not all(counts.values()):
        raise ValueError('Faltan grabaciones utilizables por clase: '+str(counts)+'. Descartadas: '+str(excluded))
    rooms={r['meta'].get('room') for r in records}
    if len(rooms)!=1: raise ValueError('El piloto requiere un solo ambiente por dataset; separa las campañas.')
    report=dict(trained_at_utc=datetime.now(timezone.utc).isoformat(),mode=mode,dataset=dataset,classes=list(classes),sessions=[r['name'] for r in records],
                counts=counts,excluded=excluded,room=next(iter(rooms)),evaluation=None,
                method='Prototipos de seis indicadores temporales; sin probabilidades calibradas.',
                quality_rules='>=60Hz, <=10% saltos; ventanas >=60 muestras, hueco <=100ms; excluir 2s iniciales y finales.',
                scope='Piloto local. No demuestra adaptacion de dominio ni reconocimiento general de posturas.')
    if min(counts.values())>=2:
        test=[next(r for r in reversed(records) if r['label']==c) for c in classes]
        testnames={r['name'] for r in test};training=[r for r in records if r['name'] not in testnames]
        model=fit(training,classes)
        matrix=np.zeros((len(classes),len(classes)),dtype=int)
        per_session=[]
        for r in test:
            pred=infer(r['x'],model,classes)
            for c in classes: matrix[list(classes).index(r['label']),list(classes).index(c)]+=int(np.sum(pred==c))
            per_session.append(dict(session=r['name'],true=r['label'],window_accuracy=float(np.mean(pred==r['label']))))
        report['evaluation']=dict(training=[r['name'] for r in training],test=sorted(testnames),
            accuracy_percent=float(100*np.trace(matrix)/matrix.sum()),confusion=matrix.tolist(),per_session=per_session,
            note='Exactitud por ventanas de grabaciones reservadas. No son ventanas independientes ni evidencia poblacional. Modelo final reajustado con todas las sesiones.')
    model=fit(records,classes)
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    np.savez(out/(mode+'.npz'),mean=model[0],scale=model[1],centers=model[2])
    (out/(mode+'.json')).write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    return report

def predict(folder,out,mode):
    out=Path(out);report=json.loads((out/(mode+'.json')).read_text(encoding='utf-8'))
    if Path(folder).name in report['sessions']: raise ValueError('Esta grabacion se uso para aprender. Captura una nueva como Prueba de enlace para reconocerla.')
    meta,x=features(folder)
    if meta.get('room')!=report['room']: raise ValueError('El ambiente es diferente al de calibracion; esta prueba local no valida transferencia.')
    if meta.get('dataset','piloto_inicial')!=report['dataset']: raise ValueError('Selecciona una captura del mismo dataset del modelo.')
    model_bytes=(out/(mode+'.npz')).read_bytes()
    with np.load(BytesIO(model_bytes),allow_pickle=False) as z: model=tuple(z[k] for k in ['mean','scale','centers'])
    pred=infer(x,model,report['classes'])
    proportions={c:float(100*np.mean(pred==c)) for c in report['classes']}
    return dict(model_mode=mode,model_dataset=report['dataset'],model_trained_at_utc=report.get('trained_at_utc'),
                model_sha256=hashlib.sha256(model_bytes).hexdigest(),
                declared_activity=meta.get('declared_activity',meta.get('label','Sin declaracion')),
                session=Path(folder).name,result=max(proportions,key=proportions.get),percentages=proportions,
                windows=len(pred),note='Porcentaje de ventanas asignadas por el modelo, no confianza ni exactitud. Puede confundir otros movimientos con las clases conocidas.')
