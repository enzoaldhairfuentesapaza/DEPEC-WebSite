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
    con.executescript((Path(__file__).parents[1]/'app'/'schema.sql').read_text())
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
        if module=='gallery':
            assert client.get('/manage/gallery').status_code==200
            assert client.get('/manage/gallery/new').status_code==200
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
    png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Zl1sAAAAASUVORK5CYII=')
    csrf=login(client)
    data=dict(csrf=csrf,group_id=2,title='Recuerdo público',body='Galería de prueba',date=date.today().isoformat(),visibility='public',status='Publicado',attachment=(io.BytesIO(png),'foto.png'))
    assert client.post('/manage/gallery/new',data=data).status_code==302
    with sqlite3.connect(app.config['DATABASE']) as db:
        rid=db.execute('SELECT max(id) FROM records').fetchone()[0]
    client.post('/logout',data={'csrf':csrf})
    assert 'Recuerdo público' in client.get('/').get_data(as_text=True)
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
