"""Figuras reproducibles para la web y la memoria, sin servicios externos."""
from io import BytesIO
from threading import Lock
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

_LOCK = Lock()
NOMBRES = ['Caminar', 'Correr', 'Saltar', 'Agitar manos', 'Sentadillas']

def figura_metricas(filas, titulo='Comparación entre configuraciones'):
    fig = Figure(figsize=(9, 4.8), layout='constrained')
    ax = fig.subplots()
    colores = ['#173847', '#2f6f89', '#39a095', '#dc9739']
    campos = [('accuracy', 'Exactitud'), ('precision_macro', 'Precisión macro'), ('recall_macro', 'Recall macro'), ('f1_macro', 'F1 macro')]
    x = np.arange(len(filas)); ancho = .19
    for j, ((campo, etiqueta), color) in enumerate(zip(campos, colores)):
        ax.bar(x + (j - 1.5) * ancho, [float(f[campo]) for f in filas], width=ancho, label=etiqueta, color=color)
    ax.set_xticks(x, [str(f.get('shots_por_clase', f.get('k'))) for f in filas])
    ax.set(xlabel='k: ejemplos etiquetados por clase', ylabel='Valor (0 a 1)', ylim=(0, 1), title=titulo)
    ax.grid(axis='y', alpha=.18); ax.set_axisbelow(True)
    ax.legend(loc='upper center', ncol=2, frameon=False)
    return fig

def figura_confusion(matriz, k=0, titulo='Matriz de confusión'):
    a = np.asarray(matriz)
    if a.shape != (5, 5) or not np.isfinite(a).all():
        raise ValueError('Se requiere una matriz finita de cinco clases')
    fig = Figure(figsize=(7.4, 6.1), layout='constrained'); ax = fig.subplots()
    im = ax.imshow(a, cmap='Blues', vmin=0, vmax=max(1, float(a.max())))
    ax.set_xticks(range(5), NOMBRES, rotation=25, ha='right')
    ax.set_yticks(range(5), NOMBRES)
    ax.set(xlabel='Actividad predicha', ylabel='Actividad real', title=f'{titulo} · {k}-shot')
    for i in range(5):
        for j in range(5):
            ax.text(j, i, str(int(a[i, j])), ha='center', va='center', color='white' if a[i, j] > a.max() * .55 else '#173847')
    fig.colorbar(im, ax=ax, label='Número de ventanas')
    return fig

def exportar_figura(figura, formato='svg'):
    with _LOCK:
        buffer = BytesIO(); FigureCanvasAgg(figura)
        figura.savefig(buffer, format=formato, dpi=160)
        figura.clear()
        return buffer.getvalue()
