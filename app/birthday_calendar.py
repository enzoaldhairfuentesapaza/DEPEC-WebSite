"""Calendario anual de cumpleaños: día y mes, sin publicar año ni edad."""
import calendar
from datetime import date,timedelta
from .community_data import local_now

MONTHS=['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']

def birthday_calendar(items,requested=None):
    today=local_now().date()
    if not requested:first=today.replace(day=1)
    elif requested.isdigit():first=date(today.year,int(requested),1)
    else:first=date.fromisoformat(requested+'-01' if len(requested)==7 else requested).replace(day=1)
    # Dejamos margen para navegar sin desbordar los límites de datetime.
    if not 1901<=first.year<=9998:raise ValueError('Año fuera de rango.')
    weeks=calendar.Calendar(firstweekday=0).monthdatescalendar(first.year,first.month)
    visible=sorted([p for p in items if p['month']==first.month],key=lambda p:(p['day'],p['name']))
    return dict(first=first,weeks=weeks,items=visible,month_name=MONTHS[first.month-1],
                previous=(first-timedelta(days=1)).replace(day=1).isoformat(),
                following=(first+timedelta(days=32)).replace(day=1).isoformat(),
                leap_birthday=first.month==2 and not calendar.isleap(first.year) and any(p['day']==29 for p in visible))

def private_birthdays(records):
    output=[]
    for item in records:
        if item['d'].get('public_birthday')!='Sí':continue
        try:born=date.fromisoformat(item['d'].get('date',''))
        except (ValueError,TypeError):continue
        output.append(dict(id=item['id'],name=item['d']['title'],group_name=item['group_name'],color=item['color'],month=born.month,day=born.day,demo=False))
    return output
