"""Inventario de archivos MAT, sin cargar matrices CSI grandes."""
import json
import re
import zipfile
from pathlib import Path
import scipy.io

PATRON = re.compile(r'^(S[567])([abc])_([A-L])\.mat$', flags=re.I)


def listar_mat(ruta):
    ruta = Path(ruta)
    if ruta.is_file() and ruta.suffix.lower() == '.zip':
        with zipfile.ZipFile(ruta) as z:
            return [{'archivo': i.filename, 'tamano_bytes': i.file_size,
                     'comprimido_bytes': i.compress_size,
                     'origen': 'zip', **interpretar_nombre(i.filename)}
                    for i in z.infolist() if i.filename.lower().endswith('.mat')]
    if ruta.is_file() and ruta.suffix.lower() == '.mat':
        ficheros = [ruta]
    elif ruta.is_dir():
        ficheros = sorted(ruta.rglob('*.mat'))
    else:
        raise FileNotFoundError(str(ruta))
    return [{'archivo': str(p), 'tamano_bytes': p.stat().st_size,
             'origen': 'sistema_archivos', **interpretar_nombre(p.name)} for p in ficheros]


def interpretar_nombre(nombre):
    coincidencia = PATRON.fullmatch(Path(nombre).name)
    if not coincidencia:
        return {'escenario': None, 'receptor': None, 'clase': None}
    s, r, c = coincidencia.groups()
    return {'escenario': s.upper(), 'receptor': r.lower(), 'clase': c.upper()}


def inspeccionar_mat(ruta):
    """Lista variables/dimensiones. whosmat no carga todas las matrices.

    Para MAT v7.3, usa HDF5; las dimensiones en h5py pueden tener orden distinto
    al reportado por MATLAB. No se interpreta el eje temporal automáticamente.
    """
    ruta = Path(ruta)
    try:
        v = scipy.io.whosmat(str(ruta))
        return {'ruta': str(ruta), 'formato': 'MAT v5/v7',
                'variables': [{'nombre': n, 'dimensiones': list(sh), 'tipo': typ}
                              for n, sh, typ in v]}
    except (NotImplementedError, ValueError, TypeError) as exc:
        try:
            import h5py
            with h5py.File(ruta, 'r') as archivo:
                campos = []
                def registrar(nombre, objeto):
                    if isinstance(objeto, h5py.Dataset):
                        campos.append({'nombre': nombre, 'dimensiones': list(objeto.shape),
                                       'tipo': str(objeto.dtype)})
                archivo.visititems(registrar)
                return {'ruta': str(ruta), 'formato': 'MAT v7.3/HDF5',
                        'variables': campos, 'advertencia':
                        'Comprobar ejes y representación compleja antes de procesar'}
        except (OSError, ImportError):
            raise ValueError(f'No se pudo inspeccionar {ruta}: {exc}') from exc


def guardar_auditoria(informe, salida):
    Path(salida).parent.mkdir(parents=True, exist_ok=True)
    Path(salida).write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding='utf-8')
