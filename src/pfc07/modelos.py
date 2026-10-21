"""Modelo base de referencia + adaptación Few-Shot prototípica sencilla.

NO es un modelo SOTA y no supone mejora garantizada; es una referencia reproducible.
"""
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from scipy.special import softmax


def entrenar_base(X, y, semilla=42):
    X = np.asarray(X, dtype=float)
    y = np.asarray(y)
    if X.ndim != 2 or len(np.unique(y)) < 2:
        raise ValueError('X debe ser 2D con al menos dos clases')
    escala = StandardScaler().fit(X)
    modelo = LogisticRegression(max_iter=1000, random_state=semilla)
    modelo.fit(escala.transform(X), y)
    return escala, modelo


def prediccion_fewshot(escala, modelo, X_query, X_support=None, y_support=None,
                       peso_prototipo=0.5):
    """Combinación fija de probabilidades base + prototipos etiquetados destino.

    La distancia prototípica se estandariza con dispersion de las distancias
    entre prototipos; no utiliza etiquetas del conjunto de consulta.
    """
    Xq = escala.transform(np.asarray(X_query, dtype=float))
    base_prob = modelo.predict_proba(Xq)
    if X_support is None or len(X_support) == 0:
        return modelo.classes_[np.argmax(base_prob, axis=1)]
    Xs = escala.transform(np.asarray(X_support, dtype=float))
    ys = np.asarray(y_support)
    if set(ys) != set(modelo.classes_):
        raise ValueError('Soporte Few-Shot incompleto: se requiere cada clase')
    centros = np.stack([Xs[ys == clase].mean(axis=0) for clase in modelo.classes_])
    d2 = ((Xq[:, None, :] - centros[None, :, :])**2).sum(axis=2)
    distancia_entre_centros = ((centros[:, None, :] - centros[None, :, :])**2).sum(axis=2)
    tri = distancia_entre_centros[np.triu_indices(len(centros), 1)]
    temperatura = max(float(np.median(tri)), 1e-8)
    prob_prototipo = softmax(-d2 / temperatura, axis=1)
    combinado = (1 - peso_prototipo) * base_prob + peso_prototipo * prob_prototipo
    return modelo.classes_[np.argmax(combinado, axis=1)]
