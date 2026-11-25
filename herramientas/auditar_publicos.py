"""Auditoria de cabeceras MAT y derivados existentes, sin cargar tensores completos."""
import argparse,json,zipfile,struct,zlib,hashlib
from pathlib import Path
import numpy as np
from lectura_mat_bloques import AUDIT_DIR, PROJECT

def tag(buf,pos,endian):
    word=struct.unpack_from(endian+'I',buf,pos)[0]
    small=word>>16
    if small:
        return word&65535,buf[pos+4:pos+4+small],pos+8
    kind,size=struct.unpack_from(endian+'II',buf,pos)
    if pos+8+size>len(buf): raise ValueError('Cabecera incompleta')
    return kind,buf[pos+8:pos+8+size],pos+8+((size+7)//8)*8

def header(stream):
    head=stream.read(128)
    if len(head)!=128 or not head.startswith(b'MATLAB 5.0'): raise ValueError('No es MAT clasico v5')
    endian={'IM':'<','MI':'>'}.get(head[126:128].decode())
    if not endian:raise ValueError('Endian desconocido')
    kind,size=struct.unpack(endian+'II',stream.read(8))
    if kind==15:
        payload=zlib.decompressobj().decompress(stream.read(min(size,262144)),4096)
        if struct.unpack_from(endian+'I',payload)[0]!=14:raise ValueError('No hay matriz')
        payload=payload[8:]
    elif kind==14:payload=stream.read(min(size,4096))
    else:raise ValueError('Elemento MAT inesperado')
    _,flags,pos=tag(payload,0,endian)
    flags=struct.unpack_from(endian+'I',flags)[0]
    _,dims,pos=tag(payload,pos,endian)
    dims=list(struct.unpack(endian+'i'*(len(dims)//4),dims))
    _,name,_=tag(payload,pos,endian)
    return dict(variable=name.decode('utf-8'),shape=dims,complex=bool(flags&0x800),matlab_class=flags&255)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archivos',type=Path,required=True,help='Directorio de S5.zip, S6.zip y S7.zip')
    parser.add_argument('--derivados',type=Path,default=PROJECT/'datos_locales')
    parser.add_argument('--salida',type=Path,default=AUDIT_DIR)
    args=parser.parse_args()
    source=args.archivos
    out=args.salida
    out.mkdir(parents=True,exist_ok=True)
    report=dict(scope='Cabeceras seleccionadas y derivados existentes; no es lectura completa ni CRC completo de ZIP.',archives=[],selected=[],prepared=[])
    for scenario in ['S5','S6','S7']:
        archive=source/(scenario+'.zip')
        with zipfile.ZipFile(archive) as z:
            mats=[i for i in z.infolist() if i.filename.lower().endswith('.mat')]
            names=[i.filename for i in mats]
            expected={f'{scenario}/{scenario}{rx}_{cl}.mat' for rx in 'abc' for cl in 'ABCDEFGHIJKL'}
            report['archives'].append(dict(scenario=scenario,path=archive.name,bytes=archive.stat().st_size,
                mat_count=len(mats),missing=sorted(expected-set(names)),unexpected=sorted(set(names)-expected),
                duplicate_names=len(names)-len(set(names))))
            old=json.loads((args.derivados/(scenario+'_real.json')).read_text(encoding='utf-8'))
            for activity in 'ABCGK':
                name=f'{scenario}/{scenario}a_{activity}.mat'
                with z.open(name) as f: info=header(f)
                previous=next(x for x in old['archivos'] if x['miembro']==name)
                info.update(member=name,scenario=scenario,receiver='a',activity=activity,
                    crc32_catalog=z.getinfo(name).CRC,previous_crc_matches=z.getinfo(name).CRC==previous['crc32'],
                    previous_shape_matches=info['shape']==previous['shape'],
                    documented_rate_hz=150,nominal_seconds=info['shape'][0]/150)
                report['selected'].append(info)
                print(name,info['shape'],'complejo',info['complex'],'CRC catalogo coincide',info['previous_crc_matches'],flush=True)
        npz=args.derivados/(scenario+'_real.npz')
        with np.load(npz,allow_pickle=False) as d:
            x=d['X'];labels=d['y'];groups=d['grupo'];order=d['orden']
            report['prepared'].append(dict(scenario=scenario,path=npz.name,shape=list(x.shape),
                dtype=str(x.dtype),finite=bool(np.isfinite(x).all()),
                labels={str(c):int(np.sum(labels==c)) for c in np.unique(labels)},
                recording_groups=len(np.unique(groups)),
                unique_recording_window_ids=len(set(zip(groups.tolist(),order.tolist())))==len(order),
                sha256=hashlib.sha256(npz.read_bytes()).hexdigest(),
                receiver=old['receptor'],antenna=old['antena'],window_packets=old['longitud_paquetes'],
                nominal_window_seconds=old['longitud_paquetes']/150,feature_bins=old['bins']))
    (out/'auditoria.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    lines=['# Auditoria de datasets publicos — 30/10/2026','',
    'Se verificaron inventarios ZIP, cabeceras de las 15 grabaciones seleccionadas y los tres archivos de caracteristicas ya existentes. No se ejecuto un CRC integral ni una nueva lectura completa de las matrices crudas. La coincidencia de CRC de catalogo es trazabilidad, no una comprobacion criptografica del contenido completo.','',
    '| Escenario | MAT en ZIP | Seleccion | Caracteristicas preparadas |', '|---|---:|---|---|']
    for a,d in zip(report['archives'],report['prepared']):lines.append(f"| {a['scenario']} | {a['mat_count']} | Receptor a; A/B/C/G/K | {d['shape']} |")
    lines+=['','## Que ya existia','',
    'El PFC conserva la preparacion de datos reales y seis evaluaciones exploratorias. Los ZIP indicados se contrastaron con los metadatos de los derivados, sin reescribir los originales.','',
    '## Diferencias frente al protocolo de tesis','',
    '- Derivados existentes: una antena, ventanas de 128 paquetes (0,8533 s a la tasa documental de 150 Hz) y 24 caracteristicas estadisticas sobre ocho bloques espectrales.',
    '- La tesis base propone ventanas de un segundo, cuatro antenas y otra representacion. Los NPZ existentes no son equivalentes a ese protocolo y no deben renombrarse como si lo fueran.',
    '- Los 150 Hz y las duraciones nominales proceden de documentacion; no se midio regularidad temporal por paquete.',
    '- No se ha reaud itado en este informe la separacion de soporte, consulta y desarrollo de las evaluaciones anteriores.'.replace('reaud itado','reauditado'),
    '- El comando generico cli.py preparar conserva referencias a csi_buff; el lector datos_reales.py usa csi. No ejecutar preparacion generica sin resolver esa diferencia.','',
    '## Siguiente paso','',
    'Verificar por lectura completa y bloques finitos al menos una grabacion seleccionada; confirmar indices espectrales y orientar el lector al protocolo de tesis. Conservar los NPZ exploratorios y generar los nuevos productos en otra carpeta. Integrar el informe y la demostracion de lectura en el video de avance.']
    (out/'INFORME.md').write_text('\n'.join(lines),encoding='utf-8')
    print('INFORME',out)

if __name__=='__main__':main()
