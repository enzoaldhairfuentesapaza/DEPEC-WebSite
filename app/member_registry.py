"""Registro de integrantes vinculado con cuentas y aprobación por iglesia."""
import json,re,sqlite3
from datetime import date
from pathlib import Path
from uuid import uuid4
from flask import request,g,abort,render_template,redirect,url_for,flash,send_file
from werkzeug.security import generate_password_hash
from .community_data import picture_info

def register_members(app,db,allowed,logged,records,get_record,now,audit):
    @app.before_request
    def prepare():
        db().execute('CREATE TABLE IF NOT EXISTS member_accounts(record_id INTEGER PRIMARY KEY REFERENCES records(id) ON DELETE CASCADE,user_id INTEGER NOT NULL UNIQUE REFERENCES users(id))')
        # Integrar solicitudes anteriores aprobadas sin duplicar registros existentes.
        for m in db().execute("SELECT ms.*,u.name,u.email FROM memberships ms JOIN users u ON u.id=ms.user_id WHERE ms.status='Aprobado' AND ms.group_id!=1 AND NOT EXISTS(SELECT 1 FROM member_accounts a WHERE a.user_id=u.id)").fetchall():
            existing=next((r for r in db().execute("SELECT id,data FROM records WHERE module='members' AND group_id=?",(m['group_id'],)) if json.loads(r['data']).get('email','').lower()==m['email'].lower()),None)
            rid=existing['id'] if existing else db().execute("INSERT INTO records(module,group_id,data,author_id,created,updated) VALUES('members',?,?,?,?,?)",(m['group_id'],json.dumps(dict(title=m['name'],email=m['email'],date='',joined=m['created'][:10],category='No bautizado',status='Activo',public_birthday='No')),m['user_id'],now(),now())).lastrowid
            db().execute('INSERT OR IGNORE INTO member_accounts VALUES(?,?)',(rid,m['user_id']))
        db().commit()

    @app.context_processor
    def member_context():
        return dict(has_member_account=bool(g.user and db().execute('SELECT 1 FROM member_accounts WHERE user_id=?',(g.user['id'],)).fetchone()))

    def detach(rid):
        account=db().execute('SELECT user_id FROM member_accounts WHERE record_id=?',(rid,)).fetchone()
        if account:
            uid=account['user_id']
            db().execute('DELETE FROM member_accounts WHERE record_id=?',(rid,))
            db().execute('DELETE FROM memberships WHERE user_id=?',(uid,))
            db().execute('DELETE FROM member_profiles WHERE user_id=?',(uid,))
            if not db().execute('SELECT 1 FROM assignments WHERE user_id=? AND active=1',(uid,)).fetchone():db().execute('UPDATE users SET active=0 WHERE id=?',(uid,))
        db().execute('DELETE FROM participation WHERE member_id=?',(rid,))

    def editor(rid=None,self_edit=False,join=False):
        item=get_record(rid) if rid else None
        if item and (item['module']!='members' or (not self_edit and not allowed(item['group_id'],'members',True))):abort(403)
        groups=[dict(r) for r in db().execute("SELECT * FROM groups WHERE active=1 AND kind IN ('SEC','GJ')") if join or self_edit or allowed(r['id'],'members',True)]
        if not groups:abort(403)
        account=db().execute('SELECT user_id FROM member_accounts WHERE record_id=?',(rid,)).fetchone() if rid else None
        data=dict(item['d']) if item else dict(category='No bautizado',status='Activo',public_birthday='No',joined=date.today().isoformat(),avatar='luz')
        gid=item['group_id'] if item else request.args.get('group',type=int) or groups[0]['id']
        if not item and gid not in [r['id'] for r in groups]:gid=groups[0]['id']
        if request.method=='POST':
            try:
                submitted=request.form.get('group_id',type=int)
                if item and submitted!=gid:abort(403)
                if submitted not in [r['id'] for r in groups]:abort(403)
                gid=submitted
                for key in ['title','email','phone','date','joined','baptism_date','guardian','body','avatar']:
                    data[key]=request.form.get(key,request.form.get('name','') if key=='title' else '').strip()
                    if len(data[key])>12000:raise ValueError('El texto es demasiado largo.')
                data['email']=data['email'].lower()
                if not data['title'] or len(data['title'])>120 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',data['email']):raise ValueError('Indica nombre y correo válido.')
                if data['date'] and date.fromisoformat(data['date'])>date.today():raise ValueError('Revisa la fecha de nacimiento.')
                if not self_edit:
                    data['category']='Bautizado' if request.form.get('baptized') else 'No bautizado'
                    data['status']='Activo' if request.form.get('active') else 'Inactivo'
                data['public_birthday']='Sí' if request.form.get('birthday') else 'No'
                if data['avatar'] not in ['luz','paloma','biblia','pez','cruz']:data['avatar']='luz'
                password=request.form.get('password','')
                needs_account=not account
                if needs_account and not 12<=len(password)<=200:raise ValueError('La contraseña inicial debe tener entre 12 y 200 caracteres.')
                if db().execute('SELECT 1 FROM users WHERE email=? AND id!=?',(data['email'],account['user_id'] if account else -1)).fetchone():raise ValueError('Ese correo ya tiene una cuenta. Usa otro correo o edita el integrante existente.')
                photo=request.files.get('photo')
                if photo and photo.filename:
                    picture_info(photo)
                    from PIL import Image
                    image=Image.open(photo);image.thumbnail((1200,1200));name=uuid4().hex+'.png';image.convert('RGB').save(Path(app.config['UPLOAD_FOLDER'])/name,'PNG');data['photo']=name
                if needs_account:
                    uid=db().execute('INSERT INTO users(name,email,password,active) VALUES(?,?,?,?)',(data['title'],data['email'],generate_password_hash(password),int(not join))).lastrowid
                    db().execute('INSERT INTO memberships(user_id,group_id,status,created) VALUES(?,?,?,?)',(uid,gid,'Pendiente' if join else 'Aprobado',now()))
                else:
                    uid=account['user_id'];db().execute('UPDATE users SET name=?,email=? WHERE id=?',(data['title'],data['email'],uid))
                if item:db().execute('UPDATE records SET data=?,updated=? WHERE id=?',(json.dumps(data),now(),rid))
                else:
                    rid=db().execute("INSERT INTO records(module,group_id,data,author_id,created,updated) VALUES('members',?,?,?,?,?)",(gid,json.dumps(data),uid if join else g.user['id'],now(),now())).lastrowid
                if needs_account:db().execute('INSERT INTO member_accounts VALUES(?,?)',(rid,uid))
                db().execute("INSERT INTO member_profiles(user_id,avatar,photo,updated) VALUES(?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET avatar=excluded.avatar,photo=CASE WHEN excluded.photo!='' THEN excluded.photo ELSE member_profiles.photo END,status='Pendiente',updated=excluded.updated",(uid,data.get('avatar','luz'),data.get('photo',''),now()))
                audit('Actualizó integrante #'+str(rid),gid) if not join else None
                db().commit()
                flash('Solicitud enviada. Tu iglesia debe aprobarla antes de que puedas iniciar sesión.' if join else 'Datos del integrante guardados.','success')
                if join:return render_template('join.html',submitted=True,public_page=True)
                return redirect(url_for('member_self') if self_edit else url_for('listing',module='members',group=gid))
            except (ValueError,sqlite3.IntegrityError) as exc:
                db().rollback();flash(str(exc) if isinstance(exc,ValueError) else 'No se pudo guardar el registro. Revisa el correo.','error')
        return render_template('member_editor.html',data=data,item=item,member_groups=groups,gid=gid,needs_account=not account,self_edit=self_edit,join=join,public_page=join or self_edit)

    @app.route('/mi-datos',methods=['GET','POST'])
    @logged
    def member_self():
        row=db().execute("SELECT a.record_id FROM member_accounts a JOIN memberships ms ON ms.user_id=a.user_id WHERE a.user_id=? AND ms.status='Aprobado'",(g.user['id'],)).fetchone()
        if not row:abort(403)
        return editor(row['record_id'],self_edit=True)

    @app.post('/members/<int:rid>/switch')
    @logged
    def member_switch(rid):
        item=get_record(rid)
        if item['module']!='members' or not allowed(item['group_id'],'members',True):abort(403)
        field=request.form.get('field')
        if field not in ['category','status']:abort(400)
        values=['No bautizado','Bautizado'] if field=='category' else ['Inactivo','Activo']
        item['d'][field]=values[int(request.form.get('enabled')=='1')]
        db().execute('UPDATE records SET data=?,updated=? WHERE id=?',(json.dumps(item['d']),now(),rid));audit('Cambió '+field+' del integrante #'+str(rid),item['group_id']);db().commit()
        return redirect(url_for('listing',module='members',group=request.form.get('group',''),q=request.form.get('q','')))

    @app.get('/members/<int:rid>/photo')
    @logged
    def member_photo(rid):
        item=get_record(rid);account=db().execute('SELECT user_id FROM member_accounts WHERE record_id=?',(rid,)).fetchone()
        if item['module']!='members' or not (allowed(item['group_id'],'members') or account and account['user_id']==g.user['id']):abort(403)
        if item['d'].get('photo'):return send_file(Path(app.config['UPLOAD_FOLDER'])/item['d']['photo'])
        return send_file(Path(app.static_folder)/'avatars'/(item['d'].get('avatar','luz')+'.svg'))

    def listing(scope):
        items=[r for r in records('members',None if scope==1 else scope) if r['group_id']!=1]
        items=[r for r in items if not db().execute("SELECT 1 FROM member_accounts a JOIN memberships ms ON ms.user_id=a.user_id WHERE a.record_id=? AND ms.status!='Aprobado'",(r['id'],)).fetchone()]
        q=request.args.get('q','').casefold();items=[r for r in items if q in json.dumps(r['d'],ensure_ascii=False).casefold()]
        return render_template('member_list.html',items=items,module='members',current_scope=scope or '')
    return dict(editor=editor,listing=listing,detach=detach)
