"""Casos de software con fixtures artificiales, nunca evidencia de eficacia CSI."""
import io
import json
import zipfile
import numpy as np
import pytest
from scipy.io import savemat
from src.pfc07.sintetico import generar_ejemplo
from src.pfc07.procesamiento import leer_features
from src.pfc07.datos_reales import preparar_zip
from src.pfc07.evaluacion import ejecutar_experimento


@pytest.fixture
def datos(tmp_path):
    generar_ejemplo(tmp_path / 'data', n_por_clase=25)
    return [leer_features(tmp_path / 'data' / f'{s}_SINTETICO.npz') for s in ('S5','S7')]


@pytest.mark.parametrize('caso', ['dimension', 'longitud', 'nan', 'inf', 'clase', 'orden', 'sesiones'])
def test_entrada_invalida_no_escribe(tmp_path, datos, caso):
    o, d = datos
    if caso == 'dimension': d['X'] = d['X'].ravel()
    if caso == 'longitud': d['y'] = d['y'][:-1]
    if caso == 'nan': d['X'][0,0] = np.nan
    if caso == 'inf': d['X'][0,0] = np.inf
    if caso == 'clase': d['y'][0] = 'Z'
    if caso == 'orden': d['orden'][1] = d['orden'][0]
    if caso == 'sesiones': d['grupo'][0] = 'otro'
    salida = tmp_path / 'resultado'
    with pytest.raises(ValueError): ejecutar_experimento(o,d,salida)
    assert not salida.exists()


@pytest.mark.parametrize('shots', [[], [2], [0,0], [0,11]])
def test_shots_invalidos_preservan_resultados(tmp_path, datos, shots):
    salida = tmp_path / 'resultado'; salida.mkdir()
    previo = salida / 'metricas.csv'; previo.write_text('evidencia anterior')
    with pytest.raises(ValueError): ejecutar_experimento(*datos,salida,shots=shots)
    assert previo.read_text() == 'evidencia anterior'
    assert list(salida.iterdir()) == [previo]


def test_reproducibilidad_y_metricas_desde_predicciones(tmp_path, datos):
    import csv
    from sklearn.metrics import accuracy_score, f1_score
    a = ejecutar_experimento(*datos,tmp_path/'a',etiqueta='SINTETICO_TEST')
    b = ejecutar_experimento(*datos,tmp_path/'b',etiqueta='SINTETICO_TEST')
    assert a == b
    protocolo=json.loads((tmp_path/'a/protocolo.json').read_text())
    consulta=set(protocolo['indices_consulta'])
    assert not consulta.intersection(i for v in protocolo['seleccion_soporte'].values() for i in v)
    for fila in a:
        k=fila['shots_por_clase']
        rows=list(csv.DictReader((tmp_path/f'a/predicciones_{k}shot.csv').open()))
        y=[r['actividad_real'] for r in rows]; p=[r['prediccion'] for r in rows]
        assert fila['accuracy'] == accuracy_score(y,p)
        assert fila['f1_macro'] == f1_score(y,p,average='macro')
        assert fila['muestras_soporte'] == 5*k
        assert set(int(r['indice_consulta']) for r in rows) == consulta


def test_lector_zip_formato_real_con_senal_artificial(tmp_path):
    """Ejercita ejes y antena del lector real, con señal artificial pequeña."""
    archivo=tmp_path/'S5.zip'
    with zipfile.ZipFile(archivo,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for i,c in enumerate('ABCGK'):
            csi=np.ones((8,2048,4),dtype=np.complex128)*(i+1)
            csi[:,:,1]=100
            f=io.BytesIO();savemat(f,{'csi':csi});z.writestr(f'S5/S5a_{c}.mat',f.getvalue())
    salida=preparar_zip(archivo,tmp_path/'S5.npz','S5',longitud=4)
    d=leer_features(salida)
    assert d['X'].shape == (10,24)
    np.testing.assert_allclose(d['X'][:,0],np.repeat(np.arange(1,6),2))
    assert np.all(d['X'][:,1::3] == 0)
    assert json.loads(salida.with_suffix('.json').read_text())['antena'] == 0


def test_npz_incompleto(tmp_path):
    p=tmp_path/'roto.npz';np.savez(p,X=np.ones((3,4)))
    with pytest.raises(ValueError,match='incompleto'):leer_features(p)
