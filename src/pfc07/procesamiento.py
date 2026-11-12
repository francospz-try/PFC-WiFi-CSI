"""Extractor exploratorio de amplitud CSI (NO implementa SHARP/Doppler)."""
import re
from pathlib import Path
import numpy as np
from scipy.io import loadmat
from .config import CLASES


def caracteristicas_ventanas(csi, eje_paquetes, longitud=128, salto=None, bins=8):
    """Devuelve características fijas por ventana temporal de paquetes CSI.

    Sin frecuencia/timestamps confirmados, longitud son paquetes, NO segundos.
    Eje temporal se exige explícitamente para evitar invertir dimensiones.
    No se aplican filtros de fase ni sanitización SHARP.
    """
    csi = np.asarray(csi)
    if csi.ndim < 2 or not np.issubdtype(csi.dtype, np.number):
        raise ValueError('Se requiere una matriz CSI numérica de 2 o más dimensiones')
    if not (0 <= eje_paquetes < csi.ndim):
        raise ValueError('eje_paquetes fuera de rango')
    if longitud < 4 or bins < 2:
        raise ValueError('longitud >= 4 y bins >= 2')
    salto = longitud if salto is None else salto
    if salto < longitud:
        raise ValueError('El pipeline exige ventanas no superpuestas: salto >= longitud')
    a = np.moveaxis(csi, eje_paquetes, 0)
    if a.shape[0] < longitud:
        raise ValueError('No hay suficientes paquetes para una sola ventana')
    a = a.reshape(a.shape[0], -1)
    if a.shape[1] < bins:
        raise ValueError('No hay suficientes canales/subportadoras para los bins')
    limites = np.linspace(0, a.shape[1], bins + 1, dtype=int)
    if np.any(np.diff(limites) == 0):
        raise ValueError('Bins no válidos')
    salida = []
    for inicio in range(0, a.shape[0] - longitud + 1, salto):
        ventana = np.abs(a[inicio:inicio + longitud]).astype(np.float32)
        if not np.isfinite(ventana).all():
            continue
        v = []
        for j in range(bins):
            segmento = ventana[:, limites[j]:limites[j + 1]]
            energia_temporal = np.abs(np.diff(segmento, axis=0))
            v.extend([float(np.mean(segmento)), float(np.std(segmento)),
                      float(np.mean(energia_temporal))])
        salida.append(v)
    if not salida:
        raise ValueError('Ninguna ventana válida tras omitir NaN/Inf')
    return np.asarray(salida, dtype=np.float32)


def preparar_escenario(directorio, escenario, receptor, salida, eje_paquetes,
                        longitud=128, salto=128, bins=8, antena=0, n_antenas=4):
    """Procesa un MAT a la vez. scipy.io.loadmat puede requerir RAM elevada.

    Solo MAT v5/v7 con variable numeric csi_buff. v7.3 requiere adaptar
    el lector después de verificar la estructura HDF5.
    """
    escenario, receptor = escenario.upper(), receptor.lower()
    if escenario not in ('S5', 'S6', 'S7') or receptor not in ('a', 'b', 'c'):
        raise ValueError('Escenario o receptor inválido')
    if n_antenas < 1 or not 0 <= antena < n_antenas:
        raise ValueError('antena debe encontrarse entre 0 y n_antenas - 1')
    matrices, etiquetas, grupos, orden = [], [], [], []
    for clase in CLASES:
        candidatos = list(Path(directorio).rglob(f'{escenario}{receptor}_{clase}.mat'))
        if len(candidatos) != 1:
            raise FileNotFoundError(f'Esperado exactamente un MAT para {escenario}{receptor}_{clase}')
        p = candidatos[0]
        try:
            datos = loadmat(p, variable_names=['csi_buff'], squeeze_me=False)
        except NotImplementedError as exc:
            raise ValueError('MAT v7.3 detectado: requiere lector HDF5 tras auditoría') from exc
        if 'csi_buff' not in datos:
            raise ValueError(f'No existe csi_buff en {p}; inspecciona el archivo')
        csi = datos['csi_buff']
        if not np.issubdtype(csi.dtype, np.number):
            raise ValueError(f'csi_buff no es numérico simple en {p}: {csi.dtype}')
        # SHARP referencia registra antenas/streams intercalados entre filas CSI.
        # Seleccionamos una sola antena de un receptor para no mezclar tiempos.
        csi = np.take(csi, indices=np.arange(antena, csi.shape[eje_paquetes], n_antenas),
                      axis=eje_paquetes)
        x = caracteristicas_ventanas(csi, eje_paquetes, longitud, salto, bins)
        matrices.append(x)
        etiquetas.extend([clase] * len(x))
        grupos.extend([p.stem] * len(x))
        orden.extend(range(len(x)))
        del datos, csi, x
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(salida, X=np.vstack(matrices), y=np.array(etiquetas),
                        grupo=np.array(grupos), orden=np.array(orden),
                        escenario=np.array(escenario), receptor=np.array(receptor),
                        antena=np.array(antena), n_antenas=np.array(n_antenas))
    return salida


def leer_features(ruta):
    with np.load(ruta, allow_pickle=False) as z:
        campos = ('X', 'y', 'grupo', 'orden', 'escenario', 'receptor')
        if any(k not in z for k in campos):
            raise ValueError(f'Archivo NPZ incompleto: esperado {campos}')
        datos = {k: z[k].copy() for k in z.files}
    validar_features(datos)
    return datos


def validar_features(datos):
    """Valida el contrato antes de entrenar o escribir resultados."""
    for campo in ('X', 'y', 'grupo', 'orden', 'escenario', 'receptor'):
        if campo not in datos:
            raise ValueError(f'Falta campo {campo}')
    X = np.asarray(datos['X'])
    if X.ndim != 2 or not all(X.shape) or X.dtype.kind not in 'fiu':
        raise ValueError('X debe ser una matriz numérica real 2D no vacía')
    if not np.isfinite(X).all():
        raise ValueError('Características con NaN o Inf')
    for campo in ('y', 'grupo', 'orden'):
        v = np.asarray(datos[campo])
        if v.ndim != 1 or len(v) != len(X):
            raise ValueError(f'{campo} debe ser un vector con una entrada por muestra')
    if set(datos['y']) != set(CLASES):
        raise ValueError('Se requieren exactamente las clases A,B,C,G,K')
    orden = np.asarray(datos['orden'])
    if orden.dtype.kind not in 'iu' or np.any(orden < 0):
        raise ValueError('orden debe contener enteros no negativos')
    for campo, permitidos in [('escenario', ('S5','S6','S7')), ('receptor', ('a','b','c'))]:
        v = np.asarray(datos[campo])
        if v.ndim != 0 or str(v) not in permitidos:
            raise ValueError(f'{campo} inválido')
    # El protocolo actual admite una grabación por clase; no mezclar sesiones.
    for clase in CLASES:
        idx = np.asarray(datos['y']) == clase
        if len(np.unique(np.asarray(datos['grupo'])[idx])) != 1:
            raise ValueError('El protocolo requiere una grabación por clase')
        if len(np.unique(orden[idx])) != int(idx.sum()):
            raise ValueError('orden contiene duplicados dentro de una clase')
