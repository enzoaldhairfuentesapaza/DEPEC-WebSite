"""Resuelve enlaces cortos de Maps sin aceptar destinos externos arbitrarios."""
import json
import re
import time
from urllib.parse import parse_qs, unquote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

HOSTS={'maps.app.goo.gl','goo.gl','www.google.com','google.com','maps.google.com'}

def trusted_map_url(url):
    parts=urlsplit(url)
    return parts.scheme=='https' and parts.netloc in HOSTS

class MapsRedirects(HTTPRedirectHandler):
    max_redirections=4
    max_repeats=2
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if not trusted_map_url(newurl):raise ValueError('El enlace no redirige a Google Maps.')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def coordinates_from_url(url):
    if not trusted_map_url(url):raise ValueError('Usa un enlace HTTPS de Google Maps.')
    decoded=unquote(url)
    pair=re.search(r'!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)',decoded)
    if pair:lat,lng=pair.groups()
    else:
        query=parse_qs(urlsplit(url).query)
        value=(query.get('q') or query.get('query') or [''])[0]
        pair=re.fullmatch(r'\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*',value)
        if not pair:raise ValueError('Google Maps no devolvió coordenadas del lugar. Puedes pegar su código de inserción.')
        lat,lng=pair.groups()
    if not (-90<=float(lat)<=90 and -180<=float(lng)<=180):raise ValueError('Coordenadas inválidas.')
    return lat+','+lng

def resolve_map_embed(url,opener=None):
    if not trusted_map_url(url):raise ValueError('Usa un enlace HTTPS de Google Maps.')
    try:coordinates=coordinates_from_url(url)
    except ValueError:
        opener=opener or build_opener(MapsRedirects())
        with opener.open(Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=3) as response:
            coordinates=coordinates_from_url(response.geturl())
    return 'https://www.google.com/maps?'+urlencode({'q':coordinates,'z':17,'output':'embed'})

def sync_short_maps(connection):
    """Un intento por enlace y día al iniciar; un fallo de red nunca impide arrancar."""
    if not connection.execute("SELECT 1 FROM sqlite_master WHERE name='site_settings'").fetchone():return
    for gid,url,embed in connection.execute("SELECT id,maps_url,maps_embed_url FROM groups WHERE kind!='DEPEC' AND maps_url!=''").fetchall():
        if embed or urlsplit(url).hostname not in ['maps.app.goo.gl','goo.gl']:continue
        key=f'maps-resolution-{gid}'
        prior=connection.execute('SELECT value FROM site_settings WHERE key=?',(key,)).fetchone()
        if prior:
            try:
                cached=json.loads(prior[0])
                if cached.get('url')==url and time.time()-cached.get('attempted',0)<86400:continue
            except (ValueError,TypeError):pass
        try:
            resolved=resolve_map_embed(url)
        except Exception:
            resolved=''
        if resolved:connection.execute('UPDATE groups SET maps_embed_url=? WHERE id=?',(resolved,gid))
        connection.execute('INSERT INTO site_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,json.dumps({'url':url,'attempted':time.time(),'resolved':bool(resolved)})))
        connection.commit()
