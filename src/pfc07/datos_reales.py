"""Lector de Exposing the CSI: MAT clásico, variable csi [tiempo, canal, antena]."""
import json, zipfile
from pathlib import Path
import numpy as np
from scipy.io import loadmat, whosmat
from .config import CLASES
from .procesamiento import caracteristicas_ventanas

def preparar_zip(archivo, salida, escenario, receptor='a', antena=0, longitud=128):
    partes=[]; etiquetas=[]; grupos=[]; orden=[]; auditoria=[]
    with zipfile.ZipFile(archivo) as z:
        for clase in CLASES:
            nombre=f'{escenario}/{escenario}{receptor}_{clase}.mat'
            with z.open(nombre) as f: info=whosmat(f)
            if len(info)!=1 or info[0][0]!='csi' or len(info[0][1])!=3 or info[0][1][1:]!=(2048,4):
                raise ValueError(f'Estructura inesperada: {nombre}: {info}')
            print(f'Leyendo {nombre}: {info[0][1]}',flush=True)
            with z.open(nombre) as f: datos=loadmat(f,variable_names=['csi'])
            csi=datos['csi']
            if not 0<=antena<csi.shape[2]:raise ValueError('Antena inválida')
            x=caracteristicas_ventanas(csi[:,:,antena],0,longitud,longitud)
            esperadas=csi.shape[0]//longitud
            if len(x)!=esperadas:raise ValueError('NaN/Inf: se requiere revisar ventanas inválidas')
            partes.append(x);etiquetas.extend([clase]*len(x));grupos.extend([Path(nombre).stem]*len(x));orden.extend(range(len(x)))
            auditoria.append({'miembro':nombre,'shape':list(csi.shape),'crc32':z.getinfo(nombre).CRC,'ventanas':len(x)})
            del csi,datos
    salida=Path(salida);salida.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(salida,X=np.vstack(partes),y=np.array(etiquetas),grupo=np.array(grupos),orden=np.array(orden),escenario=np.array(escenario),receptor=np.array(receptor))
    meta={'fuente':str(Path(archivo).resolve()),'variable':'csi','eje_tiempo':0,'eje_antena':2,'antena':antena,'receptor':receptor,'longitud_paquetes':longitud,'salto_paquetes':longitud,'bins':8,'frecuencia_hz_documentada':150,'archivos':auditoria,'naturaleza':'CSI_REAL_BASELINE_EXPLORATORIO'}
    salida.with_suffix('.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    return salida
