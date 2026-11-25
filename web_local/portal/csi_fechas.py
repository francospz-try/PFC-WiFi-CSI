"""Presentacion de fechas guardadas; nunca modifica los metadatos originales."""
from datetime import datetime, timezone, timedelta

LIMA=timezone(timedelta(hours=-5))

def fecha_local(value):
    if not value: return 'Sin fecha registrada'
    try:
        dt=datetime.fromisoformat(value.replace('Z','+00:00'))
        if dt.tzinfo is None: return 'Fecha sin zona horaria'
        return dt.astimezone(LIMA).strftime('%d/%m/%Y %H:%M:%S')
    except (ValueError,TypeError,AttributeError): return 'Fecha no valida'

def con_fechas(meta):
    d=dict(meta)
    d['inicio_local']=fecha_local(d.get('start_utc'))
    d['fin_local']=fecha_local(d.get('end_utc'))
    return d
