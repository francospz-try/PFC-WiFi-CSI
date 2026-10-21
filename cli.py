"""Punto de entrada sin interfaz web: python cli.py --help"""
import argparse
import json
from pathlib import Path
from src.pfc07.auditoria import listar_mat, inspeccionar_mat, guardar_auditoria
from src.pfc07.procesamiento import preparar_escenario, leer_features
from src.pfc07.sintetico import generar_ejemplo
from src.pfc07.evaluacion import ejecutar_experimento


def main():
    p = argparse.ArgumentParser(description='PFC07 - Herramienta local Wi-Fi CSI')
    subs = p.add_subparsers(dest='accion', required=True)
    a = subs.add_parser('inventario', help='Lista archivos .mat de ZIP/directorio')
    a.add_argument('ruta')
    a.add_argument('--salida', default='outputs/auditoria.json')
    a = subs.add_parser('inspeccionar', help='Metadatos MAT sin cargar la señal completa')
    a.add_argument('archivo')
    a = subs.add_parser('preparar', help='Prepara 5 actividades de un escenario real')
    a.add_argument('directorio')
    a.add_argument('--escenario', required=True, choices=['S5', 'S6', 'S7'])
    a.add_argument('--receptor', default='a', choices=['a', 'b', 'c'])
    a.add_argument('--eje-paquetes', type=int, required=True,
                   help='No adivinar: consultar dimensiones antes de usar')
    a.add_argument('--antena', type=int, default=0, help='Antena del receptor, 0..3 por defecto')
    a.add_argument('--n-antenas', type=int, default=4)
    a.add_argument('--longitud', type=int, default=128)
    a.add_argument('--salto', type=int, default=128)
    a.add_argument('--salida', required=True)
    a = subs.add_parser('experimento', help='Base y few-shot con .npz auditados')
    a.add_argument('--origen', required=True)
    a.add_argument('--destino', required=True)
    a.add_argument('--salida', default='outputs/experimento_real')
    a.add_argument('--semilla', type=int, default=42)
    a = subs.add_parser('demo', help='PRUEBA ARTIFICIAL, NO RESULTADOS REALES')
    a.add_argument('--salida', default='outputs/demo_sintetica')
    args = p.parse_args()
    if args.accion == 'inventario':
        contenido = listar_mat(args.ruta)
        guardar_auditoria({'tipo': 'inventario', 'archivos': contenido}, args.salida)
        print(f'Encontrados: {len(contenido)} MAT. Informe: {args.salida}')
    elif args.accion == 'inspeccionar':
        print(json.dumps(inspeccionar_mat(args.archivo), ensure_ascii=False, indent=2))
    elif args.accion == 'preparar':
        print(preparar_escenario(args.directorio, args.escenario, args.receptor,
                               args.salida, args.eje_paquetes, args.longitud, args.salto,
                               antena=args.antena, n_antenas=args.n_antenas))
    elif args.accion == 'experimento':
        o, d = leer_features(args.origen), leer_features(args.destino)
        print(json.dumps(ejecutar_experimento(o, d, args.salida, semilla=args.semilla,
                                             etiqueta='DATOS_REALES_PENDIENTES_DE_AUDITORIA'), indent=2))
    else:
        base = Path(args.salida)
        generar_ejemplo(base / 'datos')
        o = leer_features(base / 'datos' / 'S5_SINTETICO.npz')
        d = leer_features(base / 'datos' / 'S7_SINTETICO.npz')
        filas = ejecutar_experimento(o, d, base / 'resultados',
                                    etiqueta='SINTETICO_PRUEBA_SOFTWARE_NO_EVIDENCIA_CIENTIFICA')
        print('PRUEBA CON DATOS SINTÉTICOS. NO REPORTAR COMO RESULTADO EXPERIMENTAL REAL.')
        print(json.dumps(filas, indent=2))
        print(f'Generado: {base.resolve()}')


if __name__ == '__main__':
    main()
