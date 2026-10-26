"""Genera una vista estática del diseño con datos ficticios; no altera tu base."""
import html
import re
import sqlite3
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from app import create_app
from app.seed import seed

root=Path(__file__).resolve().parent
out=root/'preview';out.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as folder:
    app=create_app(dict(TESTING=True,DATABASE=str(Path(folder)/'preview.sqlite'),UPLOAD_FOLDER=str(Path(folder)/'uploads')))
    db=sqlite3.connect(app.config['DATABASE']);db.row_factory=sqlite3.Row
    db.executescript((root/'app'/'schema.sql').read_text(encoding='utf-8'));seed(db)
    client=app.test_client()
    def local_url(raw):
        url=html.unescape(raw);parts=urlsplit(url);path=parts.path
        if parts.scheme or url.startswith('#'):return url
        if path.startswith('/static/'):return '../app/static/'+path[len('/static/'):]+('?' + parts.query if parts.query else '')
        if path.startswith('/archivos/'):
            row=db.execute('SELECT static_name FROM media_files WHERE id=?',(int(path.rsplit('/',1)[1]),)).fetchone()
            if row and row['static_name']:return '../app/static/'+row['static_name']
        if path.startswith('/directiva/'):
            ids=path.split('/');row=db.execute('SELECT photo FROM leader_profiles WHERE user_id=? AND group_id=?',(int(ids[2]),int(ids[3]))).fetchone()
            if row and row['photo'].startswith('demo:'):return '../app/static/'+row['photo'][5:]
        if path.startswith('/miembros/'):
            uid=int(path.split('/')[2]);row=db.execute('SELECT avatar,photo FROM member_profiles WHERE user_id=?',(uid,)).fetchone()
            if row:return '../app/static/avatars/'+row['avatar']+'.svg'
        if path.startswith('/iglesia/'):
            gid=int(path.split('/')[2]);name={1:'depec-logo.jpg',3:'jorge-chavez.jpg',5:'jerusalen.jpg'}.get(gid,'church-placeholder.svg')
            return '../app/static/images/'+name
        if path=='/':
            gid=parse_qs(parts.query).get('group',[''])[0]
            if gid in ['', '1','3']:
                return ('jorge-chavez.html' if gid=='3' else 'index.html')+('#'+parts.fragment if parts.fragment else '')
        return 'http://127.0.0.1:5000'+url
    for endpoint,filename in [('/','index.html'),('/?group=3','jorge-chavez.html')]:
        response=client.get(endpoint);assert response.status_code==200
        source=response.get_data(as_text=True)
        source=re.sub(r'(src|href)="([^"]+)"',lambda m:m.group(1)+'="'+html.escape(local_url(m.group(2)),quote=True)+'"',source)
        notice='<div class="retro-demo-notice" style="padding:12px 24px"><span>VISTA ESTÁTICA</span> Diseño de ejemplo. Calendario, álbumes y formularios completos al ejecutar iniciar.bat.</div>'
        source=source.replace('<main id="main-content"',notice+'<main id="main-content"',1)
        (out/filename).write_text(source,encoding='utf-8')
    db.close()
print('Vista previa creada en preview/index.html y preview/jorge-chavez.html')
