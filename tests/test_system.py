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
    assert 'Evento actualizado' in client.get('/manage/events?group=2').get_data(as_text=True)
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

def test_attendance_without_capacity_and_foreign_member(client,app):
    csrf=login(client)
    data=payload(); data['csrf']=csrf; client.post('/manage/events/new',data=data)
    with sqlite3.connect(app.config['DATABASE']) as db:
        event=db.execute('SELECT max(id) FROM records').fetchone()[0]
        ids=[r[0] for r in db.execute("SELECT id FROM records WHERE module='members' AND group_id=2 LIMIT 2")]
    url=f'/participation/{event}'
    assert client.post(url,data=dict(csrf=csrf,member_id=ids[0],status='Inscrito')).status_code==302
    assert client.post(url,data=dict(csrf=csrf,member_id=ids[1],status='Inscrito')).status_code==302
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
    assert message not in client.get('/').get_data(as_text=True)
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

@pytest.mark.parametrize('width,height,layout,expected',[(300,700,'Automático','portrait'),(900,350,'Automático','landscape'),(300,700,'Horizontal','landscape'),(900,350,'Vertical','portrait')])
def test_event_card_orientation_and_override(width,height,layout,expected):
    from app.community_data import event_presentation
    group=dict(address='Local',maps_url='')
    data=dict(date='2030-01-01T18:00',end_date='2030-01-01T20:00',attachment='imagen.jpg',image_width=width,image_height=height,card_layout=layout)
    result=event_presentation(data,group)
    assert result['orientation']==expected and result['has_image'] and result['image_source']=='upload'


def test_event_image_modes_preserve_original_and_preview(client,app):
    from app.community_data import local_now
    csrf=login(client)
    data=payload();data.update(csrf=csrf,date=(local_now()+timedelta(days=1)).isoformat(timespec='minutes'),end_date=(local_now()+timedelta(days=1,hours=2)).isoformat(timespec='minutes'),attachment=image_upload(220,600),media_kind='Afiche',card_layout='Automático',image_mode='Imagen propia',generic_image='Encuentro')
    assert client.post('/manage/events/new',data=data).status_code==302
    with sqlite3.connect(app.config['DATABASE']) as db:
        rid,raw=db.execute("SELECT id,data FROM records WHERE module='events' ORDER BY id DESC LIMIT 1").fetchone()
        original=json.loads(raw)['attachment']
        media_id=db.execute('SELECT id FROM media_files WHERE record_id=?',(rid,)).fetchone()[0]
    assert app.test_client().get(f'/archivos/{media_id}').status_code==200
    edit=client.get(f'/manage/events/{rid}/edit').get_data(as_text=True)
    assert 'data-preview-card' in edit and 'data-event-editor' in edit and 'event-preview.js' in edit
    assert 'Imagen genérica' in edit and 'Sin imagen' in edit and 'Automático' in edit
    data.pop('attachment');data['image_mode']='Sin imagen'
    assert client.post(f'/manage/events/{rid}/edit',data=data).status_code==302
    page=client.get(f'/calendar?public=1&event={rid}').get_data(as_text=True)
    from html.parser import HTMLParser
    class SelectedCard(HTMLParser):
        def __init__(self):super().__init__();self.inside=False;self.images=[];self.classes=''
        def handle_starttag(self,tag,attrs):
            attrs=dict(attrs)
            if tag=='article' and 'y-event' in attrs.get('class',''):self.inside=True;self.classes=attrs.get('class','')
            if self.inside and tag=='img':self.images.append(attrs.get('src'))
        def handle_endtag(self,tag):
            if tag=='article':self.inside=False
    result=SelectedCard();result.feed(page)
    assert 'text-only' in result.classes and 'landscape' in result.classes and not result.images
    assert app.test_client().get(f'/archivos/{media_id}').status_code==403
    assert Path(app.config['UPLOAD_FOLDER'],original).exists()
    with sqlite3.connect(app.config['DATABASE']) as db:
        assert json.loads(db.execute('SELECT data FROM records WHERE id=?',(rid,)).fetchone()[0])['attachment']==original
    data.update(image_mode='Imagen genérica',generic_image='Comunidad')
    assert client.post(f'/manage/events/{rid}/edit',data=data).status_code==302
    result=SelectedCard();result.feed(client.get(f'/calendar?public=1&event={rid}').get_data(as_text=True))
    assert 'landscape' in result.classes and result.images==['/static/images/event-comunidad.svg']
    data['card_layout']='Vertical'
    assert client.post(f'/manage/events/{rid}/edit',data=data).status_code==302
    result=SelectedCard();result.feed(client.get(f'/calendar?public=1&event={rid}').get_data(as_text=True))
    assert 'portrait' in result.classes


def test_exact_map_configuration_and_validation(client,app):
    from app.community_data import normalize_map_embed
    url='https://www.google.com/maps/embed?pb=!1m18!2m3!3d100'
    assert normalize_map_embed('<iframe src="'+url+'" width="600"></iframe>')==url
    for invalid in ['https://evil.example/maps/embed?pb=a','javascript:alert(1)','https://www.google.com.evil.example/maps/embed?pb=a','https://maps.app.goo.gl/ejemplo','https://user@www.google.com/maps/embed?pb=a']:
        with pytest.raises(ValueError):normalize_map_embed(invalid)
    csrf=login(client,'israel@depec.demo')
    data=dict(csrf=csrf,group_id=2,color='#3453d1',maps_url='https://maps.app.goo.gl/exacto',maps_embed_url='<iframe src="'+url+'"></iframe>',address='Local por confirmar')
    assert client.post('/panel/identidad',data=data).status_code==302
    page=client.get('/?group=2').get_data(as_text=True)
    assert 'src="'+url+'"' in page and 'Ubicación de SEC Israel' in page
    assert 'src="'+url+'"' not in client.get('/?group=3').get_data(as_text=True)
    data['group_id']=3
    assert client.post('/panel/identidad',data=data).status_code==403
    data.update(group_id=2,maps_embed_url='https://evil.example/embed')
    assert 'Insertar un mapa' in client.post('/panel/identidad',data=data).get_data(as_text=True)
    with sqlite3.connect(app.config['DATABASE']) as db:assert db.execute('SELECT maps_embed_url FROM groups WHERE id=2').fetchone()[0]==url


def test_map_column_upgrade_preserves_existing_identity(tmp_path):
    from app.community_data import upgrade_schema
    path=tmp_path/'prior.sqlite'
    schema=(Path(__file__).parents[1]/'app'/'schema.sql').read_text(encoding='utf-8').replace(",maps_embed_url TEXT NOT NULL DEFAULT ''",'')
    with sqlite3.connect(path) as db:
        db.executescript(schema)
        db.execute("INSERT INTO groups(name,kind,color,maps_url,hero_title) VALUES('SEC Prueba','SEC','#3453d1','https://maps.app.goo.gl/conservar','Título conservado')")
        db.commit();upgrade_schema(db);upgrade_schema(db)
        assert db.execute('SELECT maps_embed_url,maps_url,hero_title FROM groups').fetchone()==('','https://maps.app.goo.gl/conservar','Título conservado')

# v0.4.4 — DEPEC sin sede, mapas permitidos y cumpleaños separados.
def test_depec_has_no_venue_and_events_require_their_own_location(client,app):
    root=client.get('/').get_data(as_text=True)
    assert 'class="local-map-section"' not in root and 'local-map-frame' not in root
    assert 'local-map-frame' in client.get('/?group=3').get_data(as_text=True)
    csrf=login(client)
    assert client.post('/panel/identidad',data=dict(csrf=csrf,group_id=1,color='#cc254b',address='No es una sede',church='No es una iglesia',schedule='No aplica',maps_url='https://maps.app.goo.gl/prueba')).status_code==302
    with sqlite3.connect(app.config['DATABASE']) as db:assert db.execute('SELECT address,church,schedule,maps_url,maps_embed_url FROM groups WHERE id=1').fetchone()==('','','','','')
    data=payload();data.update(csrf=csrf,group_id='1',location='',event_address='')
    assert client.post('/manage/events/new',data=data).status_code==302
    with sqlite3.connect(app.config['DATABASE']) as db:
        event=json.loads(db.execute("SELECT data FROM records WHERE module='events' ORDER BY id DESC LIMIT 1").fetchone()[0])
        assert event['location']=='Sede por confirmar'
    assert 'DEPEC coordina a las SEC y GJ' in client.get('/panel/identidad').get_data(as_text=True)


def test_maps_frames_and_local_preview_allowed_without_relaxing_other_sources(client):
    csp=client.get('/?group=3').headers['Content-Security-Policy']
    directives={part.split()[0]:part.split()[1:] for part in csp.split(';') if part.strip()}
    assert set(directives['frame-src'])=={'https://www.google.com','https://maps.google.com','https://google.com'}
    assert "'self'" in directives['default-src'] and "'none'" in directives['frame-ancestors']
    assert 'blob:' in directives['img-src']


def test_short_google_maps_resolution_and_redirect_protection():
    from app.map_locations import resolve_map_embed,MapsRedirects,coordinates_from_url
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def geturl(self):return 'https://www.google.com/maps/place/Prueba/data=!8m2!3d-16.42!4d-71.49'
    class Opener:
        def open(self,request,timeout):
            assert request.full_url=='https://maps.app.goo.gl/test' and timeout==3
            return Response()
    result=resolve_map_embed('https://maps.app.goo.gl/test',Opener())
    from app.community_data import normalize_map_embed
    assert normalize_map_embed(result)==result and 'q=-16.42%2C-71.49' in result
    assert coordinates_from_url('https://www.google.com/maps?q=-16.42,-71.49')=='-16.42,-71.49'
    for url in ['http://127.0.0.1/','https://evil.example/','https://www.google.com.evil.example/maps','https://www.google.com:444/maps']:
        with pytest.raises(ValueError):MapsRedirects().redirect_request(None,None,302,'',{},url)
    with pytest.raises(ValueError):coordinates_from_url('https://www.google.com/maps/@-16.4,-71.4,15z')


def test_map_sync_caches_failure_and_preserves_short_link(app,monkeypatch):
    from app import map_locations
    calls=[]
    def fail(url):calls.append(url);raise OSError('sin conexión')
    monkeypatch.setattr(map_locations,'resolve_map_embed',fail)
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute("UPDATE groups SET maps_embed_url='' WHERE id=3");db.commit()
        map_locations.sync_short_maps(db);map_locations.sync_short_maps(db)
        assert len(calls)==1
        assert db.execute('SELECT maps_url,maps_embed_url FROM groups WHERE id=3').fetchone()==('https://maps.app.goo.gl/KSo2PasAcs3HdyU36','')
        db.execute("DELETE FROM site_settings WHERE key='maps-resolution-3'");db.commit()
        monkeypatch.setattr(map_locations,'resolve_map_embed',lambda url:'https://www.google.com/maps?q=-16.42%2C-71.49&output=embed')
        map_locations.sync_short_maps(db)
        assert '-16.42' in db.execute('SELECT maps_embed_url FROM groups WHERE id=3').fetchone()[0]


def test_map_resolve_action_requires_church_permission(client,app,monkeypatch):
    from app import map_locations
    monkeypatch.setattr(map_locations,'resolve_map_embed',lambda url:'https://www.google.com/maps?q=-16.42%2C-71.49&output=embed')
    csrf=login(client,'israel@depec.demo')
    assert client.post('/panel/identidad/resolver-mapa',data=dict(csrf=csrf,group_id=3)).status_code==403
    assert client.post('/panel/identidad/resolver-mapa',data=dict(csrf=csrf,group_id=2)).status_code==302


def test_public_birthdays_need_consent_active_membership_and_approved_profile(client,app):
    with sqlite3.connect(app.config['DATABASE']) as db:
        uid=db.execute("SELECT id FROM users WHERE email='miembro-0@demo.depec.local'").fetchone()[0]
        db.execute("UPDATE users SET name='Cumpleaños autorizado' WHERE id=?",(uid,))
        db.execute("UPDATE member_profiles SET birthday_md='02-29',birthday_public=1,status='Aprobado',published=1 WHERE user_id=?",(uid,))
    path='/cumpleanos?group=3&month=2028-02-01'
    page=client.get(path).get_data(as_text=True)
    assert 'Cumpleaños autorizado' in page and 'birthday-month-grid' in page
    assert 'Cumpleaños autorizado' in client.get('/cumpleanos?month=2028-02-01').get_data(as_text=True)
    assert 'Cumpleaños autorizado' not in client.get('/cumpleanos?group=2&month=2028-02-01').get_data(as_text=True)
    assert 'Andrea Demo' not in page and 'birth_year' not in page
    for sql in ["UPDATE member_profiles SET birthday_public=0 WHERE user_id=?","UPDATE member_profiles SET birthday_public=1,status='Pendiente' WHERE user_id=?","UPDATE member_profiles SET status='Aprobado',published=0 WHERE user_id=?","UPDATE memberships SET status='Pendiente' WHERE user_id=?"]:
        with sqlite3.connect(app.config['DATABASE']) as db:
            db.execute("UPDATE member_profiles SET birthday_public=1,status='Aprobado',published=1 WHERE user_id=?",(uid,))
            db.execute("UPDATE memberships SET status='Aprobado' WHERE user_id=?",(uid,))
            db.execute(sql,(uid,))
        assert 'Cumpleaños autorizado' not in client.get(path).get_data(as_text=True)
    assert client.get('/cumpleanos?group=999').status_code==404
    assert client.get('/cumpleanos?month=2026-13-01').status_code==400


def test_member_can_opt_into_birthday_calendar_only_after_review(client,app):
    csrf=login(client,'miembro-0@demo.depec.local')
    with sqlite3.connect(app.config['DATABASE']) as db:uid=db.execute("SELECT id FROM users WHERE email='miembro-0@demo.depec.local'").fetchone()[0]
    data=dict(csrf=csrf,avatar='luz',message='Mensaje del cumpleaños',published='1',birthday_month='11',birthday_day='5',birthday_public='1')
    assert client.post('/mi-perfil',data=data).status_code==302
    with sqlite3.connect(app.config['DATABASE']) as db:
        assert db.execute('SELECT birthday_md,birthday_public,status FROM member_profiles WHERE user_id=?',(uid,)).fetchone()==('11-05',1,'Pendiente')
        name=db.execute('SELECT name FROM users WHERE id=?',(uid,)).fetchone()[0]
    assert name not in client.get('/cumpleanos?month=2026-11-01').get_data(as_text=True)
    leader=app.test_client();csrf_leader=login(leader)
    assert leader.post('/panel/aprobaciones',data=dict(csrf=csrf_leader,action='profile',id=uid,decision='Aprobado')).status_code==302
    assert name in client.get('/cumpleanos?month=2026-11-01').get_data(as_text=True)
    data.update(birthday_month='2',birthday_day='30')
    assert client.post('/mi-perfil',data=data).status_code==200
    with sqlite3.connect(app.config['DATABASE']) as db:assert db.execute('SELECT birthday_md FROM member_profiles WHERE user_id=?',(uid,)).fetchone()[0]=='11-05'
    data.update(birthday_month='11',birthday_day='5');data.pop('birthday_public')
    assert client.post('/mi-perfil',data=data).status_code==302
    assert name not in client.get('/cumpleanos?month=2026-11-01').get_data(as_text=True)


def test_private_birthday_calendar_is_separate_and_scoped(client):
    assert client.get('/birthdays').status_code==302
    login(client,'israel@depec.demo')
    page=client.get('/birthdays?month=10').get_data(as_text=True)
    assert 'birthday-month-grid' in page and 'calendario de eventos' in page
    assert 'Andrea Demo 2-1' in page and 'Andrea Demo 3-1' not in page
    assert 'Andrea Demo 3-1' not in client.get('/birthdays?group=3&month=10').get_data(as_text=True)
    assert client.get('/birthdays?month=13').status_code==400


def test_february_29_remains_visible_in_non_leap_year():
    from app.birthday_calendar import birthday_calendar
    person=dict(day=29,month=2,name='Ejemplo')
    data=birthday_calendar([person],'2027-02-01')
    assert data['leap_birthday'] and data['items']==[person]
    assert not birthday_calendar([person],'2028-02-01')['leap_birthday']


def test_upgrade_adds_birthday_consent_without_publishing_existing_members(tmp_path):
    path=tmp_path/'before-birthdays.sqlite'
    schema=(Path(__file__).parents[1]/'app'/'schema.sql').read_text(encoding='utf-8').replace(",birthday_md TEXT NOT NULL DEFAULT '',birthday_public INTEGER NOT NULL DEFAULT 0",'')
    with sqlite3.connect(path) as db:
        db.executescript(schema)
        db.execute("INSERT INTO groups(id,name,kind,color) VALUES(1,'DEPEC','DEPEC','#cc254b'),(2,'SEC Prueba','SEC','#3453d1')")
        db.execute("INSERT INTO users(id,name,email,password) VALUES(1,'Miembro real de prueba','real@example.com','hash')")
        db.execute("INSERT INTO memberships(user_id,group_id,status,created) VALUES(1,2,'Aprobado','2026-01-01')")
        db.execute("INSERT INTO member_profiles(user_id,message,published,status,updated) VALUES(1,'Mensaje conservado',1,'Aprobado','2026-01-01')")
    app=create_app(dict(TESTING=True,DATABASE=str(path),UPLOAD_FOLDER=str(tmp_path/'uploads'),SECRET_KEY='test'))
    with sqlite3.connect(path) as db:assert db.execute('SELECT birthday_md,birthday_public,message,status FROM member_profiles WHERE user_id=1').fetchone()==('',0,'Mensaje conservado','Aprobado')
    assert 'Miembro real de prueba' not in app.test_client().get('/cumpleanos').get_data(as_text=True)

# v0.4.5 — el collage rellena huecos sin inventar eventos.
def test_collage_covers_every_cell_for_all_six_event_orientation_combinations():
    from itertools import product
    from app.collage import build_event_collage
    for count in range(1,7):
        for orientations in product(['portrait','landscape'],repeat=count):
            events=[dict(id=i,d=dict(orientation=orientation)) for i,orientation in enumerate(orientations)]
            collage=build_event_collage(events)
            assert [tile['event']['id'] for tile in collage['events']]==list(range(count))
            for columns in [4,2,1]:
                occupied=set();all_cells=[item['placements'][columns] for item in collage['events']]
                all_cells += [f for f in collage['fillers'] if f['layout']==columns]
                for cell in all_cells:
                    assert 1<=cell['column']<=columns and cell['column']+cell['columns']-1<=columns
                    cells={(r,c) for r in range(cell['row'],cell['row']+cell['rows']) for c in range(cell['column'],cell['column']+cell['columns'])}
                    assert not occupied.intersection(cells)
                    occupied.update(cells)
                height=max(r for r,c in occupied)
                assert occupied=={(r,c) for r in range(1,height+1) for c in range(1,columns+1)}
                for filler in collage['fillers']:
                    assert (Path(__file__).parents[1]/'app'/'static'/filler['image']).is_file()
    assert not build_event_collage([])['fillers']
    assert len(build_event_collage([dict(id=i,d=dict(orientation='portrait')) for i in range(9)])['events'])==6


def test_depec_home_has_own_directive_and_no_member_directory(client):
    root=client.get('/').get_data(as_text=True)
    church=client.get('/?group=3').get_data(as_text=True)
    assert '<h2>DIRECTIVA <em>DEPEC</em></h2>' in root
    assert 'id="miembros"' not in root and 'members-grid' not in root
    assert 'id="miembros"' in church and 'members-grid' in church
    assert '<h2>Conoce a nuestra <em>directiva.</em></h2>' in church
    assert '<h2>DIRECTIVA <em>DEPEC</em></h2>' not in church
    assert 'testimonials-grid message-collage' in root
    assert 'Voces de nuestras <em>iglesias.</em>' in root


def test_featured_depec_events_and_decorative_fillers_are_scoped(client,app):
    from app.community_data import local_now
    future=local_now()+timedelta(days=5)
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute("DELETE FROM media_files WHERE record_id IN (SELECT id FROM records WHERE module='events')")
        db.execute("DELETE FROM participation")
        db.execute("DELETE FROM records WHERE module='events'")
        for gid in [1,3]:
            data=payload();data.update(title='Encuentro dorado' if gid==1 else 'Encuentro de iglesia',date=future.isoformat(timespec='minutes'),end_date=(future+timedelta(hours=2)).isoformat(timespec='minutes'),card_layout='Vertical')
            db.execute("INSERT INTO records(module,group_id,data,author_id,created,updated) VALUES('events',?,?,1,'2026-01-01','2026-01-01')",(gid,json.dumps(data)))
    from html.parser import HTMLParser
    class Tiles(HTMLParser):
        def __init__(self):super().__init__();self.tiles=[];self.fillers=[]
        def handle_starttag(self,tag,attrs):
            a=dict(attrs)
            if tag=='article' and 'data-placement' in a:self.tiles.append(a)
            if tag=='figure' and 'collage-filler' in a.get('class',''):self.fillers.append(a)
    root=Tiles();root.feed(client.get('/').get_data(as_text=True))
    assert len(root.tiles)==2 and len([t for t in root.tiles if 'depec-featured-event' in t['class']])==1
    assert root.fillers and all(f['aria-hidden']=='true' for f in root.fillers)
    assert all('--row4:' in tile['style'] and '--row2:' in tile['style'] and '--row1:' in tile['style'] for tile in root.tiles)
    church=Tiles();church.feed(client.get('/?group=3').get_data(as_text=True))
    assert len(church.tiles)==1 and 'depec-featured-event' not in church.tiles[0]['class']


def test_message_collage_preserves_church_and_moderation(client,app):
    with sqlite3.connect(app.config['DATABASE']) as db:
        uid=db.execute("SELECT id FROM users WHERE email='miembro-10@demo.depec.local'").fetchone()[0]
        for body,state in [('Saludo aprobado de Israel','Aprobado'),('Mensaje pendiente oculto','Pendiente')]:
            db.execute('INSERT INTO community_messages(user_id,group_id,body,status,created) VALUES(?,2,?,?,?)',(uid,body,state,'2026-01-01'))
    root=client.get('/').get_data(as_text=True)
    assert 'Saludo aprobado de Israel' in root and 'Mensaje pendiente oculto' not in root
    assert 'class="message-church">SEC Israel' in root and '--church:#' in root
    assert 'Saludo aprobado de Israel' not in client.get('/?group=3').get_data(as_text=True)
    assert 'Saludo aprobado de Israel' in client.get('/?group=2').get_data(as_text=True)

# v0.4.6 — agrandar imágenes y contacto público por organización.
def test_image_viewer_is_public_and_preserves_asset_permissions(client,app):
    root=client.get('/').get_data(as_text=True)
    assert '<dialog class="image-viewer"' in root and 'data-viewer-image' in root
    assert 'data-viewer-original' in root and 'data-viewer-zoom' in root
    assert 'viewer-contact.js' in root and 'viewer-contact.css' in root
    with sqlite3.connect(app.config['DATABASE']) as db:
        aid=db.execute('SELECT id FROM albums WHERE group_id=3 LIMIT 1').fetchone()[0]
    album=client.get(f'/album/{aid}').get_data(as_text=True)
    assert 'data-image-viewer' in album
    csrf=login(client)
    panel=client.get('/panel').get_data(as_text=True)
    assert '<dialog class="image-viewer"' not in panel
    response=client.post('/panel/contacto',data=dict(csrf=csrf,group_id=3,enabled='1',label='Habla con Jorge Chávez',title='Te escuchamos',whatsapp='+51 123 456 789',phone='+51 123 456 789',email='contacto@example.com',message='Ven a compartir',name='Directiva de prueba',hours='Sábados',whatsapp_message='Hola, ¿cuándo se reúnen?'))
    assert response.status_code==302
    page=client.get('/?group=3').get_data(as_text=True)
    assert 'Habla con Jorge Chávez' in page and 'https://wa.me/51123456789?' in page
    assert 'tel:+51123456789' in page and 'mailto:contacto@example.com' in page
    assert 'Ven a compartir' in page and 'Directiva de prueba' in page
    assert 'Habla con Jorge Chávez' not in client.get('/').get_data(as_text=True)
    assert 'Habla con Jorge Chávez' in client.get(f'/album/{aid}').get_data(as_text=True)
    assert 'Habla con Jorge Chávez' in client.get('/calendar?public=1&group=3').get_data(as_text=True)
    assert 'Habla con Jorge Chávez' in client.get('/cumpleanos?group=3').get_data(as_text=True)


def test_contact_config_scope_csrf_validation_and_visibility(client,app):
    assert client.get('/panel/contacto').status_code==302
    csrf=login(client,'israel@depec.demo')
    assert client.get('/panel/contacto?group=2').status_code==200
    assert client.get('/panel/contacto?group=3').status_code==403
    assert client.post('/panel/contacto',data=dict(csrf=csrf,group_id=3,enabled='1')).status_code==403
    assert client.post('/panel/contacto',data=dict(group_id=2,enabled='1')).status_code==400
    valid=dict(csrf=csrf,group_id=2,enabled='1',label='Escríbenos Israel',email='iglesia@example.com',message='<script>alert(1)</script>')
    assert client.post('/panel/contacto',data=valid).status_code==302
    with sqlite3.connect(app.config['DATABASE']) as db:before=db.execute('SELECT contact_settings FROM groups WHERE id=2').fetchone()[0]
    for bad in [dict(whatsapp='https://evil.example'),dict(phone='123'),dict(email='a@example.com\nBcc:x@example.com'),dict(label='a'*33)]:
        assert client.post('/panel/contacto',data={**valid,**bad}).status_code==200
        with sqlite3.connect(app.config['DATABASE']) as db:assert db.execute('SELECT contact_settings FROM groups WHERE id=2').fetchone()[0]==before
    page=client.get('/?group=2').get_data(as_text=True)
    assert 'Escríbenos Israel' in page and '<script>alert(1)</script>' not in page and '&lt;script&gt;' in page
    valid.pop('enabled')
    assert client.post('/panel/contacto',data=valid).status_code==302
    assert 'data-contact-bubble' not in client.get('/?group=2').get_data(as_text=True)
    assert 'data-contact-bubble' in client.get('/').get_data(as_text=True)


def test_contact_defaults_and_special_email_characters(client):
    from app.contact import validate_contact,public_contact
    group=dict(id=3,name='SEC Prueba',active=1,contact_settings='{}')
    assert public_contact(group)['group_name']=='SEC Prueba'
    assert public_contact(group)['whatsapp_url']==''
    group['contact_settings']=json.dumps(validate_contact(dict(enabled='1',email='name?test@example.com')))
    assert public_contact(group)['email_url']=='mailto:name%3Ftest@example.com'
    group['contact_settings']='invalid json'
    assert public_contact(group)['label']=='Contáctanos'
    group['active']=0
    assert public_contact(group) is None


def test_contact_migration_preserves_existing_organization_data(tmp_path):
    path=tmp_path/'without-contact.sqlite'
    schema=(Path(__file__).parents[1]/'app'/'schema.sql').read_text(encoding='utf-8').replace(",contact_settings TEXT NOT NULL DEFAULT '{}'",'')
    with sqlite3.connect(path) as db:
        db.executescript(schema)
        db.execute("INSERT INTO groups(id,name,kind,color,hero_title) VALUES(1,'DEPEC','DEPEC','#cc254b','Título conservado')")
    from app.community_data import upgrade_schema
    with sqlite3.connect(path) as db:
        upgrade_schema(db);upgrade_schema(db)
        assert db.execute('SELECT hero_title,contact_settings FROM groups').fetchone()==('Título conservado','{}')
        db.execute('UPDATE groups SET contact_settings=?',(json.dumps(dict(enabled=False)),));db.commit()
        upgrade_schema(db)
        assert json.loads(db.execute('SELECT contact_settings FROM groups').fetchone()[0])==dict(enabled=False)


def test_member_cannot_edit_contact_and_uses_own_church_bubble(client):
    csrf=login(client,'miembro-0@demo.depec.local')
    assert client.post('/panel/contacto',data=dict(csrf=csrf,group_id=3,enabled='1')).status_code==403
    assert 'data-contact-group="3"' in client.get('/mi-perfil').get_data(as_text=True)

# v0.4.7 — rellenos por orientación, historia en calendario y álbumes paginados.
def album_ids(html):
    from html.parser import HTMLParser
    class Albums(HTMLParser):
        def __init__(self):super().__init__();self.ids=[]
        def handle_starttag(self,tag,attrs):
            attrs=dict(attrs)
            if tag=='a' and 'data-album-id' in attrs:self.ids.append(int(attrs['data-album-id']))
    parser=Albums();parser.feed(html);return parser.ids


def test_fillers_use_compositions_for_their_actual_orientation():
    from app.collage import build_event_collage
    events=[dict(id=i,d=dict(orientation='portrait')) for i in range(5)]
    collage=build_event_collage(events)
    assert collage['fillers']
    for filler in collage['fillers']:
        if filler['rows']>filler['columns']:
            assert filler['orientation']=='portrait' and 'filler-portrait-' in filler['image']
        elif filler['rows']==filler['columns']:
            assert filler['orientation']=='square' and filler['image'].endswith('filler-square.svg')
        else:assert filler['orientation']=='landscape'
        assert (Path(__file__).parents[1]/'app'/'static'/filler['image']).exists()


def test_home_excludes_completed_events_but_past_calendar_retains_them(client,app):
    with sqlite3.connect(app.config['DATABASE']) as db:
        data=payload();data.update(title='Encuentro histórico conservado',date='2020-05-10T16:00',end_date='2020-05-10T19:00',status='Programado')
        rid=db.execute("INSERT INTO records(module,group_id,data,author_id,created,updated) VALUES('events',3,?,1,'2020-05-01','2020-05-01')",(json.dumps(data),)).lastrowid
    for path in ['/','/?group=3']:
        page=client.get(path).get_data(as_text=True)
        assert 'Encuentro histórico conservado' not in page
        assert 'Ya compartimos estos momentos' not in page and 'class="past-events"' not in page
    page=client.get(f'/calendar?public=1&group=3&month=2020-05-01&event={rid}').get_data(as_text=True)
    assert 'Encuentro histórico conservado' in page and 'Finalizado' in page
    with sqlite3.connect(app.config['DATABASE']) as db:assert json.loads(db.execute('SELECT data FROM records WHERE id=?',(rid,)).fetchone()[0])['status']=='Finalizado'


def test_album_home_limit_directory_pagination_search_and_scope(client,app):
    ids=[]
    with sqlite3.connect(app.config['DATABASE']) as db:
        for i in range(18):
            ids.append(db.execute("INSERT INTO albums(group_id,title,description,created_by,created) VALUES(3,?,'Recuerdos de la comunidad',1,'2026-01-01')",(f'CAFÉ JÓVENES {i:02}',)).lastrowid)
        secret=db.execute("INSERT INTO albums(group_id,title,visibility,created_by,created) VALUES(3,'Álbum interno oculto','internal',1,'2026-01-01')").lastrowid
    home=client.get('/?group=3').get_data(as_text=True)
    assert album_ids(home)==list(reversed(ids[-3:])) and 'Ver todos los álbumes' in home
    first=client.get('/albumes?group=3&q=cafe+jovenes').get_data(as_text=True)
    second=client.get('/albumes?group=3&q=cafe+jovenes&page=2').get_data(as_text=True)
    assert len(album_ids(first))==12 and len(album_ids(second))==6
    assert set(album_ids(first)+album_ids(second))==set(ids)
    assert 'Álbum interno oculto' not in first and secret not in album_ids(first)
    assert 'data-contact-group="3"' in first and 'data-image-viewer' in first
    assert not album_ids(client.get('/albumes?group=1&q=cafe+jovenes').get_data(as_text=True))
    assert not album_ids(client.get('/albumes?group=3&q=%25').get_data(as_text=True))
    assert client.get('/albumes?group=999').status_code==404
    for suffix in ['page=0','page=abc','q='+'a'*121]:assert client.get('/albumes?group=3&'+suffix).status_code==400
    assert client.get('/albumes?group=3&page=999').status_code==404


def test_album_cards_count_only_images_publicly_visible(client,app):
    with sqlite3.connect(app.config['DATABASE']) as db:
        aid=db.execute("INSERT INTO albums(group_id,title,created_by,created) VALUES(3,'Álbum con permisos',1,'2026-01-01')").lastrowid
        visible=db.execute("INSERT INTO media_files(group_id,album_id,title,kind,static_name,width,height,uploaded_by,visibility,created) VALUES(3,?,'Imagen pública','Fotografía','demo/amistad.png',1536,1024,1,'public','2026-01-01')",(aid,)).lastrowid
        hidden=db.execute("INSERT INTO media_files(group_id,album_id,title,kind,static_name,width,height,uploaded_by,visibility,created) VALUES(3,?,'Imagen privada','Fotografía','demo/servicio.png',1536,1024,1,'internal','2026-01-02')",(aid,)).lastrowid
        draft=db.execute("INSERT INTO records(module,group_id,data,author_id,created,updated) VALUES('gallery',3,?,1,'2026-01-01','2026-01-01')",(json.dumps(dict(title='Borrador',visibility='public',status='Borrador')),)).lastrowid
        db.execute("INSERT INTO media_files(group_id,album_id,record_id,title,kind,static_name,width,height,uploaded_by,visibility,created) VALUES(3,?,?,'Foto en borrador','Fotografía','demo/amistad.png',1536,1024,1,'public','2026-01-03')",(aid,draft))
    page=client.get('/albumes?group=3&q=permisos').get_data(as_text=True)
    assert '1 fotografía' in page and f'/archivos/{visible}' in page and f'/archivos/{hidden}' not in page
    csrf=login(client)
    page=client.get('/albumes?group=3&q=permisos').get_data(as_text=True)
    assert '1 fotografía' in page and 'Imagen privada' not in page
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute('UPDATE records SET data=? WHERE id=?',(json.dumps(dict(title='Ahora publicada',visibility='public',status='Publicado')),draft))
    assert '2 fotografías' in client.get('/albumes?group=3&q=permisos').get_data(as_text=True)


def test_depec_leaders_manage_palette_and_church_cannot_change_it(client,app):
    csrf=login(client,'presidencia@depec.demo')
    assert client.get('/panel/colores').status_code==200
    assert client.post('/panel/colores',data=dict(csrf=csrf,group_id=3,color='#7a35b4')).status_code==302
    with sqlite3.connect(app.config['DATABASE']) as db:
        assert db.execute('SELECT color FROM groups WHERE id=3').fetchone()[0]=='#7a35b4'
        assert db.execute('SELECT color FROM groups WHERE id=1').fetchone()[0]=='#cc254b'
    assert '--brand:#7a35b4' in client.get('/?group=3').get_data(as_text=True)
    assert client.post('/panel/colores',data=dict(csrf=csrf,group_id=3,color='red')).status_code==200
    with sqlite3.connect(app.config['DATABASE']) as db:assert db.execute('SELECT color FROM groups WHERE id=3').fetchone()[0]=='#7a35b4'
    other=app.test_client();csrf2=login(other,'israel@depec.demo')
    assert other.get('/panel/colores').status_code==403
    assert other.post('/panel/colores',data=dict(csrf=csrf2,group_id=2,color='#ffffff')).status_code==403
    with sqlite3.connect(app.config['DATABASE']) as db:before=db.execute('SELECT color FROM groups WHERE id=2').fetchone()[0]
    assert other.post('/panel/identidad',data=dict(csrf=csrf2,group_id=2,color='#ffffff',hero_title='Nuestra identidad',verse_mode='daily')).status_code==302
    with sqlite3.connect(app.config['DATABASE']) as db:assert db.execute('SELECT color FROM groups WHERE id=2').fetchone()[0]==before
    assert client.post('/panel/colores',data=dict(group_id=3,color='#ffffff')).status_code==400

# v0.5.0 — laboratorio global con permisos reales por identidad.
def test_global_tester_switches_roles_without_leaking_admin_access(client,app):
    response=client.post('/login',data=dict(csrf=token(client),email='pruebas@depec.demo',password='DepecPruebas2026!'))
    assert response.status_code==302
    assert 'data-role-lab' in client.get('/panel').get_data(as_text=True)
    def switch(role,gid):
        with client.session_transaction() as s:csrf=s['csrf']
        result=client.post('/pruebas/cambiar-rol',data=dict(csrf=csrf,role=role,group_id=gid))
        assert result.status_code==302
        return result
    switch('Secretario',3)
    assert client.get('/manage/members/new?group=3').status_code==200
    assert client.get('/manage/finance/new?group=3').status_code==403
    foreign=record(app,'members',2)
    assert client.get(f'/manage/members/{foreign}/edit').status_code==403
    assert 'data-role-lab' in client.get('/manage/finance/new').get_data(as_text=True)
    assert client.get('/panel/colores').status_code==403
    with client.session_transaction() as s:
        secretary=s['uid'];operator=s['test_operator']
        assert secretary!=operator
    with sqlite3.connect(app.config['DATABASE']) as db:assert db.execute('SELECT admin FROM users WHERE id=?',(secretary,)).fetchone()[0]==0
    switch('Tesorero',3)
    assert client.get('/manage/finance/new?group=3').status_code==200
    assert client.get('/manage/members/new?group=3').status_code==403
    switch('Vocal',3)
    assert client.get('/manage/events/new?group=3').status_code==403
    switch('Presidente',3)
    assert client.get('/manage/finance/new?group=3').status_code==200
    assert client.get(f'/manage/members/{foreign}/edit').status_code==403
    switch('Presidente',1)
    assert client.get(f'/manage/members/{foreign}/edit').status_code==200
    assert client.get('/panel/colores').status_code==200
    switch('Administrador',1)
    with client.session_transaction() as s:assert s['uid']==operator
    assert client.get('/manage/finance/new').status_code==200


def test_tester_member_and_visitor_can_always_return_to_admin(client,app):
    client.post('/login',data=dict(csrf=token(client),email='pruebas@depec.demo',password='DepecPruebas2026!'))
    def switch(role,gid):
        with client.session_transaction() as s:csrf=s['csrf']
        return client.post('/pruebas/cambiar-rol',data=dict(csrf=csrf,role=role,group_id=gid))
    assert switch('Miembro',3).status_code==302
    assert client.get('/mi-comunidad').status_code==200
    assert client.get('/mi-perfil').status_code==200
    assert client.get('/manage/finance').status_code==403
    assert 'data-role-lab' in client.get('/manage/finance').get_data(as_text=True)
    assert switch('Visitante',3).status_code==302
    with client.session_transaction() as s:assert s['uid'] is None and s['test_operator']
    page=client.get('/?group=3').get_data(as_text=True)
    assert 'data-role-lab' in page
    assert client.get('/manage/members').status_code==302
    assert client.get('/albumes?group=3').headers['Cache-Control']=='no-store'
    assert switch('Administrador',1).status_code==302
    assert client.get('/manage/finance/new').status_code==200
    with client.session_transaction() as s:csrf=s['csrf']
    client.post('/logout',data=dict(csrf=csrf))
    assert 'data-role-lab' not in client.get('/').get_data(as_text=True)
    assert client.post('/pruebas/cambiar-rol',data=dict(csrf=token(client),role='Administrador',group_id=1)).status_code==403


def test_test_switcher_is_not_available_to_normal_accounts_and_validates_requests(client,app):
    csrf=login(client)
    assert 'data-role-lab' not in client.get('/panel').get_data(as_text=True)
    assert client.post('/pruebas/cambiar-rol',data=dict(csrf=csrf,role='Administrador',group_id=1)).status_code==403
    client.post('/login',data=dict(csrf=csrf,email='pruebas@depec.demo',password='DepecPruebas2026!'))
    with client.session_transaction() as s:csrf=s['csrf'];operator=s['uid']
    assert client.post('/pruebas/cambiar-rol',data=dict(role='Presidente',group_id=3)).status_code==400
    for role,gid in [('Inventado',3),('Presidente',999)]:
        assert client.post('/pruebas/cambiar-rol',data=dict(csrf=csrf,role=role,group_id=gid)).status_code==400
    assert client.post('/pruebas/cambiar-rol',data=dict(csrf=csrf,role='Miembro',group_id=1)).status_code==302
    with client.session_transaction() as s:assert s['uid']==operator
    assert client.post('/pruebas/cambiar-rol',data=dict(csrf=csrf,role='Secretario',group_id=3)).status_code==302
    assert client.post('/pruebas/cambiar-rol',data=dict(csrf=csrf,role='Administrador',group_id=1)).status_code==400


def test_test_personas_are_reused_and_operator_deactivation_ends_authority(client,app):
    client.post('/login',data=dict(csrf=token(client),email='pruebas@depec.demo',password='DepecPruebas2026!'))
    ids=[]
    for role in ['Secretario','Tesorero','Secretario']:
        with client.session_transaction() as s:csrf=s['csrf'];operator=s['test_operator']
        assert client.post('/pruebas/cambiar-rol',data=dict(csrf=csrf,role=role,group_id=3)).status_code==302
        with client.session_transaction() as s:ids.append(s['uid'])
    assert ids[0]==ids[2] and ids[0]!=ids[1]
    with sqlite3.connect(app.config['DATABASE']) as db:
        assert db.execute('SELECT count(*) FROM assignments WHERE user_id=? AND active=1',(ids[0],)).fetchone()[0]==1
        db.execute('UPDATE users SET active=0 WHERE id=?',(operator,))
    assert client.get('/manage/members').status_code==302
    assert 'data-role-lab' not in client.get('/').get_data(as_text=True)
    with client.session_transaction() as s:assert 'test_operator' not in s


def test_test_account_is_not_created_implicitly_on_real_install(tmp_path):
    from app.role_lab import create_test_operator
    path=tmp_path/'real.sqlite'
    with sqlite3.connect(path) as db:
        db.executescript((Path(__file__).parents[1]/'app'/'schema.sql').read_text(encoding='utf-8'))
        db.execute("INSERT INTO users(name,email,password) VALUES('Cuenta real','pruebas@depec.demo','hash-conservado')")
        db.commit()
        assert create_test_operator(db,demo_only=True) is False
        assert create_test_operator(db) is False
        assert db.execute('SELECT admin,password FROM users').fetchone()==(0,'hash-conservado')
        assert db.execute('SELECT count(*) FROM test_operators').fetchone()[0]==0


def test_event_defaults_follow_effective_organization(client,app):
    login(client,'israel@depec.demo')
    page=client.get('/manage/events/new').get_data(as_text=True)
    from html.parser import HTMLParser
    class Selected(HTMLParser):
        def __init__(self):super().__init__();self.select='';self.values={}
        def handle_starttag(self,tag,attrs):
            attrs=dict(attrs)
            if tag=='select':self.select=attrs.get('name','')
            if tag=='option' and 'selected' in attrs:self.values[self.select]=attrs.get('value')
    selected=Selected();selected.feed(page)
    assert selected.values['group_id']=='2'
    selected=Selected();selected.feed(client.get('/manage/events').get_data(as_text=True))
    assert selected.values['group']=='2'
    with client.session_transaction() as s:csrf=s['csrf']
    client.post('/login',data=dict(csrf=csrf,email='presidencia@depec.demo',password='DepecDemo2026!'))
    selected=Selected();selected.feed(client.get('/manage/events/new').get_data(as_text=True));assert selected.values['group_id']=='1'
    assert 'name="capacity"' not in page and 'name="media_kind"' not in page and 'name="event_address"' not in page
    assert 'format-switch' in page and 'data-venue-picker' in page and 'event-editor-grid' in page


def test_pending_event_without_dates_and_church_venue(client,app):
    csrf=login(client)
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute("UPDATE groups SET address='Calle de prueba 123',maps_url='https://maps.app.goo.gl/local' WHERE id=3")
    data=payload();data.update(csrf=csrf,group_id='1',status='Por programar',date='',end_date='',location='Ignorado',venue_group='3',event_address='No usar dirección anterior')
    assert client.post('/manage/events/new',data=data).status_code==302
    with sqlite3.connect(app.config['DATABASE']) as db:
        rid,raw=db.execute("SELECT id,data FROM records WHERE module='events' ORDER BY id DESC LIMIT 1").fetchone();stored=json.loads(raw)
    assert stored['location']==stored['event_address']=='Calle de prueba 123' and 'capacity' not in stored
    assert stored['location_maps_url']=='https://maps.app.goo.gl/local'
    page=client.get(f'/events/{rid}/preview').get_data(as_text=True)
    assert 'Por programar' in page and 'Fecha y hora por confirmar' in page and 'maps.app.goo.gl/local' in page
    data.update(status='Programado')
    assert client.post('/manage/events/new',data=data).status_code==200
    assert client.get(f'/events/{rid}/preview').status_code==200
    other=app.test_client();login(other,'israel@depec.demo')
    assert other.get(f'/events/{rid}/preview').status_code==200  # Church leaders can consult public DEPEC events.
    assert client.get('/manage/events?group=1&status=Por+programar').status_code==200


def test_event_audience_controls_and_church_boundaries(client,app):
    csrf=login(client,'israel@depec.demo')
    page=client.get('/manage/events/new').get_data(as_text=True)
    assert 'El local de tu iglesia se completa por defecto.' not in page
    assert 'field-help' in page and 'Iglesias invitadas' in page
    right=page.split('class="preview-controls"')[1]
    for name in ['image_mode','generic_image','attachment','card_layout']:
        assert f'name="{name}"' in right.split('id="event-preview-title"')[0]
    # Even a manually granted foreign permission cannot change church ownership.
    with client.session_transaction() as session:uid=session['uid']
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute("INSERT INTO grants(user_id,group_id,module,can_write,active) VALUES(?,3,'events',1,1)",(uid,))
    data=payload();data.update(csrf=csrf,group_id='3')
    assert client.post('/manage/events/new',data=data).status_code==403
    assert client.get('/manage/events?group=3').status_code==403
    assert client.get('/manage/events?group=1').status_code==200
    assert client.get('/manage/finance?group=1').status_code==403


def test_event_audience_distribution_and_private_invites(client,app):
    csrf=login(client)
    ids={}
    for audience in ['Toda la DEPEC','Público de mi iglesia','Iglesias invitadas','Solo líderes de mi organización']:
        data=payload();data.pop('visibility');data.update(csrf=csrf,group_id='1' if audience.startswith('Solo') else '3',title=audience,audience=audience,invited_groups='2')
        assert client.post('/manage/events/new',data=data).status_code==302
        with sqlite3.connect(app.config['DATABASE']) as db:
            rid,raw=db.execute("SELECT id,data FROM records WHERE module='events' ORDER BY id DESC LIMIT 1").fetchone()
            ids[audience]=rid
            assert json.loads(raw)['visibility']==('internal' if audience in ['Iglesias invitadas','Solo líderes de mi organización'] else 'public')
    anonymous=app.test_client()
    public=anonymous.get('/calendar?public=1&group=2').get_data(as_text=True)
    assert 'Toda la DEPEC' in public and 'Público de mi iglesia' not in public and 'Iglesias invitadas' not in public
    owner=anonymous.get('/calendar?public=1&group=3').get_data(as_text=True)
    assert 'Público de mi iglesia' in owner
    israel=app.test_client();login(israel,'israel@depec.demo')
    invited=israel.get('/calendar?public=1&group=2').get_data(as_text=True)
    assert 'Iglesias invitadas' in invited
    assert israel.get(f"/events/{ids['Solo líderes de mi organización']}/preview").status_code==403
    # Enforcing invitations does not depend on hiding a field in the browser.
    data=payload();data.pop('visibility');data.update(csrf=csrf,audience='Iglesias invitadas')
    assert client.post('/manage/events/new',data=data).status_code==200


def test_private_invited_event_media_requires_approved_recipient(client,app):
    csrf=login(client)
    data=payload();data.pop('visibility');data.update(csrf=csrf,group_id='3',title='Adjunto reservado de invitación',audience='Iglesias invitadas',invited_groups='2',image_mode='Imagen propia',attachment=image_upload())
    assert client.post('/manage/events/new',data=data).status_code==302
    with sqlite3.connect(app.config['DATABASE']) as db:
        rid=db.execute("SELECT max(id) FROM records WHERE module='events'").fetchone()[0]
        mid=db.execute('SELECT id FROM media_files WHERE record_id=?',(rid,)).fetchone()[0]
    anonymous=app.test_client()
    assert anonymous.get(f'/media/{rid}').status_code==403
    assert anonymous.get(f'/archivos/{mid}').status_code==403
    invited=app.test_client();login(invited,'israel@depec.demo')
    assert invited.get(f'/media/{rid}').status_code==200
    assert invited.get(f'/archivos/{mid}').status_code==200
    # A member needs approval, and must belong to an invited organization.
    with sqlite3.connect(app.config['DATABASE']) as db:
        uid=db.execute("SELECT id FROM users WHERE email='israel@depec.demo'").fetchone()[0]
        db.execute('UPDATE assignments SET active=0 WHERE user_id=?',(uid,))
        db.execute("INSERT INTO memberships(user_id,group_id,status,created) VALUES(?,2,'Pendiente','2026-01-01')",(uid,))
    assert invited.get(f'/archivos/{mid}').status_code==403
    with sqlite3.connect(app.config['DATABASE']) as db:db.execute("UPDATE memberships SET status='Aprobado' WHERE user_id=?",(uid,))
    assert invited.get(f'/archivos/{mid}').status_code==200
    with sqlite3.connect(app.config['DATABASE']) as db:db.execute('UPDATE memberships SET group_id=4 WHERE user_id=?',(uid,))
    assert invited.get(f'/media/{rid}').status_code==403


def test_church_media_panel_does_not_list_depec_private_albums(client,app):
    csrf=login(client);create_album(client,csrf,1,'Álbum privado exclusivo DEPEC','internal')
    login(client,'israel@depec.demo')
    page=client.get('/panel/archivos').get_data(as_text=True)
    assert 'Álbum privado exclusivo DEPEC' not in page
