"""Planes anuales, reuniones, libro de actas, correspondencia y recepción."""
import io,sqlite3
from flask import Blueprint,abort,g,request,redirect,render_template,url_for,send_file
from .community_data import local_now


def register_secretariat(app,o):
    bp=Blueprint('secretariat',__name__,url_prefix='/secretaria')
    logged=o.logged;db=o.db

    def page(template,**data):
        org=o.organization();o.require(org['id'])
        return render_template('office/'+template,org=org,current_scope=org['id'],brand_group=org,module='documents',office=o,office_write=o.can(org['id'],write=True),**data)

    def access_meeting(mid):
        meeting=o.row('office_meetings',mid);org=o.organization();own=meeting['group_id']==org['id']
        invited=db().execute('SELECT 1 FROM office_invites WHERE meeting_id=? AND group_id=?',(mid,org['id'])).fetchone()
        if not own and not invited:abort(403)
        o.require(org['id']);return meeting,org,own

    @bp.get('')
    @logged
    def index():
        org=o.organization();o.require(org['id'])
        meetings=db().execute('SELECT m.*,a.status minutes_status FROM office_meetings m LEFT JOIN office_minutes a ON a.meeting_id=m.id WHERE m.group_id=? ORDER BY m.starts DESC',(org['id'],)).fetchall()
        invitations=db().execute("SELECT m.*,c.status credential_status FROM office_invites i JOIN office_meetings m ON m.id=i.meeting_id LEFT JOIN office_credentials c ON c.meeting_id=m.id AND c.group_id=i.group_id WHERE i.group_id=? ORDER BY m.starts DESC",(org['id'],)).fetchall()
        return page('secretary_home.html',meetings=meetings,invitations=invitations,year=local_now().year)

    @bp.route('/reuniones',methods=['GET','POST'])
    @logged
    def meetings():
        org=o.organization();o.require(org['id'])
        if request.method=='POST':
            o.require(org['id'],write=True)
            try:
                kind=o.text('kind');audience=o.text('audience')
                if kind not in ['Ordinaria','Extraordinaria'] or audience not in ['Interna','Iglesias'] or (org['id']!=1 and audience!='Interna'):raise ValueError('Revisa el tipo y el alcance de la reunión.')
                starts=o.timestamp(request.form.get('starts'));year=o.year(request.form.get('plan_year'))
                invites=set(request.form.getlist('invited',type=int)) if audience=='Iglesias' else set()
                valid={r['id'] for r in db().execute("SELECT id FROM groups WHERE active=1 AND kind IN ('SEC','GJ')")}
                if audience=='Iglesias' and (not invites or not invites<=valid):raise ValueError('Selecciona las iglesias convocadas.')
                mid=db().execute('INSERT INTO office_meetings(group_id,title,kind,audience,starts,location,agenda,plan_year,created_by,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(org['id'],o.text('title',limit=200),kind,audience,starts,o.text('location',False,500),o.text('agenda',False),year,g.user['id'],o.now(),o.now())).lastrowid
                db().executemany('INSERT INTO office_invites VALUES(?,?)',[(mid,gid) for gid in invites])
                o.commit('Convocó reunión #'+str(mid),org['id']);return redirect(url_for('.meeting',mid=mid))
            except (ValueError,sqlite3.IntegrityError) as exc:o.fail(exc)
        filter_year=request.args.get('year','');kind=request.args.get('kind','');query=request.args.get('q','').casefold()
        rows=[r for r in db().execute('SELECT m.*,a.status minutes_status FROM office_meetings m LEFT JOIN office_minutes a ON a.meeting_id=m.id WHERE m.group_id=? ORDER BY starts DESC',(org['id'],)) if (not filter_year or r['starts'].startswith(filter_year+'-')) and (not kind or r['kind']==kind) and query in (r['title']+' '+r['agenda']).casefold()]
        return page('meetings.html',meetings=rows,year=local_now().year)

    @bp.route('/reuniones/<int:mid>',methods=['GET','POST'])
    @logged
    def meeting(mid):
        meeting,org,own=access_meeting(mid)
        if request.method=='POST':
            o.require(org['id'],write=True)
            try:
                action=request.form.get('action')
                if action=='minutes':
                    if not own:abort(403)
                    state=o.text('status')
                    if state not in ['Borrador','Registrada','Firmada']:raise ValueError('Estado del acta inválido.')
                    summary=o.text('summary',False)
                    if not summary and not request.files.get('attachment') and not o.files('minutes',mid):raise ValueError('Escribe el resumen o sube el acta de la reunión.')
                    db().execute('INSERT INTO office_minutes VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(meeting_id) DO UPDATE SET folio=excluded.folio,attendance=excluded.attendance,summary=excluded.summary,agreements=excluded.agreements,correspondence=excluded.correspondence,status=excluded.status,updated_by=excluded.updated_by,updated=excluded.updated',(mid,o.text('folio',False,100),o.text('attendance',False),summary,o.text('agreements',False),o.text('correspondence',False),state,g.user['id'],o.now()))
                    o.upload('minutes',mid,org['id']);o.commit('Registró acta de reunión #'+str(mid),org['id'])
                elif action=='meeting':
                    if not own:abort(403)
                    state=o.text('status')
                    if state not in ['Convocada','Realizada','Cancelada']:raise ValueError('Estado de reunión inválido.')
                    db().execute('UPDATE office_meetings SET title=?,starts=?,location=?,agenda=?,status=?,updated=? WHERE id=?',(o.text('title',limit=200),o.timestamp(request.form.get('starts')),o.text('location',False,500),o.text('agenda',False),state,o.now(),mid))
                    o.commit('Actualizó reunión #'+str(mid),org['id'])
                elif action=='credential':
                    if own or meeting['audience']!='Iglesias' or meeting['status']=='Cancelada':abort(403)
                    attendees=o.text('attendees');old=db().execute('SELECT * FROM office_credentials WHERE meeting_id=? AND group_id=?',(mid,org['id'])).fetchone()
                    if old:
                        cid=old['id'];db().execute("UPDATE office_credentials SET attendees=?,status='Enviada',review_note='',reviewed_by=NULL,reviewed=NULL,sent_by=?,sent=? WHERE id=?",(attendees,g.user['id'],o.now(),cid))
                    else:cid=db().execute('INSERT INTO office_credentials(meeting_id,group_id,attendees,sent_by,sent) VALUES(?,?,?,?,?)',(mid,org['id'],attendees,g.user['id'],o.now())).lastrowid
                    o.upload('credential',cid,org['id'],required=True);o.commit('Envió credencial de reunión #'+str(mid),org['id'])
                elif action=='review_credential':
                    if not own:abort(403)
                    cred=o.row('office_credentials',request.form.get('credential_id',type=int))
                    if cred['meeting_id']!=mid:abort(403)
                    state=o.text('status')
                    if state not in ['Recibida','Observada']:raise ValueError('Selecciona Recibida u Observada.')
                    note=o.text('review_note',state=='Observada',2000)
                    db().execute('UPDATE office_credentials SET status=?,review_note=?,reviewed_by=?,reviewed=? WHERE id=?',(state,note,g.user['id'],o.now(),cred['id']))
                    o.commit('Recepcionó credencial #'+str(cred['id']),org['id'])
                else:abort(400)
                return redirect(url_for('.meeting',mid=mid))
            except (ValueError,sqlite3.IntegrityError) as exc:o.fail(exc)
        minutes=db().execute('SELECT * FROM office_minutes WHERE meeting_id=?',(mid,)).fetchone() if own else None
        credentials=db().execute('SELECT c.*,gr.name group_name FROM office_credentials c JOIN groups gr ON gr.id=c.group_id WHERE c.meeting_id=?'+('' if own else ' AND c.group_id=?')+' ORDER BY c.group_id', (mid,) if own else (mid,org['id'])).fetchall()
        invited=db().execute('SELECT gr.* FROM office_invites i JOIN groups gr ON gr.id=i.group_id WHERE i.meeting_id=?',(mid,)).fetchall()
        letters=db().execute('SELECT * FROM office_letters WHERE meeting_id=? AND group_id=? ORDER BY day',(mid,org['id'])).fetchall() if own else []
        return page('meeting.html',meeting=meeting,own=own,minutes=minutes,credentials=credentials,invited=invited,letters=letters)

    @bp.route('/planes',methods=['GET','POST'])
    @logged
    def plans():
        org=o.organization();o.require(org['id'])
        try:year=o.year(request.values.get('year',local_now().year))
        except ValueError:abort(400)
        if request.method=='POST':
            o.require(org['id'],write=True)
            try:
                action=request.form.get('action')
                if action=='save_plan':
                    db().execute('INSERT INTO office_plans(group_id,year,title,notes,updated) VALUES(?,?,?,?,?) ON CONFLICT(group_id,year) DO UPDATE SET title=excluded.title,notes=excluded.notes,updated=excluded.updated',(org['id'],year,o.text('title',limit=200),o.text('notes',False),o.now()))
                    plan=db().execute('SELECT * FROM office_plans WHERE group_id=? AND year=?',(org['id'],year)).fetchone()
                    o.upload('plan',plan['id'],org['id'],required=not bool(o.files('plan',plan['id'])))
                    o.commit('Guardó plan anual '+str(year),org['id'])
                elif action=='send_plan':
                    if org['id']==1:abort(403)
                    campaign=db().execute('SELECT * FROM office_campaigns WHERE year=?',(year,)).fetchone();plan=db().execute('SELECT * FROM office_plans WHERE group_id=? AND year=?',(org['id'],year)).fetchone()
                    if not campaign or not o.open_campaign(campaign):raise ValueError('DEPEC aún no ha abierto la recepción de este año o el plazo terminó.')
                    files=o.files('plan',plan['id']) if plan else []
                    if not files:raise ValueError('Sube primero tu plan anual.')
                    existing=db().execute('SELECT 1 FROM office_plan_deliveries WHERE campaign_id=? AND plan_id=? AND file_id=?',(campaign['id'],plan['id'],files[0]['id'])).fetchone()
                    if existing:raise ValueError('Esta versión ya fue enviada. Sube una revisión para realizar otra entrega.')
                    db().execute('INSERT INTO office_plan_deliveries(campaign_id,plan_id,file_id,sent_by,sent) VALUES(?,?,?,?,?)',(campaign['id'],plan['id'],files[0]['id'],g.user['id'],o.now()))
                    o.commit('Entregó plan anual '+str(year)+' a DEPEC',org['id'])
                else:abort(400)
                return redirect(url_for('.plans',year=year))
            except (ValueError,sqlite3.IntegrityError) as exc:o.fail(exc)
        plan=db().execute('SELECT * FROM office_plans WHERE group_id=? AND year=?',(org['id'],year)).fetchone();campaign=db().execute('SELECT * FROM office_campaigns WHERE year=?',(year,)).fetchone()
        deliveries=db().execute('SELECT d.* FROM office_plan_deliveries d JOIN office_plans p ON p.id=d.plan_id WHERE p.group_id=? AND p.year=? ORDER BY d.id DESC',(org['id'],year)).fetchall()
        return page('plans.html',year=year,plan=plan,campaign=campaign,deliveries=deliveries)

    @bp.route('/recepcion-planes',methods=['GET','POST'])
    @logged
    def campaigns():
        org=o.organization()
        if org['id']!=1:abort(403)
        o.require(1)
        try:year=o.year(request.values.get('year',local_now().year))
        except ValueError:abort(400)
        if request.method=='POST':
            o.require(org['id'],write=True)
            try:
                if request.form.get('action')=='campaign':
                    deadline=o.timestamp(request.form.get('deadline'))
                    db().execute('INSERT INTO office_campaigns(year,description,deadline,active,created_by,created) VALUES(?,?,?,?,?,?) ON CONFLICT(year) DO UPDATE SET description=excluded.description,deadline=excluded.deadline,active=excluded.active',(year,o.text('description',False),deadline,int(request.form.get('active')=='1'),g.user['id'],o.now()))
                    o.commit('Configuró recepción de planes '+str(year),1)
                elif request.form.get('action')=='review_plan':
                    delivery=o.row('office_plan_deliveries',request.form.get('delivery_id',type=int));state=o.text('status')
                    if state not in ['Recibido','Observado']:raise ValueError('Estado de recepción inválido.')
                    db().execute('UPDATE office_plan_deliveries SET status=?,review_note=?,reviewed_by=?,reviewed=? WHERE id=?',(state,o.text('review_note',state=='Observado',2000),g.user['id'],o.now(),delivery['id']))
                    o.commit('Recepcionó plan #'+str(delivery['id']),1)
                else:abort(400)
                return redirect(url_for('.campaigns',year=year))
            except (ValueError,sqlite3.IntegrityError) as exc:o.fail(exc)
        campaign=db().execute('SELECT * FROM office_campaigns WHERE year=?',(year,)).fetchone()
        deliveries=db().execute('SELECT d.*,gr.name group_name,p.title FROM office_plan_deliveries d JOIN office_plans p ON p.id=d.plan_id JOIN groups gr ON gr.id=p.group_id WHERE p.year=? ORDER BY d.id DESC',(year,)).fetchall()
        submitted={d['group_name'] for d in deliveries}
        missing=[r['name'] for r in db().execute("SELECT name FROM groups WHERE active=1 AND kind IN ('SEC','GJ')") if r['name'] not in submitted]
        return page('campaigns.html',year=year,campaign=campaign,deliveries=deliveries,missing=missing)

    @bp.route('/correspondencia',methods=['GET','POST'])
    @logged
    def letters():
        org=o.organization();o.require(org['id'])
        if request.method=='POST':
            o.require(org['id'],write=True)
            try:
                direction=o.text('direction')
                if direction not in ['Recibida','Enviada']:raise ValueError('Selecciona Recibida o Enviada.')
                mid=request.form.get('meeting_id',type=int)
                if mid and o.row('office_meetings',mid)['group_id']!=org['id']:abort(403)
                lid=db().execute('INSERT INTO office_letters(group_id,direction,number,day,subject,counterparty,body,meeting_id,created_by,created) VALUES(?,?,?,?,?,?,?,?,?,?)',(org['id'],direction,o.text('number',False,100),o.day(request.form.get('day')),o.text('subject',limit=200),o.text('counterparty',limit=300),o.text('body',False),mid,g.user['id'],o.now())).lastrowid
                o.upload('letter',lid,org['id'],required=True);o.commit('Archivó correspondencia #'+str(lid),org['id']);return redirect(url_for('.letters'))
            except (ValueError,sqlite3.IntegrityError) as exc:o.fail(exc)
        q=request.args.get('q','').casefold();direction=request.args.get('direction','');year=request.args.get('year','')
        rows=[r for r in db().execute('SELECT * FROM office_letters WHERE group_id=? ORDER BY day DESC,id DESC',(org['id'],)) if (not direction or r['direction']==direction) and (not year or r['day'].startswith(year+'-')) and q in (r['subject']+' '+r['counterparty']+' '+r['number']).casefold()]
        meetings=db().execute('SELECT * FROM office_meetings WHERE group_id=? ORDER BY starts DESC',(org['id'],)).fetchall()
        return page('letters.html',letters=rows,meetings=meetings)

    @bp.route('/plantillas',methods=['GET','POST'])
    @logged
    def templates():
        if not o.leader():abort(403)
        org=o.organization()
        if request.method=='POST':
            if org['id']!=1:abort(403)
            o.require(1,write=True)
            try:
                tid=db().execute('INSERT INTO office_templates(title,kind,description,created_by,created) VALUES(?,?,?,?,?)',(o.text('title',limit=200),o.text('kind',limit=100),o.text('description',False),g.user['id'],o.now())).lastrowid
                o.upload('template',tid,1,required=True);o.commit('Publicó plantilla #'+str(tid),1);return redirect(url_for('.templates'))
            except (ValueError,sqlite3.IntegrityError) as exc:o.fail(exc)
        return render_template('office/templates.html',org=org,brand_group=org,current_scope=org['id'],module='documents',office=o,templates=db().execute('SELECT * FROM office_templates WHERE active=1 ORDER BY id DESC').fetchall(),may_publish=org['id']==1 and o.can(1,write=True),office_write=org['id']==1 and o.can(1,write=True))

    @bp.get('/plantillas/base/<kind>')
    @logged
    def builtin_template(kind):
        if not o.leader():abort(403)
        names={'credencial':'Credencial para reunión','acta':'Acta de reunión','carta':'Carta institucional','plan':'Plan anual de trabajo'}
        if kind not in names:abort(404)
        from docx import Document
        from docx.shared import Pt
        doc=Document();doc.styles['Normal'].font.name='Calibri';doc.styles['Normal'].font.size=Pt(11)
        doc.add_heading(names[kind],0);doc.add_paragraph('Plantilla editable de referencia · DEPEC / SEC / GJ')
        fields={'credencial':['Iglesia: [nombre]','Reunión: [nombre, tipo y fecha]','Delegados: [nombres completos y cargos]','Vigencia: [fecha]','Firmas: [Presidencia y Secretaría]'], 'acta':['Organización y folio: [datos]','Reunión: [ordinaria / extraordinaria, fecha, hora y lugar]','Asistencia: [lista]','Agenda: [temas]','Correspondencia revisada: [cartas]','Desarrollo: [resumen]','Acuerdos: [responsables y plazos]','Cierre y firmas: [datos]'], 'carta':['Número: [correlativo]','Lugar y fecha: [datos]','Destinatario: [nombre y cargo]','Asunto: [asunto]','Saludo: [texto]','Cuerpo: [texto]','Despedida y firmas: [datos]'], 'plan':['Organización y año: [datos]','Objetivos: [objetivos del año]','Actividades: [nombre, fecha, responsable, recursos]','Coordinación DEPEC: [actividades conjuntas y fechas]','Presupuesto: [ingresos y egresos previstos]','Firmas: [datos]']}
        for text in fields[kind]:doc.add_paragraph(text)
        stream=io.BytesIO();doc.save(stream);stream.seek(0)
        return send_file(stream,as_attachment=True,download_name='plantilla_'+kind+'.docx',mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

    @bp.get('/reuniones/<int:mid>/acta.docx')
    @logged
    def minutes_docx(mid):
        meeting,org,own=access_meeting(mid)
        if not own:abort(403)
        minutes=db().execute('SELECT * FROM office_minutes WHERE meeting_id=?',(mid,)).fetchone()
        if not minutes:abort(404)
        from docx import Document
        from docx.shared import Pt
        doc=Document();doc.styles['Normal'].font.size=Pt(11)
        doc.add_heading('Acta de '+org['name'],0)
        doc.add_paragraph('Folio: '+(minutes['folio'] or 'Sin asignar')+' · Estado: '+minutes['status'])
        doc.add_heading(meeting['title'],1)
        doc.add_paragraph(meeting['kind']+' · '+meeting['starts'].replace('T',' · ')+' · '+meeting['location'])
        for title,content in [('Asistencia',minutes['attendance']),('Agenda',meeting['agenda']),('Desarrollo y resumen',minutes['summary']),('Correspondencia revisada',minutes['correspondence']),('Acuerdos',minutes['agreements'])]:
            doc.add_heading(title,2);doc.add_paragraph(content or 'Sin registro.')
        doc.add_paragraph('Presidencia: ____________________    Secretaría: ____________________')
        stream=io.BytesIO();doc.save(stream);stream.seek(0)
        return send_file(stream,as_attachment=True,download_name='acta_'+str(mid)+'.docx',mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

    @bp.get('/archivo/<int:fid>')
    @logged
    def file(fid):
        item=o.row('office_files',fid)
        if not o.file_allowed(item):abort(403)
        path=app.config['UPLOAD_FOLDER']+'/'+item['filename']
        return send_file(path,as_attachment=True,download_name=item['original_name'],mimetype=item['mime'])

    app.register_blueprint(bp)
