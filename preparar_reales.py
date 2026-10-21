from pathlib import Path
from src.pfc07.datos_reales import preparar_zip
from src.pfc07.procesamiento import leer_features
from src.pfc07.evaluacion import ejecutar_experimento
import argparse
p=argparse.ArgumentParser();p.add_argument('--descargas',type=Path,default=Path.home()/'Downloads');a=p.parse_args()
for escenario in ('S5','S6','S7'):
    preparar_zip(a.descargas/f'{escenario}.zip',Path('datos_locales')/f'{escenario}_real.npz',escenario)
for origen,destino in [('S5','S6'),('S5','S7'),('S6','S5'),('S6','S7'),('S7','S5'),('S7','S6')]:
    ejecutar_experimento(leer_features(f'datos_locales/{origen}_real.npz'),leer_features(f'datos_locales/{destino}_real.npz'),f'outputs/reales/{origen}_{destino}',etiqueta='CSI_REAL_BASELINE_EXPLORATORIO_BLOQUES_TEMPORALES')
    print(f'Completado {origen} -> {destino}',flush=True)
