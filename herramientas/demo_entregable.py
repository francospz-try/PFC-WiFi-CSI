"""Demostracion reproducible con CSI real. No entrena ni evalua el modelo de tesis."""
import argparse,hashlib,json,platform,struct,sys,time,zipfile
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import scipy
from scipy.ndimage import median_filter
from scipy.signal import resample_poly
import matplotlib
matplotlib.use('Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from lectura_mat_bloques import Inflate,exact,element,payload

PROJECT=Path(__file__).resolve().parents[1]
OUT=PROJECT/'outputs'/'entregable_30'/'demo'

def extract(archive,member,bins):
    with zipfile.ZipFile(archive) as z,z.open(member) as source:
        h=exact(source,128);endian={'IM':'<','MI':'>'}[h[126:128].decode()]
        kind,size=struct.unpack(endian+'II',exact(source,8))
        if kind==15:
            f=Inflate(source,size)
            if struct.unpack(endian+'II',exact(f,8))[0]!=14:raise ValueError('No es miMATRIX')
        elif kind==14:f=source
        else:raise ValueError('Formato inesperado')
        _,flags=payload(f,endian);flags=struct.unpack_from(endian+'I',flags)[0]
        _,dims=payload(f,endian);shape=list(struct.unpack(endian+'i'*(len(dims)//4),dims))
        _,name=payload(f,endian)
        if name!=b'csi' or not flags&0x800 or shape!=[12000,2048,4]:raise ValueError('Cabecera incompatible')
        nt,ns,na=shape
        starts=np.array([(a*ns+b)*nt for a in range(na) for b in bins]);ends=starts+nt
        components=[]
        for label in ['real','imaginary']:
            kind,size,small=element(f,endian);types={1:'i1',2:'u1',3:'i2',4:'u2',5:'i4',6:'u4',7:'f4',9:'f8',12:'i8',13:'u8'}
            if small is not None or kind not in types:raise ValueError('Tipo inesperado')
            dtype=np.dtype(endian+types[kind])
            if size!=nt*ns*na*dtype.itemsize:raise ValueError('Tamano incompatible')
            selected=np.zeros((na*len(bins),nt),dtype=np.float32);remaining=size;offset=0
            while remaining:
                block=exact(f,min(1048576,remaining));remaining-=len(block);x=np.frombuffer(block,dtype=dtype)
                if not np.isfinite(x).all():raise ValueError('Componentes no finitas')
                finish=offset+len(x)
                lo=np.searchsorted(ends,offset,side='right');hi=np.searchsorted(starts,finish,side='left')
                for j in range(lo,hi):
                    left=max(offset,starts[j]);right=min(finish,ends[j])
                    selected[j,left-starts[j]:right-starts[j]]=x[left-offset:right-offset]
                offset=finish
            if size%8:exact(f,8-size%8)
            components.append(selected.reshape(na,len(bins),nt).transpose(2,1,0))
            print('Componente leida:',label,flush=True)
        if isinstance(f,Inflate):
            while f.read(1048576):pass
            if not f.z.eof:raise ValueError('Flujo zlib incompleto')
        while source.read(1048576):pass
        return components,shape,z.getinfo(member).CRC

def run(member='S5/S5a_A.mat'):
    report=json.loads((PROJECT/'outputs/auditoria_publicos_20261030/auditoria.json').read_text())
    allowed={r['member'] for r in report['selected']}
    if member not in allowed:raise ValueError('Miembro fuera de seleccion auditada')
    scenario=member.split('/')[0];archive=Path('D:/TesisFrancoCSI')/(scenario+'.zip')
    OUT.mkdir(parents=True,exist_ok=True);start=time.monotonic()
    bins=np.linspace(0,2047,64,dtype=int)
    (re,im),shape,crc=extract(archive,member,bins)
    amp=np.hypot(re,im);del re,im
    logged=np.log1p(amp);del amp
    filtered=median_filter(logged,size=(3,1,1),mode='nearest')
    resampled=resample_poly(filtered,up=2,down=3,axis=0,padtype='line').astype(np.float32)
    windows=resampled.reshape(80,100,256)
    if not np.isfinite(windows).all():raise ValueError('Resultado no finito')
    npz=OUT/'ventanas_demo.npz'
    np.savez_compressed(npz,windows=windows,spectral_indices=bins,source_rate=150,target_rate=100)
    fig=Figure(figsize=(11,8),layout='constrained');axes=fig.subplots(3,1)
    axes[0].plot(np.arange(len(logged))/150,np.median(logged,axis=(1,2)),lw=.7)
    axes[0].set(title='Lectura real: mediana de log(1 + amplitud), proyeccion de 64 indices y 4 antenas',ylabel='Amplitud transformada',xlabel='Tiempo nominal (s)')
    axes[1].plot(np.arange(len(resampled))/100,np.median(resampled,axis=(1,2)),lw=.7,color='#b3541e')
    axes[1].set(title='Filtro mediano y remuestreo 150 a 100 Hz',ylabel='Amplitud transformada',xlabel='Tiempo nominal (s)')
    image=axes[2].imshow(windows[0].T,aspect='auto',origin='lower',cmap='viridis',extent=[0,1,0,256])
    axes[2].set(title='Primera ventana: 100 instantes por 256 canales proyectados',xlabel='Tiempo nominal dentro de ventana (s)',ylabel='Indice de canal')
    fig.colorbar(image,ax=axes[2],label='log(1 + amplitud)')
    fig.suptitle(member+' · Demostracion de lectura y ventanas · Proyeccion espectral provisional',fontsize=12)
    FigureCanvasAgg(fig);fig.savefig(OUT/'lectura_y_ventanas.png',dpi=140)
    scripts=['herramientas/demo_entregable.py','herramientas/lectura_mat_bloques.py']
    meta=dict(member=member,source=str(archive),source_shape=shape,crc32=crc,crc_verified=True,
        spectral_indices=bins.tolist(),spectral_selection='Uniforme provisional; incluye posibles posiciones nulas. No certificada como 64 subportadoras validas.',
        source_rate_hz_documented=150,target_rate_hz=100,window_shape=list(windows.shape),window_seconds=1,
        filters='log1p magnitud; mediana temporal 3; resample_poly 2/3 con antialias y extension lineal en bordes',
        finite=True,created_utc=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-start,
        npz_sha256=hashlib.sha256(npz.read_bytes()).hexdigest(),
        script_hashes={s:hashlib.sha256((PROJECT/s).read_bytes()).hexdigest() for s in scripts},
        versions=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,matplotlib=matplotlib.__version__),
        scope='Demostracion de lectura, transformacion y serializacion. No usada para entrenar; no reproduce aun todo el protocolo de tesis.',
        pending='Verificar indices OFDM/LTF validos, escala S7 y aplicar filtros dentro de las particiones antes de entrenar. La tasa y el tiempo son nominales documentales.')
    (OUT/'manifest.json').write_text(json.dumps(meta,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(meta,indent=2,ensure_ascii=False))
    return meta

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--member',default='S5/S5a_A.mat');run(p.parse_args().member)
