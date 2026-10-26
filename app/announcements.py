"""Anuncios temporales de cada organización. Fechas locales de Perú."""
import json
from math import ceil
from .community_data import LIMA, local_now
from datetime import datetime


def announcement_state(data,at=None):
    if data.get('status')!='Publicado':return data.get('status','Borrador')
    at=at or local_now()
    try:
        start=datetime.fromisoformat(data['date']);end=datetime.fromisoformat(data['end_date'])
        if start.tzinfo or end.tzinfo or end<=start:return 'Inválido'
    except (ValueError,KeyError,TypeError):return 'Inválido'
    if at<start:return 'Programado'
    if at>=end:return 'Vencido'
    return 'Vigente'


def countdown_label(seconds):
    seconds=max(0,ceil(seconds));days,rest=divmod(seconds,86400);hours,rest=divmod(rest,3600);minutes,seconds=divmod(rest,60)
    return (f'{days}d ' if days else '')+f'{hours:02d}h {minutes:02d}min {seconds:02d}s'


def active_announcements(connection,group_id,at=None):
    at=at or local_now();items=[]
    for row in connection.execute("SELECT r.id,r.data,g.name group_name FROM records r JOIN groups g ON g.id=r.group_id WHERE r.module='announcements' AND r.group_id=?",(group_id,)):
        try:data=json.loads(row['data'])
        except (TypeError,ValueError):continue
        if announcement_state(data,at)!='Vigente':continue
        end=datetime.fromisoformat(data['end_date'])
        items.append(dict(id=row['id'],d=data,group_name=row['group_name'],end_at=end.replace(tzinfo=LIMA).isoformat(),deadline_ms=int(end.replace(tzinfo=LIMA).timestamp()*1000),remaining=countdown_label((end-at).total_seconds())))
    priority={'Urgente':0,'Importante':1,'Informativo':2}
    return sorted(items,key=lambda item:(priority.get(item['d'].get('category'),2),item['deadline_ms'],item['id']))
