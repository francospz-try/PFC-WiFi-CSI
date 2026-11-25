"""Comprueba componentes de un MAT v5 numerico sin materializar el tensor."""
import argparse,json,struct,zlib,zipfile,time
from pathlib import Path
import numpy as np

PROJECT = Path(__file__).resolve().parents[1]
AUDIT_DIR = PROJECT / 'outputs' / 'auditoria_publicos_20261030'
class Inflate:
    def __init__(self,source,size):
        self.source=source;self.remaining=size;self.z=zlib.decompressobj();self.pending=b''
    def read(self,n):
        out=bytearray()
        while len(out)<n:
            if not self.pending:
                if not self.remaining:break
                block=self.source.read(min(65536,self.remaining))
                if not block:raise ValueError('Flujo comprimido truncado')
                self.remaining-=len(block);self.pending=block
            part=self.z.decompress(self.pending,n-len(out));out.extend(part)
            self.pending=self.z.unconsumed_tail
            if self.z.eof:break
        return bytes(out)

def exact(f,n):
    data=f.read(n)
    if len(data)!=n:raise ValueError('MAT truncado')
    return data

def element(f,endian):
    h=exact(f,8);word,size=struct.unpack(endian+'II',h)
    if word>>16:return word&65535,word>>16,h[4:4+(word>>16)]
    return word,size,None

def payload(f,endian):
    kind,size,small=element(f,endian)
    if small is not None:return kind,small
    value=exact(f,size)
    if size%8:exact(f,8-size%8)
    return kind,value

def audit(archive,member,out=AUDIT_DIR):
    start=time.monotonic()
    out.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as z, z.open(member) as source:
        h=exact(source,128);endian={'IM':'<','MI':'>'}[h[126:128].decode()]
        kind,size=struct.unpack(endian+'II',exact(source,8))
        if kind==15:
            f=Inflate(source,size)
            matrix_kind,matrix_size=struct.unpack(endian+'II',exact(f,8))
            if matrix_kind!=14:raise ValueError('Se esperaba matriz comprimida')
        elif kind==14:f=source
        else:raise ValueError('Formato MAT inesperado')
        _,flags=payload(f,endian);flags=struct.unpack_from(endian+'I',flags)[0]
        _,dims=payload(f,endian);shape=list(struct.unpack(endian+'i'*(len(dims)//4),dims))
        _,name=payload(f,endian)
        if name!=b'csi' or not flags&0x800:raise ValueError('Se esperaba csi complejo')
        result=dict(member=member,shape=shape,components={},method='MAT v5 por bloques de 1 MiB, sin construir tensor completo')
        total=int(np.prod(shape));samples=[]
        for label in ['real','imaginary']:
            kind,size,small=element(f,endian)
            types={1:'i1',2:'u1',3:'i2',4:'u2',5:'i4',6:'u4',7:'f4',9:'f8',12:'i8',13:'u8'}
            if small is not None or kind not in types:raise ValueError('Tipo numerico inesperado: '+str((kind,size)))
            dtype=np.dtype(endian+types[kind])
            if size!=total*dtype.itemsize:raise ValueError('Numero de componentes incompatible')
            remaining=size;finite=nonfinite=zero=count=0;lo=float('inf');hi=-float('inf');first=None
            while remaining:
                data=exact(f,min(1048576,remaining));remaining-=len(data)
                x=np.frombuffer(data,dtype=dtype);mask=np.isfinite(x)
                count+=x.size;finite+=int(mask.sum());nonfinite+=int(x.size-mask.sum());zero+=int(np.count_nonzero(x==0))
                if mask.any():lo=min(lo,float(x[mask].min()));hi=max(hi,float(x[mask].max()))
                if first is None:first=x[:4096].copy()
            if size%8:exact(f,8-size%8)
            result['components'][label]=dict(count=count,finite=finite,nonfinite=nonfinite,zeros=zero,min=lo,max=hi,dtype=str(dtype))
            samples.append(first)
            print(label,'componentes comprobados:',count,'no finitos:',nonfinite,flush=True)
        # Consumir el remanente fuerza tambien la comprobacion CRC del miembro ZIP.
        while source.read(1048576):pass
        result.update(zip_member_crc_verified=True,crc32=z.getinfo(member).CRC,elapsed_seconds=time.monotonic()-start,
                      scope='Comprobación completa del miembro indicado. No confirma índices espectrales válidos ni timestamps.')
    stem=Path(member).stem
    np.savez(out/('muestra_lectura_'+stem+'.npz'),real=samples[0],imaginary=samples[1])
    (out/('lectura_completa_'+stem+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    with (out/'INFORME.md').open('a',encoding='utf-8') as report:
        report.write('\n\n## Lectura secuencial completa: '+stem+'\n\nSe verificaron por bloques todas las componentes reales e imaginarias y el CRC del miembro ZIP. No se cargo el tensor completo en RAM. Valores no finitos: '+str(sum(c['nonfinite'] for c in result['components'].values()))+'. Detalles en lectura_completa_'+stem+'.json.\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archivo',type=Path)
    parser.add_argument('miembro')
    parser.add_argument('--salida',type=Path,default=AUDIT_DIR)
    args=parser.parse_args()
    audit(args.archivo,args.miembro,args.salida)
