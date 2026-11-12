import ctypes,json,time,zipfile
from pathlib import Path
import numpy as np
from scipy.io import loadmat

class Memory(ctypes.Structure):
    _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(x,ctypes.c_ulonglong) for x in ['total','avail','page','availpage','virt','availvirt','ext']]

m=Memory();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
print('RAM disponible GB:',round(m.avail/1e9,2),flush=True)
if m.avail<5_000_000_000:raise SystemExit('Lectura completa aplazada: requiere controlar memoria o lector por bloques.')
out=Path('C:/Franco/2026/PFC_implementacion/outputs/auditoria_publicos_20261030')
start=time.monotonic();member='S5/S5a_A.mat'
with zipfile.ZipFile('D:/TesisFrancoCSI/S5.zip') as z:
    with z.open(member) as f:
        data=loadmat(f,variable_names=['csi'])['csi']
        while f.read(1048576):pass
    print('Lectura completa:',data.shape,data.dtype,flush=True)
    finite=0;nonfinite=0;zero=0
    for i in range(0,data.shape[0],64):
        chunk=data[i:i+64];ok=np.isfinite(chunk)
        finite+=int(ok.sum());nonfinite+=int(ok.size-ok.sum());zero+=int(np.count_nonzero(chunk==0))
    result=dict(member=member,shape=list(data.shape),dtype=str(data.dtype),is_complex=bool(np.iscomplexobj(data)),
                finite_complex_values=finite,nonfinite_complex_values=nonfinite,zero_complex_values=zero,
                payload_bytes=int(data.nbytes),zip_member_crc_verified=True,crc32=z.getinfo(member).CRC,
                elapsed_seconds=time.monotonic()-start,
                scope='Un archivo crudo leido completamente y comprobado. No implica validacion completa de los 15 o 108 archivos.')
(out/'lectura_completa_S5a_A.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
with (out/'INFORME.md').open('a',encoding='utf-8') as f:
    f.write('\n\n## Lectura completa adicional\n\nSe leyo completamente S5a_A.mat desde el ZIP del disco externo y se verifico el CRC del miembro. Forma '+str(result['shape'])+', tipo '+result['dtype']+', valores complejos no finitos: '+str(nonfinite)+'. Esta comprobacion cubre un archivo; los otros 14 seleccionados conservan verificacion de cabecera y trazabilidad. Detalle en lectura_completa_S5a_A.json.\n')
print(json.dumps(result,indent=2))
