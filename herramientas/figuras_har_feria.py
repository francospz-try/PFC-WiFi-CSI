"""Figuras reproducibles de las evidencias HAR; nunca escribe capturas ni modelos."""
import csv
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch
from src.pfc07.csi_piloto import comparar

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/feria_2026/graficos'

def save(fig,name):
    OUT.mkdir(parents=True,exist_ok=True)
    fig.savefig(OUT/(name+'.svg'),bbox_inches='tight')
    fig.savefig(OUT/(name+'.png'),dpi=220,bbox_inches='tight')

def main():
    audit=json.loads((OUT.parent/'auditoria/resultados.json').read_text(encoding='utf-8'))
    report=json.loads((ROOT/'outputs/csi_reconocimiento/binario.json').read_text(encoding='utf-8'))
    sessions=report['sessions']
    fig,_=comparar(ROOT/'datos_locales/csi_piloto'/sessions[0],ROOT/'datos_locales/csi_piloto'/sessions[1])
    save(fig,'A_senales_csi')
    quality=audit['quality']; names=[('Q' if q['label']=='quietud' else 'C')+str(i+1) for i,q in enumerate(quality)]
    names=[q['session'].split('T')[1][:6]+'\n'+q['label'] for q in quality]
    fig=Figure(figsize=(12,8),layout='constrained'); axes=fig.subplots(2,2)
    for ax,(key,title) in zip(axes.flat,[('valid_csi','Registros CSI válidos'),('observed_hz','Registros/s (duración host registrada)'),('sequence_gaps','Saltos de secuencia'),('median_rssi','RSSI mediano (dBm)')]):
        vals=[q['recalculated'][key] for q in quality]
        ax.bar(names,vals,color=['#237b9c' if q['label']=='quietud' else '#c76e25' for q in quality]); ax.set_title(title)
        ax.tick_params(axis='x',labelsize=7);ax.grid(axis='y',alpha=.2)
        for i,v in enumerate(vals): ax.text(i,v,f'{v:.1f}' if key=='observed_hz' else str(v),ha='center',va='bottom',fontsize=8)
    fig.suptitle('Ocho capturas reales · har_habitacion_1m\nIdentificación por hora UTC; saltos no distinguen pérdida radio de pérdida USB')
    save(fig,'B_calidad_adquisicion')
    for key,name,title in [('internal_holdout','C_evaluacion_interna','Evaluación interna · cuatro sesiones de ajuste / dos reservadas'),('reserved_final','D_pruebas_nuevas_matriz','Dos grabaciones nuevas · modelo operativo ajustado con seis')]:
        m=np.array(audit[key]['confusion']); fig=Figure(figsize=(7,6),layout='constrained'); ax=fig.subplots()
        ax.imshow(m,cmap='Blues',vmin=0,vmax=55)
        for i in range(2):
            for j in range(2): ax.text(j,i,str(m[i,j]),ha='center',va='center',fontsize=30,color='white' if m[i,j]>35 else '#17324d')
        ax.set_xticks([0,1],['Quietud','Caminar']);ax.set_yticks([0,1],['Quietud','Caminar']);ax.set_xlabel('Clase predicha');ax.set_ylabel('Actividad declarada')
        stats=audit[key]; fig.suptitle(title+'\nAccuracy '+f"{stats['accuracy']*100:.2f}%"+' · F1 macro '+f"{stats['macro_f1']:.4f}",fontsize=12)
        fig.text(.5,-.03,'Conteos por ventanas de 1 s, temporalmente correlacionadas. No validación poblacional.',ha='center',fontsize=9)
        save(fig,name)
    tests=audit['reserved_final']['sessions'];fig=Figure(figsize=(9,5),layout='constrained');ax=fig.subplots();left=np.zeros(len(tests))
    for cls,color in [('quietud','#237b9c'),('caminar','#c76e25')]:
        vals=np.array([100*s['counts'][cls]/s['windows'] for s in tests]);ax.barh([s['true'] for s in tests],vals,left=left,label=cls,color=color)
        for i,v in enumerate(vals):ax.text(left[i]+v/2,i,f'{v:.1f}%',ha='center',va='center',color='white',fontsize=14)
        left+=vals
    ax.set_xlim(0,100);ax.set_xlabel('Proporción de ventanas asignadas (%) · no probabilidad calibrada');ax.legend(loc='upper center',bbox_to_anchor=(.5,-.15),ncol=2)
    ax.set_title('Reconocimiento de grabaciones nuevas\n55 ventanas por grabación; mayoría correcta en 2/2 sesiones')
    save(fig,'D_proporciones_ventanas')
    fig=Figure(figsize=(14,4.5));ax=fig.subplots();ax.set_xlim(0,14);ax.set_ylim(0,4);ax.axis('off')
    labels=['ESP32-C6\ntransmisor','ESP32-C6\nreceptor','Adquisición\nPython','Procesamiento\nCSI','Prototipos\nHAR','Aplicación\nDjango']
    links=['ESP-NOW','USB','raw.log','6 indicadores','Resultado']
    for i,label in enumerate(labels):
        x=.15+i*2.32;ax.add_patch(FancyBboxPatch((x,1.5),1.9,1.1,boxstyle='round,pad=.1',facecolor='#e6f0f5',edgecolor='#237b9c'));ax.text(x+.95,2.05,label,ha='center',va='center',fontsize=12)
        if i<5:
            ax.annotate('',xy=(x+2.25,2.05),xytext=(x+2.0,2.05),arrowprops={'arrowstyle':'->','color':'#17324d'});ax.text(x+2.12,2.9,links[i],ha='center',fontsize=9)
    ax.text(7,.65,'Implementado: captura y análisis por grabación. El reconocimiento en vivo es trabajo futuro.',ha='center',fontsize=13)
    ax.set_title('Arquitectura real del piloto Wi-Fi CSI',fontsize=18)
    save(fig,'E_arquitectura')
    rows=list(csv.DictReader((OUT.parent/'auditoria/ventanas.csv').open(encoding='utf-8')))
    fig=Figure(figsize=(12,5),layout='constrained');axs=fig.subplots(2,1,sharex=True)
    for ax,s in zip(axs,tests):
        rs=[r for r in rows if r['session']==s['session'] and r['predicted_final']]
        t=[float(r['start_s']) for r in rs]; yp=[int(r['predicted_final']=='caminar') for r in rs]
        ax.scatter(t,yp,c=['#237b9c' if y==0 else '#c76e25' for y in yp],s=24);ax.set_yticks([0,1],['Quietud','Caminar']);ax.set_ylim(-.3,1.3);ax.grid(alpha=.2);ax.set_title(s['session']+' · declarada '+s['true'],fontsize=10)
    axs[-1].set_xlabel('Inicio de ventana desde primer paquete (s)');fig.suptitle('Distribución temporal de predicciones · modelo operativo sin modificar')
    save(fig,'F_predicciones_temporales')
    print('Figuras escritas en',OUT)

if __name__=='__main__': main()
