"""Lectura y comparacion exploratoria de sesiones CSI C6 propias."""
import ast
import csv
import json
from pathlib import Path
import numpy as np
from matplotlib.figure import Figure


def leer_captura(folder):
    meta = json.loads((folder/'metadata.json').read_text(encoding='utf-8'))
    ts, values = [], []
    for row in csv.reader((folder/'raw.log').read_text(encoding='utf-8', errors='replace').splitlines()):
        if not row or row[0] != 'CSI_DATA':
            continue
        try:
            if len(row) != 15 or int(row[13]):
                continue
            v = ast.literal_eval(row[14])
            if not isinstance(v, list) or len(v) != int(row[12]) or len(v) != 256:
                continue
            if not all(type(x) is int for x in v):
                continue
            ts.append(int(row[9])); values.append(v)
        except (ValueError, SyntaxError, TypeError):
            continue
    if len(ts) < 30:
        raise ValueError('La sesion necesita al menos 30 paquetes utilizables.')
    ts = np.asarray(ts, dtype=np.int64)
    if np.any(np.diff(ts) <= 0):
        raise ValueError('Hay reinicios o marcas temporales no crecientes; segmentar antes de analizar.')
    iq = np.asarray(values, dtype=float)
    return meta, (ts-ts[0])/1e6, np.hypot(iq[:,::2], iq[:,1::2])


def comparar(a, b):
    data = [leer_captura(Path(p)) for p in (a,b)]
    mask = np.logical_and.reduce([np.any(x[2] > 0, axis=0) for x in data])
    if not mask.any():
        raise ValueError('No existen posiciones no nulas comunes.')
    fig = Figure(figsize=(11,7), layout='constrained')
    axes = fig.subplots(2,2)
    summary=[]
    for col,(meta,t,amp) in enumerate(data):
        x=np.log1p(amp[:,mask]); rows=[]
        # Solo intervalos completos: no se inventan muestras en huecos.
        for second in range(int(t[-1])):
            sel=(t>=second)&(t<second+1)
            if sel.sum() >= 30:
                rows.append((second+.5,float(np.median(np.std(x[sel],axis=0)))))
        if not rows:
            raise ValueError('No hay intervalos completos con suficientes paquetes.')
        v=np.asarray(rows)
        color=['#2874a6','#b3541e'][col]
        axes[0,col].plot(t,np.median(x,axis=1),lw=.7,color=color)
        axes[0,col].set_title(f"{meta['label']} · {meta['session']}", fontsize=9, wrap=True)
        axes[0,col].set_ylabel('Mediana log(1 + amplitud)')
        axes[1,col].plot(v[:,0],v[:,1],marker='o',ms=3,color=color)
        axes[1,col].set_ylabel('Variabilidad temporal por segundo')
        axes[1,col].set_xlabel('Tiempo desde primer paquete (s)')
        for ax in axes[:,col]: ax.grid(alpha=.2)
        summary.append(dict(session=meta['session'],label=meta['label'],
                            variability=float(np.median(v[:,1])),positions=int(mask.sum())))
    for row in range(2):
        lo=min(ax.get_ylim()[0] for ax in axes[row]);hi=max(ax.get_ylim()[1] for ax in axes[row])
        for ax in axes[row]: ax.set_ylim(lo,hi)
    fig.suptitle('CSI propio: comparacion descriptiva de dos grabaciones\nSin clasificador ni medida de precision HAR',fontsize=12)
    return fig,summary
