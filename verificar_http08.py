"""Prueba HTTP limitada a la instancia descartable servidor_lab08.py, puerto 8768."""
import csv
import http.cookiejar
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--salida',type=Path,required=True)
    args=parser.parse_args()
    base='http://127.0.0.1:8768'
    jar=http.cookiejar.CookieJar()
    cliente=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    with cliente.open(base+'/login/',timeout=15) as r:
        assert r.status==200
    token=next(c.value for c in jar if c.name=='csrftoken')
    data=urllib.parse.urlencode({'username':'investigador_lab08','password':'Lab08_temporal_2026!',
                               'csrfmiddlewaretoken':token}).encode()
    with cliente.open(base+'/login/',data,timeout=15) as r:
        assert r.status==200 and r.url==base+'/'
    cookie='; '.join(f'{c.name}={c.value}' for c in jar)
    def pedir(i):
        ruta=('/','/datasets/','/experimentos/')[i%3]
        req=urllib.request.Request(base+ruta,headers={'Cookie':cookie})
        start=time.perf_counter()
        try:
            with urllib.request.urlopen(req,timeout=15) as r:
                contenido=r.read();status=r.status
                correcto=b'investigador_lab08' in contenido
        except urllib.error.HTTPError as e:status=e.code;correcto=False
        except (OSError,TimeoutError):status=0;correcto=False
        return {'ruta':ruta,'status':status,'contenido_autenticado':correcto,'ms':1000*(time.perf_counter()-start)}
    filas=[]
    for n in (1,4,8):
        with ThreadPoolExecutor(max_workers=n) as pool:
            filas.extend({'concurrencia':n,**f} for f in pool.map(pedir,range(30)))
    args.salida.mkdir(parents=True,exist_ok=True)
    with (args.salida/'http_carga.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(filas[0]));w.writeheader();w.writerows(filas)
    try:
        cliente.open(base+'/experimentos/1/',timeout=15)
        acceso=200
    except urllib.error.HTTPError as e:acceso=e.code
    resumen={'peticiones':len(filas),'correctas':sum(f['status']==200 and f['contenido_autenticado'] for f in filas),
             'experimento_otro_propietario_status':acceso,
             'alcance':'GET autenticados, 1/4/8 hilos, servidor de desarrollo; no capacidad de producción ni entrenamiento concurrente'}
    (args.salida/'http_resumen.json').write_text(json.dumps(resumen,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(resumen,ensure_ascii=False))
    if resumen['correctas']!=90 or acceso!=404:raise SystemExit(1)


if __name__=='__main__':main()
