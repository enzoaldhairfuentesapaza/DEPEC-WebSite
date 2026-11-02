import io,json,sqlite3
from datetime import date
from zipfile import ZipFile
from openpyxl import load_workbook
from test_system import app,client,login,token,record

PDF=b'%PDF-1.4\n1 0 obj <<>> endobj\n%%EOF'
def file():return io.BytesIO(PDF),'documento.pdf'
def latest(app,table):
    with sqlite3.connect(app.config['DATABASE']) as con:return con.execute('SELECT max(id) FROM '+table).fetchone()[0]

def meeting_data(csrf,**more):return dict(csrf=csrf,title='Reunión de coordinación',kind='Ordinaria',audience='Iglesias',starts='2026-11-20T17:00',plan_year='2026',location='Israel',agenda='Revisar planes',invited=['2','3'],**more)

def test_new_office_pages_and_builtin_exports(client):
    login(client)
    for path in ['/secretaria','/secretaria/reuniones','/secretaria/planes','/secretaria/recepcion-planes','/secretaria/correspondencia','/secretaria/plantillas','/tesoreria','/tesoreria/movimientos/nuevo','/tesoreria/organizar','/tesoreria/deudas']:
        assert client.get(path).status_code==200,path
    for kind in ['acta','credencial','carta','plan']:
        response=client.get('/secretaria/plantillas/base/'+kind);assert response.status_code==200
        assert 'word/document.xml' in ZipFile(io.BytesIO(response.data)).namelist()
    response=client.get('/tesoreria/reporte.xlsx');assert response.status_code==200
    assert load_workbook(io.BytesIO(response.data)).sheetnames==['Resumen','Movimientos','Mensual','Por categoría','Por proyecto','Deudas']


def test_joint_meeting_acta_credential_copy_and_isolation(client,app):
    csrf=login(client,'presidencia@depec.demo')
    assert client.post('/secretaria/reuniones',data=meeting_data(csrf)).status_code==302
    mid=latest(app,'office_meetings')
    assert client.post(f'/secretaria/reuniones/{mid}',data=dict(csrf=csrf,action='minutes',summary='Acuerdos de DEPEC',status='Firmada',attachment=file())).status_code==302
    with sqlite3.connect(app.config['DATABASE']) as db:acta_file=db.execute("SELECT id FROM office_files WHERE resource='minutes'").fetchone()[0]
    israel=app.test_client();icsrf=login(israel,'israel@depec.demo')
    page=israel.get(f'/secretaria/reuniones/{mid}').get_data(as_text=True)
    assert 'Credencial de SEC Israel' in page and 'Acuerdos de DEPEC' not in page
    assert israel.get(f'/secretaria/archivo/{acta_file}').status_code==403
    assert israel.post(f'/secretaria/reuniones/{mid}',data=dict(csrf=icsrf,action='minutes',summary='Intrusión',status='Firmada')).status_code==403
    assert israel.post(f'/secretaria/reuniones/{mid}',data=dict(csrf=icsrf,action='credential',attendees='Ana · Secretaria',attachment=file())).status_code==302
    cid=latest(app,'office_credentials');fid=latest(app,'office_files')
    assert client.get(f'/secretaria/archivo/{fid}').data==israel.get(f'/secretaria/archivo/{fid}').data
    assert client.post(f'/secretaria/reuniones/{mid}',data=dict(csrf=csrf,action='review_credential',credential_id=cid,status='Observada',review_note='Falta firma')).status_code==302
    assert 'Falta firma' in israel.get(f'/secretaria/reuniones/{mid}').get_data(as_text=True)
    outsider=app.test_client();client.post('/secretaria/reuniones',data=dict(meeting_data(csrf),title='Solo DEPEC',audience='Interna'))
    private=latest(app,'office_meetings')
    assert israel.get(f'/secretaria/reuniones/{private}').status_code==403
    assert outsider.get(f'/secretaria/archivo/{fid}').status_code==302


def test_plan_window_and_frozen_delivery_copy(client,app):
    csrf=login(client,'presidencia@depec.demo')
    assert client.post('/secretaria/recepcion-planes',data=dict(csrf=csrf,action='campaign',year=2027,deadline='2027-12-31T23:59',active='1')).status_code==302
    israel=app.test_client();icsrf=login(israel,'israel@depec.demo')
    assert israel.post('/secretaria/planes',data=dict(csrf=icsrf,action='save_plan',year=2027,title='Plan Israel',attachment=file())).status_code==302
    own_file=latest(app,'office_files')
    assert client.get(f'/secretaria/archivo/{own_file}').status_code==403
    assert israel.post('/secretaria/planes',data=dict(csrf=icsrf,action='send_plan',year=2027)).status_code==302
    assert client.get(f'/secretaria/archivo/{own_file}').status_code==200
    assert israel.post('/secretaria/planes',data=dict(csrf=icsrf,action='save_plan',year=2027,title='Revisión sin enviar',attachment=file())).status_code==302
    revision=latest(app,'office_files');assert client.get(f'/secretaria/archivo/{revision}').status_code==403
    assert client.get(f'/secretaria/archivo/{own_file}').status_code==200
    client.post('/secretaria/recepcion-planes',data=dict(csrf=csrf,action='campaign',year=2027,deadline='2027-12-31T23:59'))
    response=israel.post('/secretaria/planes',data=dict(csrf=icsrf,action='send_plan',year=2027));assert response.status_code==200
    with sqlite3.connect(app.config['DATABASE']) as db:assert db.execute('SELECT count(*) FROM office_plan_deliveries').fetchone()[0]==1


def test_ledger_exact_amounts_reports_and_debt_payments(client,app):
    csrf=login(client,'israel@depec.demo')
    assert client.post('/tesoreria/organizar',data=dict(csrf=csrf,action='project',name='Campamento')).status_code==302
    pid=latest(app,'finance_projects')
    for kind,amount,description in [('Ingreso','100.10','=IMPORTAR()'),('Egreso','20.03','Música')]:
        assert client.post('/tesoreria/movimientos/nuevo',data=dict(csrf=csrf,kind=kind,amount=amount,description=description,date='2027-01-05',project_id=pid,subcategory='Música')).status_code==302
    response=client.get('/tesoreria/reporte.xlsx?year=2027&project='+str(pid));wb=load_workbook(io.BytesIO(response.data));summary={r[0].value:r[1].value for r in wb['Resumen'].iter_rows(min_row=4)}
    assert summary['Ingresos del filtro']==100.10 and summary['Egresos del filtro']==20.03 and summary['Resultado del filtro']==80.07
    cell=wb['Movimientos']['D4'];assert cell.value=='=IMPORTAR()' and cell.data_type=='s'
    assert client.post('/tesoreria/deudas',data=dict(csrf=csrf,kind='Por cobrar',counterparty='Persona de prueba',description='Préstamo',amount='40.00',date='2027-01-01',project_id=pid)).status_code==302
    did=latest(app,'finance_debts');payment=dict(csrf=csrf,amount='10.05',date='2027-01-10',token='token_para_pago_unico_de_prueba')
    assert client.post(f'/tesoreria/deudas/{did}',data=payment).status_code==302
    assert client.post(f'/tesoreria/deudas/{did}',data=payment).status_code==200
    assert '29.95' in client.get(f'/tesoreria/deudas/{did}').get_data(as_text=True)
    assert client.post(f'/tesoreria/deudas/{did}',data=dict(csrf=csrf,amount='30',date='2027-01-10')).status_code==200
    with sqlite3.connect(app.config['DATABASE']) as db:rid=db.execute('SELECT record_id FROM finance_settlements WHERE debt_id=?',(did,)).fetchone()[0]
    assert client.post(f'/tesoreria/movimientos/{rid}/anular',data=dict(csrf=csrf)).status_code==302
    assert '40.00' in client.get(f'/tesoreria/deudas/{did}').get_data(as_text=True)


def test_office_permissions_do_not_inherit_other_church_secrets(client,app):
    israel=app.test_client();icsrf=login(israel,'israel@depec.demo')
    data=dict(meeting_data(icsrf),audience='Interna')
    assert israel.post('/secretaria/reuniones',data=data).status_code==302
    mid=latest(app,'office_meetings')
    assert israel.post(f'/secretaria/reuniones/{mid}',data=dict(csrf=icsrf,action='minutes',status='Registrada',summary='Privado Israel',attachment=file())).status_code==302
    fid=latest(app,'office_files')
    csrf=login(client,'presidencia@depec.demo')
    assert client.get(f'/secretaria/reuniones/{mid}').status_code==403
    assert client.get(f'/secretaria/archivo/{fid}').status_code==403
    assert client.get(f'/secretaria/reuniones/{mid}/acta.docx').status_code==403
    assert client.get('/manage/finance?group=2').status_code==403
    assert client.get(f'/manage/documents/{record(app,"documents",2)}/edit').status_code==403
    # Vocal consulta su archivo, pero no puede escribir ni acceder a caja.
    vocal=app.test_client();vcsrf=login(vocal,'vocal@depec.demo')
    assert vocal.get(f'/secretaria/reuniones/{mid}').status_code==200
    assert vocal.post(f'/secretaria/reuniones/{mid}',data=dict(csrf=vcsrf,action='minutes',summary='No autorizado',status='Registrada')).status_code==403
    assert vocal.get('/tesoreria').status_code==403


def test_correspondence_link_and_custom_templates(client,app):
    csrf=login(client,'presidencia@depec.demo')
    assert client.post('/secretaria/reuniones',data=dict(meeting_data(csrf),audience='Interna')).status_code==302
    mid=latest(app,'office_meetings')
    assert client.post('/secretaria/correspondencia',data=dict(csrf=csrf,direction='Recibida',day='2026-10-31',subject='Carta confidencial DEPEC',counterparty='Remitente',meeting_id=mid,attachment=file())).status_code==302
    fid=latest(app,'office_files')
    assert 'Carta confidencial DEPEC' in client.get(f'/secretaria/reuniones/{mid}').get_data(as_text=True)
    israel=app.test_client();icsrf=login(israel,'israel@depec.demo')
    assert israel.get(f'/secretaria/archivo/{fid}').status_code==403
    assert israel.post('/secretaria/correspondencia',data=dict(csrf=icsrf,direction='Enviada',day='2026-10-31',subject='No vincular',counterparty='DEPEC',meeting_id=mid,attachment=file())).status_code==403
    assert client.post('/secretaria/plantillas',data=dict(csrf=csrf,title='Modelo oficial prueba',kind='Carta',attachment=file())).status_code==302
    tid=latest(app,'office_files')
    assert israel.get(f'/secretaria/archivo/{tid}').status_code==200
    assert israel.post('/secretaria/plantillas',data=dict(csrf=icsrf,title='No autorizado',kind='Carta',attachment=file())).status_code==403


def test_invalid_credential_rolls_back_without_orphan_upload(client,app):
    csrf=login(client,'presidencia@depec.demo');client.post('/secretaria/reuniones',data=meeting_data(csrf));mid=latest(app,'office_meetings')
    israel=app.test_client();icsrf=login(israel,'israel@depec.demo')
    response=israel.post(f'/secretaria/reuniones/{mid}',data=dict(csrf=icsrf,action='credential',attendees='Nombre',attachment=(io.BytesIO(b'no es un PDF'),'invalido.pdf')))
    assert response.status_code==200
    with sqlite3.connect(app.config['DATABASE']) as db:
        assert db.execute('SELECT count(*) FROM office_credentials').fetchone()[0]==0
        assert db.execute('SELECT count(*) FROM office_files').fetchone()[0]==0
    assert not list(__import__('pathlib').Path(app.config['UPLOAD_FOLDER']).glob('office_*'))


def test_report_month_opening_and_foreign_project_protection(client,app):
    csrf=login(client,'israel@depec.demo')
    for day,kind,amount,state in [('2027-01-01','Ingreso','10.10','Aprobado'),('2027-02-01','Egreso','2.03','Aprobado'),('2027-02-02','Ingreso','100.00','Pendiente')]:
        assert client.post('/tesoreria/movimientos/nuevo',data=dict(csrf=csrf,kind=kind,amount=amount,description='Detalle',date=day,status=state)).status_code==302
    response=client.get('/tesoreria/reporte.xlsx?year=2027&month=2');wb=load_workbook(io.BytesIO(response.data));values={r[0].value:r[1].value for r in wb['Resumen'].iter_rows(min_row=4)}
    assert values['Saldo de caja previo al periodo (organización completa)']>=10.10
    assert values['Egresos del filtro']==2.03 and values['Ingresos del filtro']==0
    assert round(values['Saldo de caja previo al periodo (organización completa)']-values['Saldo de caja al cierre (organización completa)'],2)==2.03
    depec=app.test_client();dcsrf=login(depec,'presidencia@depec.demo');depec.post('/tesoreria/organizar',data=dict(csrf=dcsrf,action='project',name='Solo DEPEC'));pid=latest(app,'finance_projects')
    assert client.get('/tesoreria/reporte.xlsx?project='+str(pid)).status_code==403
    assert client.post('/tesoreria/movimientos/nuevo',data=dict(csrf=csrf,kind='Ingreso',amount='5',description='No autorizado',date='2027-01-01',project_id=pid)).status_code==403


def test_duplicate_movement_token_and_csrf(client,app):
    csrf=login(client,'israel@depec.demo');data=dict(csrf=csrf,kind='Ingreso',amount='5.55',description='Una vez',date='2027-01-01',token='token_financiero_para_un_solo_envio')
    assert client.post('/tesoreria/movimientos/nuevo',data=data).status_code==302
    assert client.post('/tesoreria/movimientos/nuevo',data=data).status_code==200
    with sqlite3.connect(app.config['DATABASE']) as db:assert len([r for r in db.execute("SELECT data FROM records WHERE module='finance'") if json.loads(r[0]).get('body')=='Una vez'])==1
    data.pop('csrf');assert client.post('/tesoreria/movimientos/nuevo',data=data).status_code==400
