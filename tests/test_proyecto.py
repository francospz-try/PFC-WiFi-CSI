import json
from pathlib import Path
import numpy as np
import pytest
from scipy.io import savemat
from src.pfc07.auditoria import interpretar_nombre, inspeccionar_mat, listar_mat
from src.pfc07.procesamiento import caracteristicas_ventanas, leer_features
from src.pfc07.sintetico import generar_ejemplo
from src.pfc07.evaluacion import ejecutar_experimento, dividir_soporte_consulta


def test_nombres():
    assert interpretar_nombre('S5a_A.mat') == {'escenario': 'S5', 'receptor': 'a', 'clase': 'A'}
    assert interpretar_nombre('foo.mat')['escenario'] is None


def test_inspeccion_mat(tmp_path):
    ruta = tmp_path / 'S5a_A.mat'
    savemat(ruta, {'csi_buff': np.ones((300, 32), dtype=np.complex64)})
    info = inspeccionar_mat(ruta)
    assert info['variables'][0]['dimensiones'] == [300, 32]
    assert listar_mat(tmp_path)[0]['clase'] == 'A'


def test_extraer_ventanas():
    rng = np.random.default_rng(1)
    X = caracteristicas_ventanas(rng.normal(size=(320, 32)), eje_paquetes=0,
                                longitud=64, salto=64)
    assert X.shape == (5, 24)
    assert np.isfinite(X).all()


def test_salto_no_solapa():
    with pytest.raises(ValueError):
        caracteristicas_ventanas(np.ones((100, 16)), 0, longitud=20, salto=10)


def test_division_soporte_consulta():
    y = np.repeat(['A', 'B', 'C', 'G', 'K'], 40)
    orden = np.tile(np.arange(40), 5)
    soporte, consulta = dividir_soporte_consulta(y, orden)
    assert len(consulta) == 5 * (40 - 10 - 4)
    assert not set(consulta).intersection({i for x in soporte.values() for i in x})
    assert len(soporte['A']) == 10


def test_pipeline_sintetico(tmp_path):
    generar_ejemplo(tmp_path / 'data', n_por_clase=35)
    o = leer_features(tmp_path / 'data' / 'S5_SINTETICO.npz')
    d = leer_features(tmp_path / 'data' / 'S7_SINTETICO.npz')
    vals = ejecutar_experimento(o, d, tmp_path / 'results')
    assert [x['shots_por_clase'] for x in vals] == [0, 1, 5, 10]
    assert len({x['muestras_consulta'] for x in vals}) == 1
    assert (tmp_path / 'results' / 'confusion_10shot.csv').exists()
    protocolo = json.loads((tmp_path / 'results' / 'protocolo.json').read_text())
    assert protocolo['consultas_compartidas']


def test_rechaza_mismo_ambiente(tmp_path):
    generar_ejemplo(tmp_path / 'data', n_por_clase=35)
    o = leer_features(tmp_path / 'data' / 'S5_SINTETICO.npz')
    with pytest.raises(ValueError, match='ambientes diferentes'):
        ejecutar_experimento(o, o, tmp_path / 'results')


def test_preparacion_desde_mat_simulado(tmp_path):
    """Prueba integración MAT->NPZ. No son señales experimentales reales."""
    from src.pfc07.procesamiento import preparar_escenario
    rng = np.random.default_rng(4)
    for escenario in ('S5', 'S7'):
        carpeta = tmp_path / escenario
        carpeta.mkdir()
        for i, clase in enumerate('ABCGK'):
            # Filas intercaladas de 4 antenas; 24 ventanas de 32 paquetes por antena.
            senal = (rng.normal(size=(24 * 32 * 4, 32)) +
                     1j * rng.normal(size=(24 * 32 * 4, 32))) * (1 + i / 5)
            savemat(carpeta / f'{escenario}a_{clase}.mat', {'csi_buff': senal})
        preparar_escenario(carpeta, escenario, 'a', tmp_path / f'{escenario}.npz',
                           eje_paquetes=0, longitud=32, salto=32, antena=0)
    origen = leer_features(tmp_path / 'S5.npz')
    destino = leer_features(tmp_path / 'S7.npz')
    assert origen['X'].shape == (120, 24)
    filas = ejecutar_experimento(origen, destino, tmp_path / 'salida',
                                etiqueta='TEST_MAT_SINTETICO_NO_CSI_REAL')
    assert len(filas) == 4
