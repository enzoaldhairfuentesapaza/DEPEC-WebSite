import calendar
import csv
import io
import json
import os
import secrets
import sqlite3
import time
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps
from pathlib import Path
from uuid import uuid4

import click
from flask import Flask, abort, flash, g, redirect, render_template, request, send_file, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from .modules import MODULES, ROLES
from .community_data import upgrade_schema, local_now, event_presentation, picture_info, contrast_color, verse_lines
from .community import register_community
from .announcements import announcement_state


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.jinja_env.filters['verse_lines']=verse_lines
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    keyfile = Path(app.instance_path) / 'session.key'
    if not keyfile.exists():
        keyfile.write_text(secrets.token_hex(32),encoding='utf-8')
        keyfile.chmod(0o600)
    app.config.from_mapping(SECRET_KEY=os.getenv('SECRET_KEY') or keyfile.read_text(encoding='utf-8'), DATABASE=str(Path(app.instance_path)/'depec.sqlite'), UPLOAD_FOLDER=str(Path(app.instance_path)/'uploads'), MAX_CONTENT_LENGTH=10*1024*1024, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE')=='1', PERMANENT_SESSION_LIFETIME=timedelta(hours=8))
    if test_config:
        app.config.update(test_config)
    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True,exist_ok=True)
    if Path(app.config['DATABASE']).exists():
        with sqlite3.connect(app.config['DATABASE']) as connection:
            upgrade_schema(connection)
            from .retro_demo import seed_visual_demo
            seed_visual_demo(connection)

    def db():
        if 'db' not in g:
            g.db=sqlite3.connect(app.config['DATABASE'])
            g.db.row_factory=sqlite3.Row
            g.db.execute('PRAGMA foreign_keys=ON')
        return g.db

    @app.teardown_appcontext
    def close(_):
        connection=g.pop('db',None)
        if connection:
            connection.close()

    def now():
        return local_now().isoformat(timespec='seconds')

    def audit(action, group_id=None):
        db().execute('INSERT INTO audit(user_id,group_id,action,created) VALUES(?,?,?,?)',(g.user['id'],group_id,action,now()))

    def roles_for(group_id):
        if not g.user:
            return set()
        return {r['role'] for r in db().execute('SELECT role FROM assignments WHERE user_id=? AND active=1 AND group_id IN (?,1)',(g.user['id'],group_id))}

    def allowed(group_id,module,write=False):
        if not g.user:
            return False
        if g.user['admin']:
            return True
        grant=db().execute('SELECT max(can_write) FROM grants WHERE user_id=? AND group_id IN (?,1) AND module=? AND active=1',(g.user['id'],group_id,module)).fetchone()[0]
        if grant is not None and (not write or grant): return True
        roles=roles_for(group_id)
        if not roles:
            return False
        if {'Presidente','Vicepresidente','Líder'} & roles:
            return True
        if module in ['finance']:
            return bool({'Tesorero','Protesorero'} & roles)
        if module in {'members','documents','requests'}:
            return bool({'Secretario','Prosecretario'} & roles)
        if not write:
            return True
        return bool({'Secretario','Prosecretario'} & roles)

    def records(module, scope=None, public=False):
        rows=db().execute('SELECT records.*,groups.name group_name,groups.color FROM records JOIN groups ON groups.id=group_id WHERE module=? ORDER BY records.id DESC',(module,)).fetchall()
        result=[]
        for row in rows:
            item=dict(row); item['d']=json.loads(row['data'])
            if module=='announcements':item['d']['display_status']=announcement_state(item['d'])
            if module=='events':
                gr=db().execute('SELECT * FROM groups WHERE id=?',(item['group_id'],)).fetchone()
                item['d']=event_presentation(item['d'],gr)
            if scope and item['group_id']!=scope:
                continue
            if public:
                d=item['d']
                if d.get('visibility')!='public' or (module in ['posts','gallery'] and (d.get('status')!='Publicado' or (module=='posts' and d.get('date','')>now()))):
                    continue
            elif not allowed(item['group_id'],module):
                continue
            result.append(item)
        return result

    def get_record(record_id):
        row=db().execute('SELECT * FROM records WHERE id=?',(record_id,)).fetchone()
        if not row:
            abort(404)
        item=dict(row); item['d']=json.loads(row['data'])
        return item

    def logged(fn):
        @wraps(fn)
        def wrapped(*args,**kwargs):
            if not g.user:
                return redirect(url_for('login'))
            if not community['is_leader']() and db().execute('SELECT 1 FROM memberships WHERE user_id=?',(g.user['id'],)).fetchone() and request.endpoint not in ['dashboard','account','community.member_home','retro.member_profile']:
                abort(403)
            return fn(*args,**kwargs)
        return wrapped

    @app.before_request
    def before():
        g.user=db().execute('SELECT * FROM users WHERE id=? AND active=1',(session.get('uid'),)).fetchone() if session.get('uid') else None
        if request.endpoint!='static':
            completed=False
            for row in db().execute("SELECT id,data FROM records WHERE module='events'").fetchall():
                data=json.loads(row['data'])
                if data.get('status') not in ['Cancelado','Finalizado'] and data.get('end_date') and data['end_date']<now():
                    data['previous_status']=data.get('status'); data['status']='Finalizado'
                    db().execute('UPDATE records SET data=?,updated=? WHERE id=?',(json.dumps(data),now(),row['id']))
                    db().execute('INSERT INTO audit(action,created,group_id) SELECT ?,?,group_id FROM records WHERE id=?',('Sistema: finalizó evento #'+str(row['id']),now(),row['id']));completed=True
            if completed:db().commit()
        if 'csrf' not in session:
            session['csrf']=secrets.token_urlsafe(32)
        if request.method=='POST' and not secrets.compare_digest(session['csrf'],request.form.get('csrf','')):
            abort(400, 'El formulario expiró. Recarga la página e inténtalo de nuevo.')

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Referrer-Policy']='same-origin'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        if g.get('user') or request.endpoint=='public':
            response.headers['Cache-Control']='no-store'
        return response

    @app.context_processor
    def context():
        groups=db().execute('SELECT * FROM groups ORDER BY id').fetchall()
        demo_mode=db().execute("SELECT 1 FROM users WHERE email='admin@depec.demo'").fetchone() is not None
        scope=request.args.get('group',type=int) or 1
        if request.endpoint=='community.album':
            album=db().execute('SELECT group_id FROM albums WHERE id=?',((request.view_args or {}).get('album_id'),)).fetchone()
            if album:scope=album['group_id']
        brand_group=db().execute('SELECT * FROM groups WHERE id=?',(scope,)).fetchone()
        return dict(contrast_color=contrast_color,brand_group=brand_group,is_leader=community['is_leader'],can_review=community['can_review'],demo_mode=demo_mode,modules=MODULES, groups=groups, can=allowed, csrf=session.get('csrf'), today=local_now().date().isoformat(), roles=ROLES, current_scope=request.args.get('group',''), nav=request.endpoint)

    @app.route('/')
    def public():
        scope=request.args.get('group',type=int)
        selected=db().execute('SELECT * FROM groups WHERE id=?',(scope,)).fetchone() if scope else None
        if scope and not selected:abort(404)
        active_scope=scope or 1
        return render_template('public.html',selected=selected if active_scope!=1 else None,events=sorted(records('events',scope,True),key=lambda r:r['d'].get('date','')),posts=records('posts',scope,True),gallery=records('gallery',scope,True),public_page=True,**community['public_context'](active_scope))

    @app.route('/login',methods=['GET','POST'])
    def login():
        if request.method=='POST':
            email=request.form.get('email','').strip().lower()
            db().execute('DELETE FROM attempts WHERE created<?',(time.time()-900,))
            count=db().execute('SELECT count(*) FROM attempts WHERE email=?',(email,)).fetchone()[0]
            if count>=8:
                db().commit(); abort(429,'Demasiados intentos. Espera 15 minutos.')
            user=db().execute('SELECT * FROM users WHERE email=? AND active=1',(email,)).fetchone()
            if user and check_password_hash(user['password'],request.form.get('password','')):
                db().execute('DELETE FROM attempts WHERE email=?',(email,)); db().commit()
                session.clear(); session['uid']=user['id']; session['csrf']=secrets.token_urlsafe(32); session.permanent=True
                return redirect(url_for('dashboard'))
            db().execute('INSERT INTO attempts VALUES(?,?)',(email,time.time())); db().commit()
            flash('Correo o contraseña incorrectos.','error')
        return render_template('login.html',public_page=True)

    @app.post('/logout')
    def logout():
        session.clear()
        return redirect(url_for('public'))

    @app.get('/panel')
    @logged
    def dashboard():
        if not community['is_leader']() and db().execute("SELECT 1 FROM memberships WHERE user_id=? AND status='Aprobado'",(g.user['id'],)).fetchone():return redirect(url_for('community.member_home'))
        scope=request.args.get('group',type=int)
        members=records('members',scope); events=records('events',scope)
        money=records('finance',scope)
        balance=sum((Decimal(r['d'].get('amount','0'))*(1 if r['d'].get('category')=='Ingreso' else -1) for r in money if r['d'].get('status')=='Aprobado'),Decimal(0))
        upcoming=sorted([r for r in events if r['d'].get('date','')[:10]>=date.today().isoformat() and r['d'].get('status')!='Cancelado'], key=lambda r:r['d']['date'])
        pending=[r for r in records('requests',scope)+records('tasks',scope) if r['d'].get('status') in ['Pendiente','Observado','En proceso']]
        return render_template('dashboard.html',members=members,events=upcoming,money=money,balance=balance,pending=pending,posts=records('posts',scope)[:3])

    @app.get('/calendar')
    def calendar_view():
        public_mode=not g.user or request.args.get('public')=='1'
        scope=request.args.get('group',type=int)
        try:
            first=date.fromisoformat(request.args.get('month',local_now().strftime('%Y-%m')+'-01')) .replace(day=1)
        except ValueError:
            abort(400)
        events=records('events',scope,public_mode)
        weeks=calendar.Calendar(firstweekday=0).monthdatescalendar(first.year,first.month)
        previous=(first-timedelta(days=1)).replace(day=1).isoformat()
        following=(first+timedelta(days=32)).replace(day=1).isoformat()
        names=['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
        selected_event=None
        event_id=request.args.get('event',type=int)
        if event_id:
            selected_event=next((ev for ev in events if ev['id']==event_id),None)
            if not selected_event:abort(404)
        return render_template('calendar.html',selected_event=selected_event,events=events,weeks=weeks,first=first,previous=previous,following=following,month_name=names[first.month-1],public_page=public_mode)

    @app.get('/birthdays')
    @logged
    def birthdays():
        members=records('members',request.args.get('group',type=int))
        try:
            month=int(request.args.get('month',date.today().month))
            if not 1<=month<=12: raise ValueError()
        except ValueError: abort(400)
        return render_template('birthdays.html',items=sorted([r for r in members if int(r['d']['date'][5:7])==month],key=lambda r:r['d']['date'][8:]),month=month)

    @app.get('/manage/<module>')
    @logged
    def listing(module):
        if module not in MODULES: abort(404)
        items=records(module,request.args.get('group',type=int))
        q=request.args.get('q','').casefold()
        status=request.args.get('status','')
        items=[r for r in items if q in ' '.join(str(v) for k,v in r['d'].items() if k!='attachment').casefold() and (not status or r['d'].get('status')==status)]
        return render_template('listing.html',module=module,config=MODULES[module],items=items)

    def validate(module, group_id, existing=None):
        data=dict(existing or {})
        for field in MODULES[module]['fields']:
            key=field['key']; kind=field['kind']
            if kind=='file': continue
            value=request.form.get(key,'').strip()
            if field['required'] and not value: raise ValueError('Completa '+field['label']+'.')
            if len(value)>12000: raise ValueError('Texto demasiado largo.')
            if kind=='select' and value and value not in field['options']: raise ValueError('Opción inválida.')
            if value and kind in ['date','datetime-local']:
                datetime.fromisoformat(value)
            if value and kind=='money':
                amount=Decimal(value)
                if not amount.is_finite() or amount<0 or amount>Decimal('999999999') or amount.as_tuple().exponent < -2: raise ValueError('El monto debe ser positivo, con hasta dos decimales.')
                value=str(amount.quantize(Decimal('.01')))
            if kind=='number':
                number=int(value or 0)
                if not 0<=number<=100000: raise ValueError('Cupos inválidos.')
                value=str(number)
            if value and kind=='event':
                target=get_record(int(value))
                if target['module']!='events' or target['group_id']!=group_id: raise ValueError('El evento debe pertenecer al mismo grupo.')
            data[key]=value
        if module=='announcements':
            start=datetime.fromisoformat(data['date']);end=datetime.fromisoformat(data['end_date'])
            if start.tzinfo or end.tzinfo or end<=start:raise ValueError('El vencimiento debe ser posterior al inicio, con la hora local de Perú.')
        if module=='events':
            group=db().execute('SELECT * FROM groups WHERE id=?',(group_id,)).fetchone()
            if not data.get('location'):data['location']=group['address']
            if not data.get('event_address'):data['event_address']=data.get('location') or group['address']
            data['media_kind']=data.get('media_kind') or 'Afiche'
        if module=='events' and data['end_date']<data['date']: raise ValueError('La finalización debe ser posterior al inicio.')
        if module=='members' and data['date']>date.today().isoformat(): raise ValueError('La fecha de nacimiento no puede ser futura.')
        file=request.files.get('attachment')
        if file and file.filename:
            filename=secure_filename(file.filename)
            extensions={'png','jpg','jpeg'} if module in ['gallery','events','posts'] else {'pdf','docx','xlsx','png','jpg','jpeg'}
            if '.' not in filename or filename.rsplit('.',1)[-1].lower() not in extensions:
                raise ValueError('Formato de archivo no permitido.')
            if module in ['gallery','events','posts']:
                header=file.stream.read(12); file.stream.seek(0)
                ext=filename.rsplit('.',1)[-1].lower()
                if not ((ext=='png' and header.startswith(b'\x89PNG\r\n\x1a\n')) or (ext in ['jpg','jpeg'] and header.startswith(b'\xff\xd8\xff'))): raise ValueError('Imagen inválida.')
            if module in ['gallery','events','posts']:
                data['image_width'],data['image_height']=picture_info(file)
            storage=uuid4().hex+'_'+filename
            file.save(Path(app.config['UPLOAD_FOLDER'])/storage)
            data['attachment']=storage
            data['attachment_name']=filename
        if module=='gallery' and not data.get('attachment'): raise ValueError('Adjunta una imagen.')
        return data

    @app.route('/manage/<module>/new',methods=['GET','POST'])
    @app.route('/manage/<module>/<int:record_id>/edit',methods=['GET','POST'])
    @logged
    def edit(module,record_id=None):
        if module not in MODULES: abort(404)
        item=get_record(record_id) if record_id else None
        if item and item['module']!=module: abort(404)
        if item and not allowed(item['group_id'],module,True): abort(403)
        writable=[dict(r) for r in db().execute('SELECT * FROM groups WHERE active=1') if allowed(r['id'],module,True)]
        if not writable: abort(403)
        data=item['d'] if item else {}
        group_id=item['group_id'] if item else request.args.get('group',type=int)
        if request.method=='POST':
            try:
                submitted=int(request.form.get('group_id','0'))
                if item and submitted!=item['group_id']: abort(403)
                if not any(r['id']==submitted for r in writable): abort(403)
                group_id=submitted
                data=validate(module,group_id,data)
                if item:
                    db().execute('UPDATE records SET data=?,updated=? WHERE id=?',(json.dumps(data),now(),record_id))
                else:
                    cursor=db().execute('INSERT INTO records(module,group_id,data,author_id,created,updated) VALUES(?,?,?,?,?,?)',(module,group_id,json.dumps(data),g.user['id'],now(),now()))
                    record_id=cursor.lastrowid
                if data.get('attachment') and module in ['events','posts','gallery']:
                    kind=data.get('media_kind') or ('Fotografía' if module=='gallery' else 'Afiche')
                    visibility='public' if data.get('visibility')=='public' and (module=='events' or data.get('status')=='Publicado') else 'internal'
                    prior=db().execute('SELECT id,filename FROM media_files WHERE record_id=?',(record_id,)).fetchone()
                    if prior:
                        db().execute('UPDATE media_files SET title=?,kind=?,filename=?,width=?,height=?,visibility=? WHERE id=?',(data['title'],kind,data['attachment'],int(data.get('image_width',1)),int(data.get('image_height',1)),visibility,prior['id']))
                        if prior['filename']!=data['attachment']:db().execute('UPDATE media_files SET uploaded_by=?,created=? WHERE id=?',(g.user['id'],now(),prior['id']))
                    else:db().execute('INSERT INTO media_files(group_id,record_id,title,kind,filename,width,height,uploaded_by,visibility,created) VALUES(?,?,?,?,?,?,?,?,?,?)',(group_id,record_id,data['title'],kind,data['attachment'],int(data.get('image_width',1)),int(data.get('image_height',1)),g.user['id'],visibility,now()))
                audit(f'{"Actualizó" if item else "Creó"} {MODULES[module]["singular"]} #{record_id}: {data["title"]}',group_id)
                db().commit(); flash('Guardado correctamente.','success')
                return redirect(url_for('listing',module=module,group=group_id))
            except (ValueError,InvalidOperation):
                flash('Revisa los datos: campos obligatorios, fechas y montos válidos; inicio anterior al fin.','error')
                data={**data,**request.form.to_dict()}
        return render_template('edit.html',module=module,config=MODULES[module],item=item,data=data,writable=writable,selected_group=group_id,event_options=records('events'))

    @app.post('/records/<int:record_id>/delete')
    @logged
    def delete(record_id):
        item=get_record(record_id)
        if not allowed(item['group_id'],item['module'],True): abort(403)
        db().execute('DELETE FROM media_files WHERE record_id=?',(record_id,))
        db().execute('DELETE FROM records WHERE id=?',(record_id,))
        audit(f'Eliminó {item["module"]} #{record_id}',item['group_id']); db().commit()
        if item['d'].get('attachment'):
            (Path(app.config['UPLOAD_FOLDER'])/item['d']['attachment']).unlink(missing_ok=True)
        flash('Registro eliminado.','success')
        return redirect(url_for('listing',module=item['module']))

    @app.get('/records/<int:record_id>/file')
    @logged
    def download(record_id):
        item=get_record(record_id)
        if not allowed(item['group_id'],item['module']): abort(403)
        filename=item['d'].get('attachment')
        if not filename: abort(404)
        return send_file(Path(app.config['UPLOAD_FOLDER'])/filename,as_attachment=True,download_name=item['d'].get('attachment_name','documento'))

    @app.get('/media/<int:record_id>')
    def media(record_id):
        item=get_record(record_id)
        if item['module'] not in ['events','posts','gallery']: abort(404)
        d=item['d']
        is_public=d.get('visibility')=='public' and (item['module']=='events' or (d.get('status')=='Publicado' and (item['module']=='gallery' or d.get('date','')<=now())))
        if not is_public and not allowed(item['group_id'],item['module']): abort(403)
        if not d.get('attachment'): abort(404)
        return send_file(Path(app.config['UPLOAD_FOLDER'])/d['attachment'])

    @app.get('/export/<module>')
    @logged
    def export(module):
        if module not in MODULES: abort(404)
        items=records(module,request.args.get('group',type=int))
        output=io.StringIO(); writer=csv.writer(output)
        fields=[f for f in MODULES[module]['fields'] if f['kind']!='file']
        writer.writerow(['Grupo']+[f['label'] for f in fields])
        def safe(value):
            value=str(value)
            return "'"+value if value.lstrip().startswith(('=','+','-','@','\t','\r')) else value
        for item in items:
            writer.writerow([safe(item['group_name'])]+[safe(item['d'].get(f['key'],'')) for f in fields])
        return send_file(io.BytesIO(('\ufeff'+output.getvalue()).encode()),as_attachment=True,download_name=module+'.csv',mimetype='text/csv')

    @app.route('/participation/<int:record_id>',methods=['GET','POST'])
    @logged
    def participation(record_id):
        item=get_record(record_id)
        if item['module'] not in ['events','meetings'] or not allowed(item['group_id'],'members'): abort(403)
        members=records('members',item['group_id'])
        if request.method=='POST':
            if not allowed(item['group_id'],'members',True): abort(403)
            member_id=request.form.get('member_id',type=int)
            status=request.form.get('status')
            if status not in ['Inscrito','Presente','Ausente','Justificado'] or member_id not in [r['id'] for r in members]: abort(400)
            if status=='Inscrito' and item['module']=='events':
                cap=int(item['d'].get('capacity') or 0)
                count=db().execute('SELECT count(*) FROM participation WHERE record_id=? AND member_id<>? AND status IN (\'Inscrito\',\'Presente\')',(record_id,member_id)).fetchone()[0]
                if cap and count>=cap: abort(400,'No hay cupos disponibles.')
            db().execute('INSERT INTO participation(record_id,member_id,status) VALUES(?,?,?) ON CONFLICT(record_id,member_id) DO UPDATE SET status=excluded.status',(record_id,member_id,status))
            audit(f'Registró asistencia/inscripción en #{record_id}',item['group_id']); db().commit()
            flash('Participación actualizada.','success')
            return redirect(url_for('participation',record_id=record_id))
        statuses={r['member_id']:r['status'] for r in db().execute('SELECT * FROM participation WHERE record_id=?',(record_id,))}
        return render_template('participation.html',item=item,members=members,statuses=statuses)

    @app.route('/account',methods=['GET','POST'])
    @logged
    def account():
        if request.method=='POST':
            new=request.form.get('new','')
            if not check_password_hash(g.user['password'],request.form.get('old','')) or len(new)<12:
                flash('Verifica la contraseña actual. La nueva debe tener al menos 12 caracteres.','error')
            else:
                db().execute('UPDATE users SET password=? WHERE id=?',(generate_password_hash(new),g.user['id'])); audit('Cambió su contraseña'); db().commit(); flash('Contraseña actualizada.','success')
        return render_template('account.html',public_page=not community['is_leader']())

    @app.route('/organization',methods=['GET','POST'])
    @logged
    def organization():
        if request.method=='POST':
            if not g.user['admin']: abort(403)
            try:
                action=request.form['action']
                if action=='group':
                    kind=request.form['kind']; color=request.form['color']
                    if kind not in ['SEC','GJ','DEPEC'] or len(color)!=7 or color[0]!='#' or any(c not in '0123456789abcdefABCDEF' for c in color[1:]): raise ValueError()
                    values=(request.form['name'].strip(),kind,color,request.form.get('description',''),request.form.get('church',''),request.form.get('address',''),request.form.get('schedule',''))
                    if not values[0]: raise ValueError()
                    gid=request.form.get('id',type=int)
                    if gid==1 and kind!='DEPEC': raise ValueError()
                    if gid:
                        db().execute('UPDATE groups SET name=?,kind=?,color=?,description=?,church=?,address=?,schedule=? WHERE id=?',(*values,gid))
                    else:
                        db().execute('INSERT INTO groups(name,kind,color,description,church,address,schedule) VALUES(?,?,?,?,?,?,?)',values)
                elif action=='user':
                    password=request.form['password']
                    if len(password)<12 or '@' not in request.form['email'] or not request.form['name'].strip(): raise ValueError()
                    db().execute('INSERT INTO users(name,email,password) VALUES(?,?,?)',(request.form['name'],request.form['email'].strip().lower(),generate_password_hash(password)))
                elif action=='assignment':
                    if request.form['role'] not in ROLES: raise ValueError()
                    db().execute('INSERT INTO assignments(user_id,group_id,role,period) VALUES(?,?,?,?)',(int(request.form['user_id']),int(request.form['group_id']),request.form['role'],request.form['period']))
                elif action=='revoke':
                    db().execute('UPDATE assignments SET active=0 WHERE id=?',(int(request.form['id']),))
                elif action=='grant':
                    if request.form['module'] not in MODULES: raise ValueError()
                    db().execute('INSERT INTO grants(user_id,group_id,module,can_write) VALUES(?,?,?,?)',(int(request.form['user_id']),int(request.form['group_id']),request.form['module'],int(request.form.get('can_write')=='1')))
                elif action=='revoke_grant':
                    db().execute('UPDATE grants SET active=0 WHERE id=?',(int(request.form['id']),))
                elif action=='toggle_user':
                    uid=int(request.form['id'])
                    if uid==g.user['id']: raise ValueError()
                    db().execute('UPDATE users SET active=1-active WHERE id=? AND admin=0',(uid,))
                else: abort(400)
                audit('Administración: '+action); db().commit(); flash('Organización actualizada.','success')
            except (ValueError,sqlite3.IntegrityError,KeyError):
                db().rollback(); flash('Datos inválidos o duplicados. Revisa el formulario.','error')
            return redirect(url_for('organization'))
        assignments=db().execute('SELECT a.*,u.name person,gr.name organization FROM assignments a JOIN users u ON a.user_id=u.id JOIN groups gr ON gr.id=a.group_id ORDER BY a.id DESC').fetchall() if g.user['admin'] else db().execute('SELECT a.*,u.name person,gr.name organization FROM assignments a JOIN users u ON a.user_id=u.id JOIN groups gr ON gr.id=a.group_id WHERE a.active=1').fetchall()
        users=db().execute('SELECT id,name,email,active FROM users').fetchall() if g.user['admin'] else []
        grants=db().execute('SELECT p.*,u.name person,gr.name organization FROM grants p JOIN users u ON u.id=p.user_id JOIN groups gr ON gr.id=p.group_id WHERE p.active=1').fetchall() if g.user['admin'] else []
        return render_template('organization.html',assignments=assignments,users=users,grants=grants)

    @app.get('/reports')
    @logged
    def reports():
        rows=[]
        for group in db().execute('SELECT * FROM groups'):
            if not any(allowed(group['id'],m) for m in MODULES): continue
            members=records('members',group['id']); money=records('finance',group['id'])
            approved=[r for r in money if r['d'].get('status')=='Aprobado']
            income=sum((Decimal(r['d']['amount']) for r in approved if r['d']['category']=='Ingreso'),Decimal(0))
            expense=sum((Decimal(r['d']['amount']) for r in approved if r['d']['category']=='Egreso'),Decimal(0))
            rows.append(dict(group=group,members=len(members),baptized=sum(r['d']['category']=='Bautizado' for r in members),events=len(records('events',group['id'])),income=income,expense=expense,balance=income-expense,see_members=allowed(group['id'],'members'),see_money=allowed(group['id'],'finance')))
        return render_template('reports.html',rows=rows)

    @app.get('/audit')
    @logged
    def audit_view():
        rows=db().execute('SELECT a.*,u.name person,gr.name organization FROM audit a LEFT JOIN users u ON a.user_id=u.id LEFT JOIN groups gr ON a.group_id=gr.id ORDER BY a.id DESC LIMIT 500').fetchall()
        rows=[r for r in rows if g.user['admin'] or (r['group_id'] and {'Presidente','Vicepresidente'} & roles_for(r['group_id']))]
        return render_template('audit.html',items=rows)

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(413)
    @app.errorhandler(429)
    def error(error):
        return render_template('error.html',error=error,public_page=not g.user),error.code

    @app.cli.command('init-db')
    def init_db():
        db().executescript((Path(__file__).parent/'schema.sql').read_text(encoding='utf-8'))
        db().execute("INSERT OR IGNORE INTO groups(id,name,kind,color,description) VALUES(1,'DEPEC','DEPEC','#d46a3b','Una comunidad, muchos caminos para servir.')")
        db().commit()
        upgrade_schema(db())
        click.echo('Base de datos inicializada.')

    @app.cli.command('upgrade-db')
    def upgrade_db():
        upgrade_schema(db());click.echo('Esquema actualizado sin eliminar registros.')

    @app.cli.command('seed-demo')
    def seed_demo():
        from .seed import seed
        seed(db()); click.echo('Datos ficticios creados. Consulta README.md para ingresar.')

    @app.cli.command('demo-retro')
    def demo_retro():
        from .retro_demo import seed_visual_demo
        upgrade_schema(db());added=seed_visual_demo(db());click.echo('Ejemplos retro añadidos.' if added else 'No se añadieron duplicados; exige una base de demostración.')

    @app.cli.command('create-admin')
    @click.option('--email',prompt=True)
    @click.option('--name',prompt=True)
    @click.option('--password',prompt=True,hide_input=True,confirmation_prompt=True)
    def create_admin(email,name,password):
        if len(password)<12: raise click.ClickException('Usa 12 caracteres como mínimo.')
        db().execute('INSERT INTO users(name,email,password,admin) VALUES(?,?,?,1)',(name,email.lower(),generate_password_hash(password))); db().commit(); click.echo('Administrador creado.')

    community=register_community(app,dict(db=db,allowed=allowed,logged=logged,audit=audit,now=now,roles_for=roles_for,get_record=get_record))
    return app
