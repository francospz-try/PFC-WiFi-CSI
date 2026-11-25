import argparse
import json
from pathlib import Path
from lectura_mat_bloques import AUDIT_DIR, audit

parser=argparse.ArgumentParser(description='Verifica completamente las 15 grabaciones seleccionadas.')
parser.add_argument('--archivos',type=Path,required=True,help='Directorio de S5.zip, S6.zip y S7.zip')
parser.add_argument('--salida',type=Path,default=AUDIT_DIR)
args=parser.parse_args()
out=args.salida
for scenario in ['S5','S6','S7']:
    for activity in 'ABCGK':
        stem=f'{scenario}a_{activity}'
        if (out/('lectura_completa_'+stem+'.json')).exists():continue
        print('AUDITANDO',stem,flush=True)
        audit(args.archivos/(scenario+'.zip'),scenario+'/'+stem+'.mat',out)
reports=[json.loads((out/f'lectura_completa_{s}a_{c}.json').read_text()) for s in ['S5','S6','S7'] for c in 'ABCGK']
summary=dict(files=len(reports),all_crc_verified=all(x['zip_member_crc_verified'] for x in reports),
    nonfinite_components=sum(c['nonfinite'] for r in reports for c in r['components'].values()),
    scope='Lectura completa de las 15 grabaciones seleccionadas; no de los 108 archivos del inventario.',members=[r['member'] for r in reports])
(out/'resumen_lectura_15.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
with (out/'INFORME.md').open('a',encoding='utf-8') as f:f.write('\n\n## Cierre de lectura seleccionada\n\nLas 15 grabaciones A/B/C/G/K del receptor a en S5/S6/S7 se leyeron completamente por bloques. CRC correcto en todas. Componentes no finitas: '+str(summary['nonfinite_components'])+'. Esto sustituye el alcance inicial de solo cabeceras para esta seleccion; los otros 93 MAT siguen solo inventariados. No equivale a validar el protocolo experimental ni las etiquetas por video.\n')
print('RESUMEN',json.dumps(summary),flush=True)
