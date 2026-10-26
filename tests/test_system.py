import io
import json
import sqlite3
from datetime import date,timedelta
from pathlib import Path
import pytest
from app import create_app
from app.seed import seed


@pytest.fixture()
def app(tmp_path):
    app=create_app(dict(TESTING=True,DATABASE=str(tmp_path/'db.sqlite'),UPLOAD_FOLDER=str(tmp_path/'uploads'),SECRET_KEY='test-secret'))
    con=sqlite3.connect(app.config['DATABASE'])
    con.executescript((Path(__file__).parents[1]/'app'/'schema.sql').read_text(encoding='utf-8'))
    seed(con); con.close()
    return app

@pytest.fixture()
def client(app): return app.test_client()

def token(client):
    client.get('/login')
    with client.session_transaction() as session: return session['csrf']

def login(client,email='admin@depec.demo'):
    response=client.post('/login',data={'csrf':token(client),'email':email,'password':'DepecDemo2026!'})
    assert response.status_code==302
    with client.session_transaction() as session: return session['csrf']

def record(app,module,gid=2):
    with sqlite3.connect(app.config['DATABASE']) as db:
        return db.execute('SELECT id FROM records WHERE module=? AND group_id=? LIMIT 1',(module,gid)).fetchone()[0]

def payload():
    return dict(group_id='2',title='Prueba funcional',body='Descripción del evento',date=date.today().isoformat()+'T10:00',end_date=date.today().isoformat()+'T12:00',location='Local',category='Encuentro',visibility='public',status='Programado',capacity='1')

def test_all_pages_render(client,app):
    for path in ['/','/?group=2','/login','/calendar?public=1']:
        assert client.get(path).status_code==200,path
    login(client)
    for path in ['/panel','/calendar','/birthdays','/organization','/reports','/audit','/account']:
        assert client.get(path).status_code==200,path
    from app.modules import MODULES
    for module in MODULES:
        if module in ['gallery','announcements']:
            assert client.get('/manage/'+module).status_code==200
            assert client.get('/manage/'+module+'/new').status_code==200
            continue
        for path in [f'/manage/{module}',f'/manage/{module}/new',f'/manage/{module}/{record(app,module)}/edit',f'/export/{module}']:
            assert client.get(path).status_code==200,path
    assert client.get(f'/participation/{record(app,"events")}').status_code==200

def test_anonymous_cannot_access_private_data(client,app):
    for path in ['/manage/members','/manage/finance','/export/members','/organization',f'/records/{record(app,"documents")}/file']:
        assert client.get(path).status_code==302
    public=client.get('/').get_data(as_text=True)
    assert 'Andrea Demo' not in public and 'Ofrenda de la semana' not in public

def test_csrf_required(client):
    assert client.post('/login',data={'email':'admin@depec.demo','password':'DepecDemo2026!'}).status_code==400

def test_group_isolation_and_forged_scope(client,app):
    csrf=login(client,'israel@depec.demo')
    foreign=record(app,'members',3)
    assert client.get(f'/manage/members/{foreign}/edit').status_code==403
    assert client.post(f'/records/{foreign}/delete',data={'csrf':csrf}).status_code==403
    assert 'Demo 3-' not in client.get('/export/members?group=3').get_data(as_text=True)
    data=payload(); data.update(csrf=csrf,group_id='3')
    assert client.post('/manage/events/new',data=data).status_code==403
    own=record(app,'events',2)
    assert client.post(f'/manage/events/{own}/edit',data=data).status_code==403

def test_role_permissions(client,app):
    login(client,'tesoreria@depec.demo')
    assert client.get(f'/manage/members/{record(app,"members")}/edit').status_code==403
    assert client.get('/manage/finance/new').status_code==200
    client.post('/logout',data={'csrf':token(client)})
    login(client,'secretaria@depec.demo')
    assert client.get('/manage/finance/new').status_code==403
    assert client.get('/manage/members/new').status_code==200
    client.post('/logout',data={'csrf':token(client)})
    login(client,'vocal@depec.demo')
    assert client.get('/manage/events/new').status_code==403
    assert client.get('/manage/members/new').status_code==403

def test_depec_president_consolidates_groups(client,app):
    login(client,'presidencia@depec.demo')
    assert client.get(f'/manage/members/{record(app,"members",7)}/edit').status_code==200
    assert 'Demo 7-' in client.get('/export/members').get_data(as_text=True)

def test_create_edit_delete_event_and_audit(client,app):
    csrf=login(client)
    data=payload(); data['csrf']=csrf
    assert client.post('/manage/events/new',data=data).status_code==302
    with sqlite3.connect(app.config['DATABASE']) as db:
        rid=db.execute('SELECT max(id) FROM records').fetchone()[0]
    assert 'Prueba funcional' in client.get('/calendar').get_data(as_text=True)
    data['title']='Evento actualizado'
    assert client.post(f'/manage/events/{rid}/edit',data=data).status_code==302
    assert 'Evento actualizado' in client.get('/manage/events').get_data(as_text=True)
    assert client.post(f'/records/{rid}/delete',data={'csrf':csrf}).status_code==302
    assert 'Eliminó events' in client.get('/audit').get_data(as_text=True)

def test_invalid_dates_amount_and_select_rejected(client,app):
    csrf=login(client)
    data=payload(); data.update(csrf=csrf,end_date='2020-01-01T10:00')
    assert 'Revisa los datos' in client.post('/manage/events/new',data=data).get_data(as_text=True)
    data.update(end_date=payload()['end_date'],visibility='secret')
    assert 'Revisa los datos' in client.post('/manage/events/new',data=data).get_data(as_text=True)
    for amount in ['-5','NaN','1.001']:
        data=dict(csrf=csrf,group_id=2,title='Gasto inválido',category='Egreso',amount=amount,date=date.today().isoformat(),account='Efectivo',subcategory='Otro',status='Aprobado',event_id='',body='')
        assert 'Revisa los datos' in client.post('/manage/finance/new',data=data).get_data(as_text=True)

def test_private_file_access_and_upload_validation(client,app):
    csrf=login(client)
    rid=record(app,'documents',3)
    data=dict(csrf=csrf,group_id=3,title='Documento privado',category='Acta',date=date.today().isoformat(),period='2026',status='Presentado',body='Acta privada',attachment=(io.BytesIO(b'%PDF-1.4 test'),'acta.pdf'))
    assert client.post(f'/manage/documents/{rid}/edit',data=data).status_code==302
    assert client.get(f'/records/{rid}/file').status_code==200
    client.post('/logout',data={'csrf':csrf}); csrf=login(client,'israel@depec.demo')
    assert client.get(f'/records/{rid}/file').status_code==403
    data.update(csrf=csrf,group_id=2,attachment=(io.BytesIO(b'<script>alert(1)</script>'),'attack.html'))
    assert 'Revisa los datos' in client.post('/manage/documents/new',data=data).get_data(as_text=True)

def test_future_draft_internal_posts_not_public(client,app):
    csrf=login(client)
    base=dict(csrf=csrf,group_id=2,title='NO DEBE SER PUBLICO',body='Contenido interno',date=date.today().isoformat()+'T00:00',category='Noticia',visibility='public',status='Borrador')
    client.post('/manage/posts/new',data=base)
    base.update(status='Publicado',visibility='internal'); client.post('/manage/posts/new',data=base)
    base.update(visibility='public',date=(date.today()+timedelta(days=10)).isoformat()+'T10:00'); client.post('/manage/posts/new',data=base)
    assert 'NO DEBE SER PUBLICO' not in client.get('/').get_data(as_text=True)

def test_attendance_capacity_and_foreign_member(client,app):
    csrf=login(client)
    data=payload(); data['csrf']=csrf; client.post('/manage/events/new',data=data)
    with sqlite3.connect(app.config['DATABASE']) as db:
        event=db.execute('SELECT max(id) FROM records').fetchone()[0]
        ids=[r[0] for r in db.execute("SELECT id FROM records WHERE module='members' AND group_id=2 LIMIT 2")]
    url=f'/participation/{event}'
    assert client.post(url,data=dict(csrf=csrf,member_id=ids[0],status='Inscrito')).status_code==302
    assert client.post(url,data=dict(csrf=csrf,member_id=ids[1],status='Inscrito')).status_code==400
    assert client.post(url,data=dict(csrf=csrf,member_id=record(app,'members',3),status='Presente')).status_code==400

def test_csv_formula_protection(client,app):
    csrf=login(client)
    data=payload(); data.update(csrf=csrf,title='=HYPERLINK("bad")')
    client.post('/manage/events/new',data=data)
    assert "'=HYPERLINK" in client.get('/export/events').get_data(as_text=True)

def test_revoke_assignment_removes_access(client,app):
    csrf=login(client)
    client.post('/organization',data=dict(csrf=csrf,action='revoke',id='1'))
    client.post('/logout',data={'csrf':csrf})
    login(client,'israel@depec.demo')
    assert client.get('/manage/events/new').status_code==403

def test_password_change(client):
    csrf=login(client)
    assert client.post('/account',data=dict(csrf=csrf,old='DepecDemo2026!',new='NuevaClave123456!')).status_code==200
    client.post('/logout',data={'csrf':csrf})
    response=client.post('/login',data=dict(csrf=token(client),email='admin@depec.demo',password='NuevaClave123456!'))
    assert response.status_code==302

def test_invalid_calendar_month_and_birthdays(client):
    assert client.get('/calendar?month=bad').status_code==400
    login(client)
    assert client.get('/birthdays?month=13').status_code==400

def test_additional_permission_can_be_granted_and_revoked(client,app):
    csrf=login(client)
    assert client.post('/organization',data=dict(csrf=csrf,action='grant',user_id=6,group_id=2,module='posts',can_write='1')).status_code==302
    client.post('/logout',data={'csrf':csrf}); csrf=login(client,'vocal@depec.demo')
    assert client.get('/manage/posts/new').status_code==200
    data=dict(csrf=csrf,group_id=3,title='Ajeno',body='No autorizado',date=date.today().isoformat()+'T10:00',category='Noticia',visibility='public',status='Publicado')
    assert client.post('/manage/posts/new',data=data).status_code==403
    client.post('/logout',data={'csrf':csrf}); csrf=login(client)
    assert client.post('/organization',data=dict(csrf=csrf,action='revoke_grant',id=1)).status_code==302
    client.post('/logout',data={'csrf':csrf}); login(client,'vocal@depec.demo')
    assert client.get('/manage/posts/new').status_code==403

def test_gallery_public_visibility_and_fake_image_rejected(client,app):
    import base64
    from PIL import Image
    buffer=io.BytesIO(); Image.new('RGB',(100,160),'red').save(buffer,format='PNG'); png=buffer.getvalue()
    csrf=login(client)
    data=dict(csrf=csrf,group_id=2,title='Recuerdo público',body='Galería de prueba',date=date.today().isoformat(),visibility='public',status='Publicado',attachment=(io.BytesIO(png),'foto.png'))
    assert client.post('/manage/gallery/new',data=data).status_code==302
    with sqlite3.connect(app.config['DATABASE']) as db:
        rid=db.execute('SELECT max(id) FROM records').fetchone()[0]
    client.post('/logout',data={'csrf':csrf})
    assert 'Recuerdo público' not in client.get('/').get_data(as_text=True)  # Hero DEPEC no incluye archivos de otra iglesia
    assert client.get(f'/media/{rid}').status_code==200
    csrf=login(client)
    data.update(csrf=csrf,visibility='internal',attachment=(io.BytesIO(png),'foto.png'))
    client.post(f'/manage/gallery/{rid}/edit',data=data)
    client.post('/logout',data={'csrf':csrf})
    assert client.get(f'/media/{rid}').status_code==403
    csrf=login(client)
    data.update(csrf=csrf,attachment=(io.BytesIO(b'<script>bad</script>'),'false.png'))
    assert 'Revisa los datos' in client.post('/manage/gallery/new',data=data).get_data(as_text=True)

def test_clean_install_cli_bootstrap(tmp_path):
    app=create_app(dict(TESTING=True,DATABASE=str(tmp_path/'clean.sqlite'),UPLOAD_FOLDER=str(tmp_path/'uploads')))
    runner=app.test_cli_runner()
    assert runner.invoke(args=['init-db']).exit_code==0
    assert runner.invoke(args=['seed-demo']).exit_code==0
    with sqlite3.connect(app.config['DATABASE']) as db:
        assert db.execute('SELECT count(*) FROM groups').fetchone()[0]==7
        assert db.execute('SELECT name FROM groups WHERE id=1').fetchone()[0]=='DEPEC'
    assert runner.invoke(args=['seed-demo']).exit_code!=0

# v0.3: reglas de comunidad, archivos, membresía y presentación.
def image_upload(width=180,height=260,name='imagen.png'):
    from PIL import Image
    content=io.BytesIO();Image.new('RGB',(width,height),'#bd123b').save(content,format='PNG');content.seek(0)
    return content,name

def create_album(client,csrf,gid=1,title='Álbum de prueba',visibility='public'):
    return client.post('/panel/archivos',data=dict(csrf=csrf,action='album',group_id=gid,title=title,description='Fotos del encuentro',visibility=visibility))

def test_community_pages_and_logo(client,app):
    for path in ['/','/?group=5','/solicitar-registro','/iglesia/5/foto','/static/community.css','/static/images/depec-logo.jpg','/iglesia/2/foto']:
        assert client.get(path).status_code==200,path
    body=client.get('/').get_data(as_text=True)
    assert 'Arequipa sureste' in body and 'daily-verse' in body and 'native-mobile-menu' in body
    assert 'images/jerusalen.jpg' not in body # imagen real va por ruta de iglesia
    login(client)
    for path in ['/panel/archivos','/panel/directiva','/panel/identidad','/panel/aprobaciones']:
        assert client.get(path).status_code==200,path

def test_hero_uses_only_organization_files_and_preserves_kind(client,app):
    csrf=login(client)
    for gid,title,kind in [(2,'EXCLUSIVO DE ISRAEL','Fotografía'),(1,'AFICHE DE DEPEC','Afiche'),(1,'FOTO DE DEPEC','Fotografía')]:
        data=dict(csrf=csrf,action='upload',group_id=gid,title=title,kind=kind,visibility='public',photos=image_upload())
        assert client.post('/panel/archivos',data=data).status_code==302
    body=client.get('/').get_data(as_text=True)
    assert 'AFICHE DE DEPEC' in body and 'FOTO DE DEPEC' in body
    assert 'EXCLUSIVO DE ISRAEL' not in body
    own=client.get('/?group=2').get_data(as_text=True)
    assert 'EXCLUSIVO DE ISRAEL' in own and 'AFICHE DE DEPEC' not in own

def test_album_contributors_scopes_and_metadata(client,app):
    csrf=login(client);create_album(client,csrf,1,'Global');create_album(client,csrf,3,'Jorge')
    with sqlite3.connect(app.config['DATABASE']) as db:
        aid=db.execute("SELECT id FROM albums WHERE title='Global'").fetchone()[0]
        foreign=db.execute("SELECT id FROM albums WHERE title='Jorge'").fetchone()[0]
    client.post('/logout',data={'csrf':csrf});csrf=login(client,'israel@depec.demo')
    data=dict(csrf=csrf,action='upload',group_id=2,album_id=aid,title='Servicio juntos',kind='Fotografía',visibility='public',photos=image_upload())
    assert client.post('/panel/archivos',data=data).status_code==302
    body=client.get(f'/album/{aid}').get_data(as_text=True)
    assert 'Presidencia Israel' in body and 'SEC Israel' in body and 'Servicio juntos' in body and 'ID #' in body
    data.update(album_id=foreign,photos=image_upload())
    assert client.post('/panel/archivos',data=data).status_code==403
    data.update(album_id=aid,group_id=3,photos=image_upload())
    assert client.post('/panel/archivos',data=data).status_code==403

def test_member_registration_moderation_and_no_privilege_escalation(client,app):
    csrf=token(client)
    assert 'Solicitud enviada' in client.post('/solicitar-registro',data=dict(csrf=csrf,name='Miembro de prueba',email='persona@example.com',password='ClaveMiembro2026!',group_id=2)).get_data(as_text=True)
    # No puede iniciar sesión pendiente de aprobación.
    assert client.post('/login',data=dict(csrf=token(client),email='persona@example.com',password='ClaveMiembro2026!')).status_code==200
    csrf=login(client,'israel@depec.demo')
    with sqlite3.connect(app.config['DATABASE']) as db:mid=db.execute("SELECT id FROM memberships ORDER BY id DESC LIMIT 1").fetchone()[0]
    assert client.post('/panel/aprobaciones',data=dict(csrf=csrf,action='membership',id=mid,decision='Aprobado')).status_code==302
    client.post('/logout',data={'csrf':csrf})
    assert client.post('/login',data=dict(csrf=token(client),email='persona@example.com',password='ClaveMiembro2026!')).status_code==302
    assert client.get('/panel').location.endswith('/mi-comunidad')
    assert client.get('/manage/members').status_code==403
    with client.session_transaction() as session:csrf=session['csrf']
    message='Encontré una comunidad que me ayuda a crecer.'
    assert client.post('/mi-comunidad',data=dict(csrf=csrf,body=message)).status_code==302
    assert message not in client.get('/').get_data(as_text=True)
    with sqlite3.connect(app.config['DATABASE']) as db:message_id=db.execute('SELECT max(id) FROM community_messages').fetchone()[0]
    client.post('/logout',data={'csrf':csrf});csrf=login(client,'israel@depec.demo')
    assert client.post('/panel/aprobaciones',data=dict(csrf=csrf,action='message',id=message_id,decision='Aprobado')).status_code==302
    assert message in client.get('/').get_data(as_text=True)
    assert message not in client.get('/?group=3').get_data(as_text=True)

def test_foreign_church_cannot_approve_members(client,app):
    csrf=token(client);client.post('/solicitar-registro',data=dict(csrf=csrf,name='Otra persona',email='otra@example.com',password='OtraClave123456!',group_id=3))
    with sqlite3.connect(app.config['DATABASE']) as db:mid=db.execute('SELECT max(id) FROM memberships').fetchone()[0]
    csrf=login(client,'israel@depec.demo')
    assert client.post('/panel/aprobaciones',data=dict(csrf=csrf,action='membership',id=mid,decision='Aprobado')).status_code==403

def test_event_defaults_maps_orientation_and_automatic_completion(client,app):
    from app.community_data import local_now
    csrf=login(client)
    address='Dirección de prueba 123, Arequipa'
    assert client.post('/panel/identidad',data=dict(csrf=csrf,group_id=2,color='#265ba1',description='Comunidad',church='Israel',address=address,maps_url='https://maps.app.goo.gl/ejemplo',schedule='Sábados')).status_code==302
    data=payload();data.update(csrf=csrf,location='',date=(local_now()+timedelta(days=2)).isoformat(timespec='minutes'),end_date=(local_now()+timedelta(days=2,hours=3)).isoformat(timespec='minutes'),attachment=image_upload(400,180),media_kind='Afiche')
    assert client.post('/manage/events/new',data=data).status_code==302
    with sqlite3.connect(app.config['DATABASE']) as db:
        rid,raw=db.execute("SELECT id,data FROM records WHERE module='events' ORDER BY id DESC LIMIT 1").fetchone()
        saved=json.loads(raw);assert saved['location']==address and saved['image_width']==400
    result=client.get(f'/calendar?public=1&event={rid}').get_data(as_text=True)
    assert 'calendar-detail' in result and 'y-event landscape' in result and 'https://maps.app.goo.gl/ejemplo' in result and 'Pronto' in result
    with sqlite3.connect(app.config['DATABASE']) as db:
        saved['end_date']=(local_now()-timedelta(hours=1)).isoformat(timespec='minutes');saved['date']=(local_now()-timedelta(hours=3)).isoformat(timespec='minutes')
        db.execute('UPDATE records SET data=? WHERE id=?',(json.dumps(saved),rid))
    client.get('/')
    with sqlite3.connect(app.config['DATABASE']) as db:assert json.loads(db.execute('SELECT data FROM records WHERE id=?',(rid,)).fetchone()[0])['status']=='Finalizado'

def test_verse_changes_daily_and_stays_stable():
    from app.community_data import daily_verse
    a=date(2026,10,26)
    assert daily_verse(a)==daily_verse(a)
    assert daily_verse(a)['reference']!=daily_verse(a+timedelta(days=1))['reference']

def test_leader_profile_publication_and_local_theme(client,app):
    csrf=login(client,'israel@depec.demo')
    data=dict(csrf=csrf,user_id=2,group_id=2,message='Aquí seguimos creciendo juntos.',phone='+51999000111',published='1',photo=image_upload())
    assert client.post('/panel/directiva',data=data).status_code==302
    body=client.get('/?group=2').get_data(as_text=True)
    assert 'Aquí seguimos creciendo juntos.' in body and 'tel:+51999000111' in body
    assert 'Aquí seguimos creciendo juntos.' not in client.get('/').get_data(as_text=True)
    assert client.get('/directiva/2/2/foto').status_code==200
    data.update(user_id=5,group_id=1,photo=image_upload())
    assert client.post('/panel/directiva',data=data).status_code==403

def test_unsafe_maps_link_rejected(client,app):
    csrf=login(client)
    response=client.post('/panel/identidad',data=dict(csrf=csrf,group_id=2,color='#265ba1',description='Prueba',address='Dirección',maps_url='javascript:alert(1)'))
    assert 'Usa un enlace HTTPS de Google Maps' in response.get_data(as_text=True)

def test_upgrade_from_v02_preserves_data_and_is_idempotent(tmp_path):
    from app.community_data import upgrade_schema
    path=tmp_path/'old.sqlite'
    old_schema=(Path(__file__).parents[1]/'app'/'schema.sql').read_text(encoding='utf-8').split('CREATE TABLE IF NOT EXISTS albums')[0].replace(",photo TEXT NOT NULL DEFAULT '',maps_url TEXT NOT NULL DEFAULT ''",'')
    with sqlite3.connect(path) as db:
        db.executescript(old_schema)
        db.execute("INSERT INTO groups(id,name,kind,color) VALUES(1,'DEPEC','DEPEC','#bd123b')")
        db.execute("INSERT INTO users(id,name,email,password) VALUES(1,'Nombre conservado','guardado@example.com','hash')")
        db.execute("INSERT INTO records(module,group_id,data,author_id,created,updated) VALUES('tasks',1,?,1,'2026-01-01','2026-01-01')",(json.dumps(dict(title='No borrar esta tarea')),))
        db.commit();upgrade_schema(db);upgrade_schema(db)
        assert db.execute('SELECT name FROM users WHERE id=1').fetchone()[0]=='Nombre conservado'
        assert json.loads(db.execute('SELECT data FROM records').fetchone()[0])['title']=='No borrar esta tarea'
        assert 'maps_url' in [r[1] for r in db.execute('PRAGMA table_info(groups)')]
        assert db.execute('PRAGMA user_version').fetchone()[0]==4
        assert db.execute('SELECT count(*) FROM media_files').fetchone()[0]==0

def test_private_album_is_not_exposed_to_foreign_church(client,app):
    csrf=login(client);create_album(client,csrf,3,'Álbum reservado','internal')
    with sqlite3.connect(app.config['DATABASE']) as db:aid=db.execute("SELECT id FROM albums WHERE title='Álbum reservado'").fetchone()[0]
    assert client.get(f'/album/{aid}').status_code==200
    client.post('/logout',data={'csrf':csrf})
    assert client.get(f'/album/{aid}').status_code==403
    login(client,'israel@depec.demo')
    assert client.get(f'/album/{aid}').status_code==403

# v0.4: portada por iglesia, contenido configurable y perfiles voluntarios.
def test_retro_demo_and_home_scope(client,app):
    from html.parser import HTMLParser
    class Layout(HTMLParser):
        def __init__(self):super().__init__();self.ids=[];self.collage_count=None;self.inside=False;self.tiles=0
        def handle_starttag(self,tag,attrs):
            a=dict(attrs)
            if a.get('id'):self.ids.append(a['id'])
            if 'retro-collage' in a.get('class',''):self.collage_count=int(a['data-count'])
    root=client.get('/').get_data(as_text=True);jc=client.get('/?group=3').get_data(as_text=True)
    page=Layout();page.feed(root)
    assert page.ids.index('grupos')<page.ids.index('eventos')
    assert page.collage_count==6
    church=Layout();church.feed(jc)
    assert 'grupos' not in church.ids and church.collage_count==6
    assert 'Más que una iglesia, una familia que camina junta' in jc
    assert 'Nos conocemos bien, compartimos la vida sin filtros' in jc
    assert 'Colosenses 3:14' in jc and 'KSo2PasAcs3HdyU36' in jc
    assert 'Fecha de aniversario por confirmar' in jc
    assert 'Perfil ficticio' in jc and 'Evento ficticio' in jc
    assert client.get('/iglesia/3/foto').status_code==200

def test_custom_hero_verse_configuration_and_anniversary(client,app):
    csrf=login(client,'israel@depec.demo')
    data=dict(csrf=csrf,group_id=2,color='#dfb82f',hero_title='Una comunidad que acompaña',hero_description='Cada día caminamos juntos.',description='Nuestra casa',verse_mode='custom',verse_lines='Referencia A | Primer texto\nReferencia B | Segundo texto',founded_date='2000-11-15',anniversary_note='Dato de prueba',address='Dirección de ejemplo 12',maps_url='')
    assert client.post('/panel/identidad',data=data).status_code==302
    html=client.get('/?group=2').get_data(as_text=True)
    assert 'Una comunidad que acompaña' in html and ('Primer texto' in html or 'Segundo texto' in html)
    assert 'Dato de prueba' in html
    data['verse_mode']='off'
    client.post('/panel/identidad',data=data)
    assert 'class="daily-verse"' not in client.get('/?group=2').get_data(as_text=True)
    data.update(group_id=3)
    assert client.post('/panel/identidad',data=data).status_code==403

def test_member_profile_requires_approval_and_is_self_managed(client,app):
    # Cuenta de demostración ya verificada; no tiene permisos de líder.
    assert client.post('/login',data=dict(csrf=token(client),email='miembro-0@demo.depec.local',password='DepecDemo2026!')).status_code==302
    with client.session_transaction() as session:csrf=session['csrf'];uid=session['uid']
    assert client.get('/mi-perfil').status_code==200
    message='Mi perfil personalizado todavía debe revisarse.'
    data=dict(csrf=csrf,message=message,verse_ref='Salmos 23:1',verse_text='El Señor es mi pastor.',likes='Música',gifts='Escuchar',dislikes='La falta de respeto',avatar='pez',published='1')
    assert client.post('/mi-perfil',data=data).status_code==302
    assert message not in client.get('/?group=3').get_data(as_text=True)
    assert client.get(f'/miembros/{uid}/foto').status_code==200
    client.post('/logout',data={'csrf':csrf})
    assert client.get(f'/miembros/{uid}/foto').status_code==403
    csrf=login(client,'israel@depec.demo')
    assert client.post('/panel/aprobaciones',data=dict(csrf=csrf,action='profile',id=uid,decision='Aprobado')).status_code==403
    client.post('/logout',data={'csrf':csrf});csrf=login(client)
    assert client.post('/panel/aprobaciones',data=dict(csrf=csrf,action='profile',id=uid,decision='Aprobado')).status_code==302
    assert message in client.get('/?group=3').get_data(as_text=True)
    assert message in client.get('/').get_data(as_text=True)
    assert message not in client.get('/?group=2').get_data(as_text=True)
    client.post('/logout',data={'csrf':csrf})
    assert client.get(f'/miembros/{uid}/foto').status_code==200

def test_profile_opt_out_removes_public_card(client,app):
    client.post('/login',data=dict(csrf=token(client),email='miembro-1@demo.depec.local',password='DepecDemo2026!'))
    with client.session_transaction() as session:csrf=session['csrf'];uid=session['uid']
    assert client.post('/mi-perfil',data=dict(csrf=csrf,avatar='cruz',message='Este perfil está retirado.')).status_code==302
    assert 'Este perfil está retirado.' not in client.get('/').get_data(as_text=True)
    with sqlite3.connect(app.config['DATABASE']) as db:assert db.execute('SELECT published FROM member_profiles WHERE user_id=?',(uid,)).fetchone()[0]==0

def test_anniversary_and_configured_daily_verses():
    from app.community_data import anniversary,group_verse
    data=dict(founded_date='2000-11-15',anniversary_note='Ejemplo')
    assert anniversary(data,date(2026,11,14))['years']==25
    assert anniversary(data,date(2026,11,15))['years']==26
    assert anniversary(data,date(2026,11,16))['next_years']==27
    assert anniversary(dict(founded_date='',anniversary_note=''),date(2026,10,26)) is None
    assert anniversary(dict(founded_date='2000-02-29',anniversary_note=''),date(2025,2,28))['years']==25
    group=dict(verse_mode='custom',custom_verses=json.dumps([dict(reference='A',text='Texto A'),dict(reference='B',text='Texto B')]))
    a=group_verse(group,date(2026,10,26));b=group_verse(group,date(2026,10,27))
    assert a['reference']!=b['reference']

def test_retro_demo_idempotent_and_does_not_run_on_real_install(tmp_path):
    from app.community_data import upgrade_schema
    from app.retro_demo import seed_visual_demo
    db=sqlite3.connect(tmp_path/'blank.sqlite')
    db.executescript((Path(__file__).parents[1]/'app'/'schema.sql').read_text(encoding='utf-8'));upgrade_schema(db)
    db.execute("INSERT INTO groups(name,kind,color) VALUES('DEPEC','DEPEC','#bd123b')")
    db.execute("INSERT INTO users(name,email,password) VALUES('Usuario real','real@example.com','hash')")
    assert seed_visual_demo(db) is False
    assert db.execute('SELECT count(*) FROM users').fetchone()[0]==1
    db.close()

def notice_payload(csrf,gid=3,**changes):
    from app.community_data import local_now
    at=local_now()
    values=dict(csrf=csrf,group_id=gid,title='Aviso temporal de prueba',body='Esta semana se cancela el culto por elecciones, nos vemos la siguiente semana.',category='Importante',date=(at-timedelta(hours=1)).isoformat(timespec='minutes'),end_date=(at+timedelta(days=2)).isoformat(timespec='minutes'),status='Publicado')
    values.update(changes);return values

def test_announcement_board_empty_hidden_and_scoped(client,app):
    assert 'id="anuncios"' not in client.get('/').get_data(as_text=True)
    assert 'id="anuncios"' not in client.get('/?group=3').get_data(as_text=True)
    csrf=login(client)
    assert client.post('/manage/announcements/new',data=notice_payload(csrf)).status_code==302
    html=client.get('/?group=3').get_data(as_text=True)
    assert 'id="anuncios"' in html and 'Esta semana se cancela el culto' in html
    assert 'data-announcement-deadline=' in html and 'Vence en ' in html and '(Perú)' in html
    assert 'id="anuncios"' not in client.get('/').get_data(as_text=True)
    assert 'id="anuncios"' not in client.get('/?group=2').get_data(as_text=True)

def test_announcement_states_and_expiration_boundaries():
    from app.announcements import announcement_state,countdown_label
    from datetime import datetime
    at=datetime(2026,10,26,12)
    d=dict(status='Publicado',date='2026-10-26T12:00',end_date='2026-10-26T13:00')
    assert announcement_state(d,at)=='Vigente'
    assert announcement_state(d,at-timedelta(seconds=1))=='Programado'
    assert announcement_state(d,at+timedelta(hours=1))=='Vencido'
    assert announcement_state({**d,'status':'Borrador'},at)=='Borrador'
    assert announcement_state({**d,'status':'Retirado'},at)=='Retirado'
    assert countdown_label(90061)=='1d 01h 01min 01s'

def test_drafts_future_expired_and_withdrawn_not_public(client,app):
    from app.community_data import local_now
    csrf=login(client);now=local_now()
    variants=[dict(status='Borrador'),dict(status='Retirado'),dict(date=(now+timedelta(days=1)).isoformat(timespec='minutes')),dict(date=(now-timedelta(days=2)).isoformat(timespec='minutes'),end_date=(now-timedelta(seconds=1)).isoformat(timespec='seconds'))]
    for variant in variants:assert client.post('/manage/announcements/new',data=notice_payload(csrf,**variant)).status_code==302
    html=client.get('/?group=3').get_data(as_text=True)
    assert 'id="anuncios"' not in html and 'Esta semana se cancela el culto' not in html

def test_announcements_permissions_validation_and_priority(client,app):
    csrf=login(client,'israel@depec.demo')
    assert client.post('/manage/announcements/new',data=notice_payload(csrf,gid=3)).status_code==403
    assert client.post('/manage/announcements/new',data=notice_payload(csrf,gid=2,end_date='2020-01-01T10:00')).status_code==200
    assert client.post('/manage/announcements/new',data=notice_payload(csrf,gid=2,date='2026-10-26T10:00+00:00',end_date='2026-10-27T10:00+00:00')).status_code==200
    assert client.post('/manage/announcements/new',data=notice_payload(csrf,gid=2,title='Aviso normal',category='Informativo')).status_code==302
    assert client.post('/manage/announcements/new',data=notice_payload(csrf,gid=2,title='Aviso prioritario',category='Urgente')).status_code==302
    html=client.get('/?group=2').get_data(as_text=True)
    assert html.index('Aviso prioritario')<html.index('Aviso normal')
    with sqlite3.connect(app.config['DATABASE']) as db:rid=db.execute("SELECT max(id) FROM records WHERE module='announcements'").fetchone()[0]
    payload=notice_payload(csrf,gid=2,title='Aviso prioritario',status='Retirado')
    assert client.post(f'/manage/announcements/{rid}/edit',data=payload).status_code==302
    assert 'Aviso prioritario' not in client.get('/?group=2').get_data(as_text=True)

def test_depec_announcement_and_expiry_without_database_deletion(client,app):
    from app.community_data import local_now
    csrf=login(client)
    assert client.post('/manage/announcements/new',data=notice_payload(csrf,gid=1)).status_code==302
    assert 'id="anuncios"' in client.get('/').get_data(as_text=True)
    with sqlite3.connect(app.config['DATABASE']) as db:
        rid,raw=db.execute("SELECT id,data FROM records WHERE module='announcements'").fetchone();d=json.loads(raw)
        d['date']=(local_now()-timedelta(days=2)).isoformat(timespec='seconds');d['end_date']=(local_now()-timedelta(seconds=1)).isoformat(timespec='seconds')
        db.execute('UPDATE records SET data=? WHERE id=?',(json.dumps(d),rid))
    assert 'id="anuncios"' not in client.get('/').get_data(as_text=True)
    with sqlite3.connect(app.config['DATABASE']) as db:assert db.execute('SELECT count(*) FROM records WHERE id=?',(rid,)).fetchone()[0]==1

@pytest.mark.parametrize('broken_kind', ['Fotografía'.encode('utf-8').decode('cp1252'), 'Fotografía'.encode('utf-8').decode('latin1'), 'FotografÃa'])
def test_windows_media_constraint_repaired_before_startup_demo(tmp_path,broken_kind):
    path=tmp_path/'windows.sqlite'
    schema=(Path(__file__).parents[1]/'app'/'schema.sql').read_text(encoding='utf-8')
    with sqlite3.connect(path) as db:
        db.executescript(schema.replace("'Fotografía'", "'"+broken_kind+"'"))
        for gid,name in [(1,'DEPEC'),(2,'SEC Israel'),(3,'SEC Jorge Chávez')]:
            db.execute('INSERT INTO groups(id,name,kind,color) VALUES(?,?,?,?)',(gid,name,'SEC','#3453d1'))
        db.execute("INSERT INTO users(id,name,email,password,admin) VALUES(1,'Nombre conservado','admin@depec.demo','hash-sin-cambios',1)")
        aid=db.execute("INSERT INTO albums(group_id,title,created_by,created) VALUES(3,'Álbum conservado',1,'2026-01-01')").lastrowid
        db.execute("INSERT INTO media_files(id,group_id,album_id,title,kind,filename,width,height,uploaded_by,visibility,created) VALUES(42,3,?,'Foto conservada',?,'no-mover.jpg',640,480,1,'internal','2026-01-01')",(aid,broken_kind))
        db.execute("INSERT INTO media_files(id,group_id,title,kind,width,height,uploaded_by,created) VALUES(43,1,'Afiche conservado','Afiche',600,800,1,'2026-01-01')")
        db.execute("INSERT INTO records(module,group_id,data,author_id,created,updated) VALUES('finance',3,?,1,'2026-01-01','2026-01-01')",(json.dumps({'title':'Ingreso conservado','amount':'123.45'}),))
        db.execute('CREATE INDEX media_custom_title ON media_files(title)')
    config=dict(TESTING=True,DATABASE=str(path),UPLOAD_FOLDER=str(tmp_path/'uploads'),SECRET_KEY='test')
    app=create_app(config)
    assert app.test_client().get('/?group=3').status_code==200
    with sqlite3.connect(path) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
        assert db.execute('SELECT album_id,title,kind,filename,visibility FROM media_files WHERE id=42').fetchone()==(aid,'Foto conservada','Fotografía','no-mover.jpg','internal')
        assert db.execute('SELECT kind FROM media_files WHERE id=43').fetchone()[0]=='Afiche'
        assert db.execute('SELECT password FROM users WHERE id=1').fetchone()[0]=='hash-sin-cambios'
        assert json.loads(db.execute("SELECT data FROM records WHERE module='finance'").fetchone()[0])['amount']=='123.45'
        assert db.execute("SELECT 1 FROM sqlite_master WHERE name='media_custom_title'").fetchone()
        assert db.execute("SELECT 1 FROM site_settings WHERE key='retro-demo-v04'").fetchone()
        counts=[db.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in ['media_files','users','records']]
    backups=list(tmp_path.glob('windows.sqlite.pre-utf8-*.bak'))
    assert len(backups)==1
    with sqlite3.connect(backups[0]) as db:
        assert db.execute('SELECT kind FROM media_files WHERE id=42').fetchone()[0]==broken_kind
        assert db.execute('SELECT count(*) FROM users').fetchone()[0]==1
    create_app(config)
    with sqlite3.connect(path) as db:
        assert counts==[db.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in ['media_files','users','records']]
    assert len(list(tmp_path.glob('windows.sqlite.pre-utf8-*.bak')))==1


def test_sql_files_always_read_as_utf8(tmp_path,monkeypatch):
    original=Path.read_text
    def checked(path,*args,**kwargs):
        if path.suffix=='.sql':assert kwargs.get('encoding')=='utf-8'
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'read_text',checked)
    app=create_app(dict(TESTING=True,DATABASE=str(tmp_path/'fresh.sqlite'),UPLOAD_FOLDER=str(tmp_path/'uploads'),SECRET_KEY='test'))
    runner=app.test_cli_runner()
    assert runner.invoke(args=['init-db']).exit_code==0
    assert runner.invoke(args=['seed-demo']).exit_code==0
    create_app(dict(TESTING=True,DATABASE=app.config['DATABASE'],UPLOAD_FOLDER=app.config['UPLOAD_FOLDER'],SECRET_KEY='test'))
