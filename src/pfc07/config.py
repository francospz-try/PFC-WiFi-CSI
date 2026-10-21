from pathlib import Path

ACTIVIDADES = {
    'A': 'Caminar', 'B': 'Correr', 'C': 'Saltar',
    'G': 'Agitar las manos', 'K': 'Sentadillas'
}
CLASES = tuple(ACTIVIDADES)
AMBIENTES = {'S5': 'Laboratorio', 'S6': 'Oficina', 'S7': 'Vestíbulo'}
SHOT_VALUES = (0, 1, 5, 10)
ROOT = Path(__file__).resolve().parents[2]
