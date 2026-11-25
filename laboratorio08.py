"""Evidencias reproducibles del Caso B; no altera el modelo ni los datos originales."""
import argparse
import csv
import hashlib
import json
import platform
import time
import os
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import sklearn
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from src.pfc07.procesamiento import leer_features
from src.pfc07.evaluacion import ejecutar_experimento, dividir_soporte_consulta
from src.pfc07.modelos import entrenar_base, prediccion_fewshot
from src.pfc07.config import CLASES


def guardar_csv(ruta, filas):
    with ruta.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(filas[0]));w.writeheader();w.writerows(filas)


def metricas(y,p):
    return dict(accuracy=float(accuracy_score(y,p)),
                precision_macro=float(precision_score(y,p,labels=CLASES,average='macro',zero_division=0)),
                recall_macro=float(recall_score(y,p,labels=CLASES,average='macro',zero_division=0)),
                f1_macro=float(f1_score(y,p,labels=CLASES,average='macro',zero_division=0)))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--datos',type=Path,default=Path('datos_locales'))
    parser.add_argument('--salida',type=Path,default=Path('outputs/laboratorio08'))
    parser.add_argument('--semillas',type=int,nargs='+',default=[7,21,42,84,123])
    args=parser.parse_args()
    # Nunca sobrescribir evidencias anteriores.
    salida=args.salida.resolve();salida.mkdir(parents=True,exist_ok=False)
    datos={s:leer_features(args.datos/f'{s}_real.npz') for s in ('S5','S6','S7')}
    metas={s:json.loads((args.datos/f'{s}_real.json').read_text(encoding='utf-8')) for s in datos}
    for s,m in metas.items():
        if m.get('naturaleza')!='CSI_REAL_BASELINE_EXPLORATORIO':
            raise ValueError(f'{s}: procedencia real no declarada')
        for k in ('antena','receptor','longitud_paquetes','salto_paquetes','bins'):
            if m[k]!=metas['S5'][k]:raise ValueError(f'Preprocesamiento incompatible: {k}')
    manifiesto={'fecha_utc':datetime.now(timezone.utc).isoformat(),
        'python':platform.python_version(),'numpy':np.__version__,'sklearn':sklearn.__version__,
        'plataforma':platform.platform(),'semillas':args.semillas,
        'hilos':{k:os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')},
        'sha256_codigo':{str(p.relative_to(Path(__file__).parent)):hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in [Path(__file__), *sorted((Path(__file__).parent/'src/pfc07').glob('*.py'))]},
        'sha256_entradas':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for s in datos for p in [args.datos/f'{s}_real.npz',args.datos/f'{s}_real.json']},
        'limites':['NPZ existentes; no se regeneraron desde MAT en esta ejecución',
                   'Una grabación por clase; ventanas no independientes',
                   'No se ajustan hiperparámetros con los resultados de evaluación',
                   'Las semillas varían el soporte, no representan sesiones nuevas']}
    (salida/'manifiesto.json').write_text(json.dumps(manifiesto,indent=2,ensure_ascii=False),encoding='utf-8')
    cruzadas=[]; variantes=[]; internas=[];rendimiento=[];robustez=[];explicaciones=[]
    for s,d in datos.items():
        train=[];test=[]
        for c in CLASES:
            idx=np.flatnonzero(d['y']==c);idx=idx[np.argsort(d['orden'][idx])]
            corte=int(len(idx)*0.6);train.extend(idx[:corte]);test.extend(idx[corte+4:])
        escala,modelo=entrenar_base(d['X'][train],d['y'][train])
        for nombre,idx in [('entrenamiento',train),('prueba_temporal',test)]:
            internas.append({'ambiente':s,'particion':nombre,'n':len(idx),**metricas(d['y'][idx],prediccion_fewshot(escala,modelo,d['X'][idx]))})
    for a,o in datos.items():
        for b,d in datos.items():
            if a==b:continue
            print(f'Evaluando {a} -> {b}',flush=True)
            soporte,consulta=dividir_soporte_consulta(d['y'],d['orden'])
            escala,modelo=entrenar_base(o['X'],o['y'])
            for semilla in args.semillas:
                filas=ejecutar_experimento(o,d,salida/f'{a}_{b}'/f'semilla_{semilla}',semilla=semilla,
                    etiqueta='CSI_REAL_EXPLORATORIO_LAB08')
                cruzadas.extend({'origen':a,'destino':b,'semilla':semilla,**f} for f in filas)
                rng=np.random.default_rng(semilla)
                perm={c:rng.permutation(v) for c,v in soporte.items()}
                for k in (1,5,10):
                    idx=[i for c in CLASES for i in perm[c][:k]]
                    pred=prediccion_fewshot(escala,modelo,d['X'][consulta],d['X'][idx],d['y'][idx],peso_prototipo=1)
                    variantes.append({'origen':a,'destino':b,'semilla':semilla,'k':k,'metodo':'solo_prototipos_diagnostico',**metricas(d['y'][consulta],pred)})
            Xq=d['X'][consulta];yq=d['y'][consulta]
            base=prediccion_fewshot(escala,modelo,Xq)
            for factor in (1,10,100):
                X=np.tile(Xq,(factor,1));prediccion_fewshot(escala,modelo,X)
                tiempos=[]
                for _ in range(7):
                    inicio=time.perf_counter();prediccion_fewshot(escala,modelo,X);tiempos.append(time.perf_counter()-inicio)
                tracemalloc.start()
                prediccion_fewshot(escala,modelo,X)
                _,pico=tracemalloc.get_traced_memory();tracemalloc.stop()
                rendimiento.append({'origen':a,'destino':b,'n':len(X),'repeticiones':7,
                    'mediana_ms':1000*float(np.median(tiempos)), 'p95_ms':1000*float(np.percentile(tiempos,95)),
                    'bytes_matriz_entrada':X.nbytes,'muestras_segundo':len(X)/float(np.median(tiempos)),
                    'pico_bytes_asignaciones_rastreadas':pico,
                    'alcance_memoria':'tracemalloc durante predicción; no RAM total ni todas las reservas nativas',
                    'tipo_carga':'ventanas_replicadas_solo_rendimiento'})
            rng=np.random.default_rng(42)
            for sigma in (0,0.01,0.05,0.1):
                perturbado=Xq+rng.normal(size=Xq.shape)*escala.scale_*sigma
                p=prediccion_fewshot(escala,modelo,perturbado)
                robustez.append({'origen':a,'destino':b,'ruido_sigma_origen':sigma,
                    'fraccion_predicciones_cambiadas':float(np.mean(p!=base)),**metricas(yq,p)})
            # Descomposición exacta del logit de la regresión logística, no de la mezcla Few-Shot.
            z=escala.transform(Xq[:1])[0];clase=base[0];j=list(modelo.classes_).index(clase)
            aportes=z*modelo.coef_[j];logit=float(aportes.sum()+modelo.intercept_[j])
            assert np.isclose(logit,modelo.decision_function(z[None,:])[0,j])
            for ix in np.argsort(np.abs(aportes))[-5:][::-1]:
                explicaciones.append({'origen':a,'destino':b,'indice_consulta':int(consulta[0]),
                    'real':str(yq[0]),'prediccion':str(clase),'grupo_subportadoras':int(ix//3+1),
                    'estadistico':('media_amplitud','desviacion_amplitud','cambio_temporal')[ix%3],
                    'aporte_logit':float(aportes[ix]),'logit_total':logit,
                    'alcance':'modelo_base; no causalidad física ni explicación de Few-Shot'})
            np.savetxt(salida/f'confusion_base_{a}_{b}.csv',confusion_matrix(yq,base,labels=CLASES),delimiter=',',fmt='%d')
    for nombre,filas in [('cross_domain',cruzadas),('prototipos_diagnostico',variantes),('validacion_temporal',internas),
                         ('rendimiento',rendimiento),('robustez',robustez),('explicaciones_base',explicaciones)]:
        guardar_csv(salida/f'{nombre}.csv',filas)
    resumen=[]
    for a in datos:
        for b in datos:
            if a==b:continue
            for k in (0,1,5,10):
                filas=[f for f in cruzadas if f['origen']==a and f['destino']==b and f['shots_por_clase']==k]
                resumen.append({'origen':a,'destino':b,'k':k,'semillas':len(filas),
                    'accuracy_media':float(np.mean([f['accuracy'] for f in filas])),
                    'accuracy_desviacion':float(np.std([f['accuracy'] for f in filas])),
                    'f1_macro_media':float(np.mean([f['f1_macro'] for f in filas]))})
    guardar_csv(salida/'resumen.csv',resumen)
    print(f'Evidencias guardadas: {salida}',flush=True)


if __name__=='__main__':main()
