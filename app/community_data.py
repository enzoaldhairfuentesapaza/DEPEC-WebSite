"""Migración aditiva y reglas de presentación compartidas."""
import json
import re
import sqlite3
from datetime import datetime, date
from pathlib import Path
from random import Random
from urllib.parse import urlencode
from urllib.parse import urlsplit
from html.parser import HTMLParser
from zoneinfo import ZoneInfo
from PIL import Image, UnidentifiedImageError

LIMA=ZoneInfo('America/Lima')

def local_now():
    return datetime.now(LIMA).replace(tzinfo=None)

def repair_media_encoding(connection):
    """Repara el CHECK creado al leer UTF-8 como Windows-1252; conserva IDs y archivos."""
    row=connection.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='media_files'").fetchone()
    if not row:return
    schema=row[0]
    pattern=r"CHECK\s*\(\s*kind\s+IN\s*\(\s*'Afiche'\s*,\s*'(Fotograf[^']*)'\s*\)\s*\)"
    match=re.search(pattern,schema,re.IGNORECASE)
    if not match or match.group(1)=='Fotografía':return
    # No usamos writable_schema ni desactivamos las restricciones de integridad.
    if connection.in_transaction:
        raise RuntimeError('La reparación de media_files debe iniciarse sin una transacción pendiente.')
    database=connection.execute('PRAGMA database_list').fetchone()[2]
    if database:
        source=Path(database)
        backup=source.with_name(source.name+'.pre-utf8-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.bak')
        with sqlite3.connect(backup) as destination:connection.backup(destination)
    repaired=schema[:match.start(1)]+'Fotografía'+schema[match.end(1):]
    repaired=re.sub(r'^(CREATE\s+TABLE\s+)(?:IF\s+NOT\s+EXISTS\s+)?[\["`]?media_files[\]"`]?',r'\1media_files_utf8',repaired,count=1,flags=re.IGNORECASE)
    extras=[r[0] for r in connection.execute("SELECT sql FROM sqlite_master WHERE tbl_name='media_files' AND type IN ('index','trigger') AND sql IS NOT NULL")]
    columns=[r[1] for r in connection.execute('PRAGMA table_info(media_files)')]
    quoted=', '.join('"'+name.replace('"','""')+'"' for name in columns)
    selection=', '.join('CASE WHEN kind=? THEN ? ELSE kind END' if name=='kind' else '"'+name.replace('"','""')+'"' for name in columns)
    connection.execute('SAVEPOINT repair_media_utf8')
    try:
        connection.execute(repaired)
        connection.execute(f'INSERT INTO media_files_utf8 ({quoted}) SELECT {selection} FROM media_files',(match.group(1),'Fotografía'))
        connection.execute('DROP TABLE media_files')
        connection.execute('ALTER TABLE media_files_utf8 RENAME TO media_files')
        for statement in extras:connection.execute(statement)
        if connection.execute('PRAGMA foreign_key_check(media_files)').fetchone():
            raise RuntimeError('La reparación detectó referencias inválidas en media_files.')
        connection.execute('RELEASE repair_media_utf8')
    except Exception:
        connection.execute('ROLLBACK TO repair_media_utf8')
        connection.execute('RELEASE repair_media_utf8')
        raise

def upgrade_schema(connection):
    if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='groups'").fetchone():
        return
    repair_media_encoding(connection)
    if connection.execute('PRAGMA user_version').fetchone()[0]<3:
        connection.execute("UPDATE groups SET color='#bd123b' WHERE id=1 AND color='#d46a3b'")
    names={r[1] for r in connection.execute('PRAGMA table_info(groups)')}
    for name,definition in [('photo',"TEXT NOT NULL DEFAULT ''"),('maps_url',"TEXT NOT NULL DEFAULT ''"),('maps_embed_url',"TEXT NOT NULL DEFAULT ''")]:
        if name not in names:connection.execute(f'ALTER TABLE groups ADD COLUMN {name} {definition}')
    connection.executescript((Path(__file__).parent/'community_schema.sql').read_text(encoding='utf-8'))
    for name,definition in [('hero_title',"TEXT NOT NULL DEFAULT ''"),('hero_description',"TEXT NOT NULL DEFAULT ''"),('verse_mode',"TEXT NOT NULL DEFAULT 'daily'"),('custom_verses',"TEXT NOT NULL DEFAULT '[]'"),('founded_date',"TEXT NOT NULL DEFAULT ''"),('anniversary_note',"TEXT NOT NULL DEFAULT ''")]:
        if name not in names:connection.execute(f'ALTER TABLE groups ADD COLUMN {name} {definition}')
    connection.executescript((Path(__file__).parent/'retro_schema.sql').read_text(encoding='utf-8'))
    # Incorpora adjuntos anteriores sin borrar ni mover los archivos originales.
    upload_root=Path(connection.execute('PRAGMA database_list').fetchone()[2]).parent/'uploads'
    for rid,module,gid,raw,uid,created in connection.execute("SELECT id,module,group_id,data,author_id,created FROM records WHERE module IN ('events','posts','gallery')").fetchall():
        data=json.loads(raw)
        if not data.get('attachment'):continue
        prior=connection.execute('SELECT id,album_id FROM media_files WHERE record_id=?',(rid,)).fetchone()
        aid=None
        if module=='gallery':
            title='Galería anterior · '+connection.execute('SELECT name FROM groups WHERE id=?',(gid,)).fetchone()[0]
            album=connection.execute('SELECT id FROM albums WHERE group_id=? AND title=?',(gid,title)).fetchone()
            aid=album[0] if album else connection.execute('INSERT INTO albums(group_id,title,description,created_by,created) VALUES(?,?,?,?,?)',(gid,title,'Fotografías conservadas de la versión anterior.',uid,created)).lastrowid
        if prior:
            if aid and not prior[1]:connection.execute('UPDATE media_files SET album_id=? WHERE id=?',(aid,prior[0]))
            continue
        width,height=int(data.get('image_width',1)),int(data.get('image_height',1))
        try:
            with Image.open(upload_root/data['attachment']) as im:width,height=im.size
        except (OSError,ValueError):pass
        connection.execute('INSERT INTO media_files(group_id,album_id,record_id,title,kind,filename,width,height,uploaded_by,visibility,created) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(gid,aid,rid,data['title'],data.get('media_kind') or ('Fotografía' if module=='gallery' else 'Afiche'),data['attachment'],width,height,uid,data.get('visibility','internal'),created))
    connection.execute('PRAGMA user_version=4')
    connection.commit()

def picture_info(file):
    try:
        image=Image.open(file.stream)
        if image.format not in ['PNG','JPEG'] or image.width*image.height>40_000_000:
            raise ValueError('Usa una imagen PNG o JPEG de hasta 40 megapíxeles.')
        width,height=image.size
        if image.getexif().get(274,1) in [5,6,7,8]:width,height=height,width
        file.stream.seek(0)
        return width,height
    except (UnidentifiedImageError,OSError,Image.DecompressionBombError) as exc:
        file.stream.seek(0)
        raise ValueError('La imagen no es válida.') from exc

GENERIC_EVENT_IMAGES={
    'Encuentro':('images/event-encuentro.svg',720,1000),
    'Comunidad':('images/event-comunidad.svg',1200,700),
    'Servicio':('images/event-servicio.svg',1200,700),
}

def normalize_map_embed(value):
    """Acepta el enlace de inserción o el iframe de Compartir > Insertar un mapa."""
    value=value.strip()
    if not value:return ''
    if value.startswith('<'):
        class FrameParser(HTMLParser):
            sources=[]
            def handle_starttag(self,tag,attrs):
                if tag=='iframe':self.sources.append(dict(attrs).get('src',''))
        parser=FrameParser();parser.sources=[];parser.feed(value)
        if len(parser.sources)!=1:raise ValueError('Pega un único iframe de Google Maps.')
        value=parser.sources[0]
    parsed=urlsplit(value)
    if (parsed.scheme!='https' or parsed.netloc not in ['www.google.com','maps.google.com','google.com']
        or parsed.path not in ['/maps/embed','/maps/embed/'] or not parsed.query or len(value)>6000):
        raise ValueError('Usa el enlace de Google Maps de Compartir → Insertar un mapa, no el enlace corto.')
    return value

def local_map(group):
    exact=normalize_map_embed(group['maps_embed_url']) if group['maps_embed_url'] else ''
    address=group['address'] or ''
    confirmed=address and not any(word in address.lower() for word in ['ejemplo','por confirmar','ver ubicación'])
    # El enlace corto no revela coordenadas: no inventamos un marcador para la iglesia.
    query=address if confirmed else 'Arequipa, Perú'
    return dict(src=exact or 'https://maps.google.com/maps?'+urlencode({'q':query,'z':15 if confirmed else 12,'output':'embed'}),
                reference=not bool(exact or confirmed),link=group['maps_url'] or 'https://www.google.com/maps/search/?'+urlencode({'api':1,'query':query}))

def event_presentation(data,group,at=None):
    result=dict(data)
    end=result.get('end_date') or result.get('date','')
    if result.get('status')=='Cancelado':state='Cancelado'
    elif result.get('status') in ['Realizado','Finalizado'] or end and end < (at or local_now()).isoformat(timespec='seconds'):state='Finalizado'
    elif result.get('status')=='Reprogramado':state='Reprogramado'
    elif result.get('date','') <= (at or local_now()).isoformat(timespec='seconds'):state='En curso'
    else:state='Pronto'
    result['display_status']=state
    mode=result.get('image_mode') or 'Imagen propia'
    result['image_source']='none'
    result['display_static']=''
    if mode=='Imagen genérica':
        preset=GENERIC_EVENT_IMAGES.get(result.get('generic_image'),GENERIC_EVENT_IMAGES['Encuentro'])
        result['image_source']='static';result['display_static']=preset[0]
        width,height=preset[1:]
    elif mode!='Sin imagen' and (result.get('attachment') or result.get('poster_static')):
        result['image_source']='upload' if result.get('attachment') else 'static'
        result['display_static']=result.get('poster_static','')
        width,height=int(result.get('image_width',0)),int(result.get('image_height',0))
    else:width,height=1,0
    layout=result.get('card_layout','Automático')
    result['orientation']=('portrait' if layout=='Vertical' else 'landscape' if layout=='Horizontal' else 'landscape' if width>height else 'portrait')
    result['has_image']=result['image_source']!='none'
    result['location']=result.get('location') or group['address'] or 'Lugar por confirmar'
    address=result.get('event_address') or result.get('location') or group['address']
    result['maps_link']='https://www.google.com/maps/search/?'+urlencode({'api':1,'query':address}) if address and 'por confirmar' not in address.lower() and 'ejemplo' not in address.lower() else ''
    if result.get('event_address','') in ['',group['address']] and result['location']==group['address'] and group['maps_url']:
        result['maps_link']=group['maps_url']
    return result

# Textos breves de Reina-Valera 1909 (dominio público), sin servicio externo.
VERSES=[('Salmos 133:1','¡Mirad cuán bueno y cuán delicioso es habitar los hermanos igualmente en uno!'),('Filipenses 4:13','Todo lo puedo en Cristo que me fortalece.'),('1 Juan 4:19','Nosotros le amamos á él, porque él nos amó primero.'),('Salmos 119:105','Lámpara es á mis pies tu palabra, y lumbrera á mi camino.'),('1 Corintios 16:14','Todas vuestras cosas sean hechas con caridad.'),('Romanos 12:21','No seas vencido de lo malo; mas vence con el bien el mal.'),('1 Tesalonicenses 5:16','Estad siempre gozosos.'),('1 Tesalonicenses 5:17','Orad sin cesar.'),('Salmos 23:1','Jehová es mi pastor; nada me faltará.'),('Salmos 46:1','Dios es nuestro amparo y fortaleza, nuestro pronto auxilio en las tribulaciones.'),('Proverbios 17:17','En todo tiempo ama el amigo; y el hermano para la angustia es nacido.'),('Mateo 5:9','Bienaventurados los pacificadores: porque ellos serán llamados hijos de Dios.'),('Romanos 12:12','Gozosos en la esperanza; sufridos en la tribulación; constantes en la oración.'),('Salmos 150:6','Todo lo que respira alabe á JAH. Aleluya.'),('1 Juan 4:8','El que no ama, no conoce á Dios; porque Dios es amor.')]
VERSE_ORDER=list(range(len(VERSES)));Random('DEPEC-Arequipa').shuffle(VERSE_ORDER)
def daily_verse(day=None):
    day=day or local_now().date()
    ref,text=VERSES[VERSE_ORDER[day.toordinal()%len(VERSE_ORDER)]]
    return dict(reference=ref,text=text,date=day.isoformat(),version='Reina-Valera 1909')


def group_verse(group,day=None):
    day=day or local_now().date()
    if group['verse_mode']=='off':return None
    if group['verse_mode']=='custom':
        try:items=json.loads(group['custom_verses'])
        except (ValueError,TypeError):items=[]
        if items:
            item=items[day.toordinal()%len(items)]
            return dict(reference=item['reference'],text=item['text'],version=item.get('version') or 'Texto de la comunidad',date=day.isoformat())
    return daily_verse(day)


def anniversary(group,day=None):
    day=day or local_now().date()
    if not group['founded_date']:return None
    try:founded=date.fromisoformat(group['founded_date'])
    except ValueError:return None
    if founded>day:return None
    # Para un 29 de febrero, celebramos el 28 en años no bisiestos.
    try:next_day=founded.replace(year=day.year)
    except ValueError:next_day=date(day.year,2,28)
    current_anniversary=next_day
    if next_day<day:
        try:next_day=founded.replace(year=day.year+1)
        except ValueError:next_day=date(day.year+1,2,28)
    completed=day.year-founded.year-int(day<current_anniversary)
    return dict(date=founded.isoformat(),next_date=next_day.isoformat(),years=completed,next_years=next_day.year-founded.year,note=group['anniversary_note'])


def contrast_color(hex_color):
    try:
        value=hex_color.lstrip('#');parts=[int(value[i:i+2],16)/255 for i in [0,2,4]]
        linear=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in parts]
        return '#18151b' if sum(x*w for x,w in zip(linear,[.2126,.7152,.0722]))>.38 else '#ffffff'
    except (ValueError,IndexError):return '#ffffff'

def verse_lines(value):
    try:return '\n'.join(item['reference']+' | '+item['text'] for item in json.loads(value))
    except (ValueError,KeyError,TypeError):return ''
