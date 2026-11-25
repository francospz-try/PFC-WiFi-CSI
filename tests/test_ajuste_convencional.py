import csv
import json

from src.pfc07.evaluacion import ejecutar_experimento
from src.pfc07.procesamiento import leer_features
from src.pfc07.sintetico import generar_ejemplo


def test_ajuste_convencional_comparte_particion_y_cero_shot(tmp_path):
    generar_ejemplo(tmp_path / 'datos', n_por_clase=35)
    origen = leer_features(tmp_path / 'datos' / 'S5_SINTETICO.npz')
    destino = leer_features(tmp_path / 'datos' / 'S7_SINTETICO.npz')
    combinado = tmp_path / 'combinado'
    ajuste = tmp_path / 'ajuste'
    referencia = ejecutar_experimento(origen, destino, combinado)
    filas = ejecutar_experimento(origen, destino, ajuste, metodo='ajuste_convencional')
    assert filas[0] == referencia[0]
    assert [f['muestras_soporte'] for f in filas] == [0, 5, 25, 50]

    def protocolo(ruta):
        return json.loads((ruta / 'protocolo.json').read_text(encoding='utf-8'))

    base_meta, ajuste_meta = protocolo(combinado), protocolo(ajuste)
    assert ajuste_meta['metodo'] == 'ajuste_convencional'
    assert ajuste_meta['indices_consulta'] == base_meta['indices_consulta']
    assert ajuste_meta['seleccion_soporte'] == base_meta['seleccion_soporte']
    assert (ajuste / 'predicciones_0shot.csv').read_bytes() == (combinado / 'predicciones_0shot.csv').read_bytes()
    with (ajuste / 'predicciones_5shot.csv').open(encoding='utf-8', newline='') as archivo:
        assert [int(row['indice_consulta']) for row in csv.DictReader(archivo)] == ajuste_meta['indices_consulta']
    assert (ajuste / 'confusion_10shot.csv').is_file()
