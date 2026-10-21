"""Datos ARTIFICIALES de funcionalidades para PRUEBAS, NO señal Wi-Fi CSI.

Nunca utilizar resultados de esta simulación como evidencia de eficacia del PFC.
"""
from pathlib import Path
import numpy as np
from .config import CLASES


def generar_ejemplo(salida, semilla=42, n_por_clase=80, dimension=24):
    rng = np.random.default_rng(semilla)
    sal = Path(salida)
    sal.mkdir(parents=True, exist_ok=True)
    bases = rng.normal(0, 0.95, (len(CLASES), dimension))
    desplazamientos = {'S5': np.zeros(dimension),
                       'S6': rng.normal(0.35, .65, dimension),
                       'S7': rng.normal(0.8, .8, dimension)}
    for escenario, bias in desplazamientos.items():
        X, y, orden, grupos = [], [], [], []
        for i, clase in enumerate(CLASES):
            base = bases[i] + bias + rng.normal(0, .3, dimension) * (i+1)/5
            ruido = rng.normal(0, 1.5, (n_por_clase, dimension))
            tendencias = np.linspace(-.2, .2, n_por_clase)[:, None]
            Xi = base + ruido + tendencias
            X.extend(Xi)
            y.extend([clase] * n_por_clase)
            orden.extend(range(n_por_clase))
            grupos.extend([f'{escenario}a_{clase}_ARTIFICIAL'] * n_por_clase)
        np.savez_compressed(sal / f'{escenario}_SINTETICO.npz',
                            X=np.asarray(X, dtype=np.float32), y=np.asarray(y),
                            orden=np.asarray(orden), grupo=np.asarray(grupos),
                            escenario=np.array(escenario), receptor=np.array('a'))
    return sal
