"""Álbumes, archivos, perfiles y membresía aprobada. Permisos siempre en servidor."""
import re
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4
from flask import Blueprint, abort, flash, g, redirect, render_template, request, send_file, url_for
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from .community_data import daily_verse, picture_info


def register_community(app, services):
    bp=Blueprint('community',__name__)
    db,allowed,logged,audit,now,roles_for=[services[k] for k in ['db','allowed','logged','audit','now','roles_for']]

    def is_leader():
        return bool(g.user and (g.user['admin'] or db().execute('SELECT 1 FROM assignments WHERE user_id=? AND active=1',(g.user['id'],)).fetchone()))

    def can_review(gid):
        return bool(g.user and (g.user['admin'] or {'Presidente','Vicepresidente','Secretario','Prosecretario','Líder'} & roles_for(gid)))

    def save_image(file):
        name=secure_filename(file.filename or '')
        if '.' not in name or name.rsplit('.',1)[-1].lower() not in ['png','jpg','jpeg']:raise ValueError('Usa PNG o JPG.')
        width,height=picture_info(file)
        name=uuid4().hex+'_'+name
        file.save(Path(app.config['UPLOAD_FOLDER'])/name)
        return name,width,height

    def file_visible(item):
        if item['visibility']!='public':return False
        if item['album_id']:
            album=db().execute('SELECT visibility FROM albums WHERE id=?',(item['album_id'],)).fetchone()
            if not album or album['visibility']!='public':return False
        if item['record_id']:
            record=services['get_record'](item['record_id']);d=record['d']
            if d.get('visibility')!='public':return False
            if record['module'] in ['posts','gallery'] and (d.get('status')!='Publicado' or (record['module']=='posts' and d.get('date','')>now())):return False
        return True

    def public_files(scope=None,album=None):
        rows=db().execute('SELECT m.*,u.name uploader,gr.name church_name,a.title album_title FROM media_files m JOIN users u ON u.id=m.uploaded_by JOIN groups gr ON gr.id=m.group_id LEFT JOIN albums a ON a.id=m.album_id ORDER BY m.created DESC,m.id DESC').fetchall()
        return [dict(r) for r in rows if (scope is None or r['group_id']==scope) and (album is None or r['album_id']==album) and file_visible(r)]

    def public_albums(scope):
        output=[]
        for row in db().execute('SELECT a.*,gr.name group_name FROM albums a JOIN groups gr ON gr.id=a.group_id WHERE a.group_id=? AND a.visibility=\'public\' ORDER BY a.id DESC',(scope,)):
            item=dict(row); photos=public_files(album=row['id']);item['photos']=photos;item['cover']=photos[0] if photos else None;output.append(item)
        return output

    def leaders(scope):
        return [dict(r) for r in db().execute('SELECT a.role,u.id user_id,u.name,p.message,p.phone,p.photo,p.featured FROM assignments a JOIN users u ON u.id=a.user_id JOIN leader_profiles p ON p.user_id=u.id AND p.group_id=a.group_id WHERE a.group_id=? AND a.active=1 AND u.active=1 AND p.published=1 ORDER BY a.id',(scope,))]

    def messages(scope):
        return db().execute('SELECT m.*,u.name,gr.name group_name FROM community_messages m JOIN users u ON u.id=m.user_id JOIN groups gr ON gr.id=m.group_id JOIN memberships ms ON ms.user_id=u.id AND ms.status=\'Aprobado\' WHERE m.status=\'Aprobado\' AND u.active=1 AND (?=1 OR m.group_id=?) ORDER BY m.id DESC LIMIT 12',(scope,scope)).fetchall()

    def public_context(scope):
        people=leaders(scope);ranking={'Presidente':0,'Vicepresidente':1,'Secretario':2,'Prosecretario':3,'Tesorero':4,'Protesorero':5,'Vocal':6}
        return dict(hero_files=public_files(scope)[:8],albums=public_albums(scope),testimonials=messages(scope),main_leaders=sorted([p for p in people if p['role'] in ranking],key=lambda p:ranking[p['role']]),other_leaders=sorted([p for p in people if p['role'] not in ranking],key=lambda p:not p['featured']),verse=daily_verse())

    @bp.get('/archivos/<int:file_id>')
    def asset(file_id):
        item=db().execute('SELECT * FROM media_files WHERE id=?',(file_id,)).fetchone()
        if not item:abort(404)
        if not file_visible(item) and not (g.user and (item['uploaded_by']==g.user['id'] or allowed(item['group_id'],'gallery'))):abort(403)
        base=Path(app.static_folder) if item['static_name'] else Path(app.config['UPLOAD_FOLDER'])
        return send_file(base/(item['static_name'] or item['filename']))

    @bp.get('/album/<int:album_id>')
    def album(album_id):
        item=db().execute('SELECT a.*,gr.name group_name FROM albums a JOIN groups gr ON gr.id=a.group_id WHERE a.id=?',(album_id,)).fetchone()
        if not item:abort(404)
        if item['visibility']!='public' and not allowed(item['group_id'],'gallery'):abort(403)
        photos=public_files(album=album_id)
        if item['visibility']!='public':
            photos=[dict(r) for r in db().execute('SELECT m.*,u.name uploader,gr.name church_name,a.title album_title FROM media_files m JOIN users u ON u.id=m.uploaded_by JOIN groups gr ON gr.id=m.group_id JOIN albums a ON a.id=m.album_id WHERE m.album_id=?',(album_id,))]
        return render_template('album.html',album=item,photos=photos,public_page=True,uploadable=is_leader() and (item['group_id']==1 or allowed(item['group_id'],'events')))

    @bp.route('/panel/archivos',methods=['GET','POST'])
    @logged
    def files():
        if not is_leader():abort(403)
        scopes=[dict(r) for r in db().execute('SELECT * FROM groups WHERE active=1') if allowed(r['id'],'events')]
        all_albums=[dict(r) for r in db().execute('SELECT * FROM albums ORDER BY id DESC') if (r['group_id']==1 and (r['visibility']=='public' or allowed(1,'events'))) or allowed(r['group_id'],'events')]
        if request.method=='POST':
            try:
                action=request.form['action'];gid=int(request.form.get('group_id','0'))
                if gid not in [r['id'] for r in scopes]:abort(403)
                if action=='album':
                    if not allowed(gid,'gallery',True):abort(403)
                    title=request.form.get('title','').strip(); visibility=request.form.get('visibility','public')
                    if not title or len(title)>160 or visibility not in ['public','internal']:raise ValueError('Revisa el título y visibilidad.')
                    db().execute('INSERT INTO albums(group_id,title,description,visibility,created_by,created) VALUES(?,?,?,?,?,?)',(gid,title,request.form.get('description','')[:3000],visibility,g.user['id'],now()))
                    audit('Creó álbum: '+title,gid)
                elif action=='upload':
                    kind=request.form.get('kind');aid=request.form.get('album_id',type=int);title=request.form.get('title','').strip();visibility=request.form.get('visibility','public')
                    if kind not in ['Afiche','Fotografía'] or not title or len(title)>160 or visibility not in ['public','internal']:raise ValueError('Completa el título, tipo y visibilidad.')
                    if aid:
                        album=db().execute('SELECT * FROM albums WHERE id=?',(aid,)).fetchone()
                        if not album or not any(a['id']==aid for a in all_albums):abort(403)
                        if kind!='Fotografía':raise ValueError('Los álbumes contienen fotografías. Publica afiches sin álbum.')
                    files=request.files.getlist('photos')
                    if not files or not any(f.filename for f in files):raise ValueError('Selecciona al menos una imagen.')
                    if len(files)>20:raise ValueError('Máximo 20 imágenes por carga.')
                    # Valida todos los archivos antes de escribir el lote.
                    for file in files:
                        name=secure_filename(file.filename or '')
                        if name.rsplit('.',1)[-1].lower() not in ['png','jpg','jpeg']:raise ValueError('Usa PNG o JPG.')
                        picture_info(file)
                    for i,file in enumerate(files):
                        filename,width,height=save_image(file)
                        db().execute('INSERT INTO media_files(group_id,album_id,title,kind,filename,width,height,uploaded_by,visibility,created) VALUES(?,?,?,?,?,?,?,?,?,?)',(gid,aid,title+(f' · {i+1}' if len(files)>1 else ''),kind,filename,width,height,g.user['id'],visibility,now()))
                    audit(f'Subió {len(files)} archivo(s): {title}',gid)
                elif action=='visibility':
                    item=db().execute('SELECT * FROM media_files WHERE id=?',(request.form.get('id',type=int),)).fetchone()
                    if not item or item['group_id']!=gid:abort(404)
                    if item['uploaded_by']!=g.user['id'] and not allowed(gid,'gallery',True):abort(403)
                    db().execute('UPDATE media_files SET visibility=CASE visibility WHEN \'public\' THEN \'internal\' ELSE \'public\' END WHERE id=?',(item['id'],))
                    audit('Cambió visibilidad de archivo #'+str(item['id']),gid)
                else:abort(400)
                db().commit();flash('Cambios guardados.','success');return redirect(url_for('community.files'))
            except (ValueError,KeyError) as exc:
                db().rollback();flash(str(exc),'error')
        items=[dict(r) for r in db().execute('SELECT m.*,u.name uploader,gr.name church_name,a.title album_title FROM media_files m JOIN users u ON u.id=m.uploaded_by JOIN groups gr ON gr.id=m.group_id LEFT JOIN albums a ON a.id=m.album_id ORDER BY m.id DESC') if allowed(r['group_id'],'events') or (r['album_id'] and file_visible(r) and any(a['id']==r['album_id'] and a['group_id']==1 for a in all_albums))]
        return render_template('files.html',items=items,scopes=scopes,all_albums=all_albums)

    @bp.route('/solicitar-registro',methods=['GET','POST'])
    def join():
        submitted=False
        if request.method=='POST':
            try:
                name=request.form.get('name','').strip();email=request.form.get('email','').strip().lower();password=request.form.get('password','');gid=request.form.get('group_id',type=int)
                if not name or len(name)>120 or len(password)<12 or len(password)>200 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email):raise ValueError('Revisa el nombre, correo y contraseña de al menos 12 caracteres.')
                group=db().execute('SELECT * FROM groups WHERE id=? AND active=1 AND kind IN (\'SEC\',\'GJ\')',(gid,)).fetchone()
                if not group:raise ValueError('Selecciona tu SEC o GJ.')
                uid=db().execute('INSERT INTO users(name,email,password,active) VALUES(?,?,?,0)',(name,email,generate_password_hash(password))).lastrowid
                db().execute('INSERT INTO memberships(user_id,group_id,created) VALUES(?,?,?)',(uid,gid,now()));db().commit();submitted=True
            except sqlite3.IntegrityError:
                db().rollback();flash('Ya existe una solicitud o cuenta con ese correo. Consulta a tus líderes.','error')
            except ValueError as exc:flash(str(exc),'error')
        return render_template('join.html',public_page=True,submitted=submitted)

    @bp.route('/mi-comunidad',methods=['GET','POST'])
    @logged
    def member_home():
        member=db().execute('SELECT ms.*,gr.name group_name FROM memberships ms JOIN groups gr ON gr.id=ms.group_id WHERE ms.user_id=? AND ms.status=\'Aprobado\'',(g.user['id'],)).fetchone()
        if not member:abort(403)
        if request.method=='POST':
            body=request.form.get('body','').strip()
            if not 10<=len(body)<=600:flash('Escribe un mensaje de 10 a 600 caracteres.','error')
            elif db().execute('SELECT count(*) FROM community_messages WHERE user_id=? AND status=\'Pendiente\'',(g.user['id'],)).fetchone()[0]>=3:flash('Ya tienes tres mensajes pendientes de revisión.','error')
            else:
                db().execute('INSERT INTO community_messages(user_id,group_id,body,created) VALUES(?,?,?,?)',(g.user['id'],member['group_id'],body,now()));audit('Envió mensaje para moderación',member['group_id']);db().commit();flash('Tu mensaje está pendiente de aprobación.','success');return redirect(url_for('community.member_home'))
        messages=db().execute('SELECT * FROM community_messages WHERE user_id=? ORDER BY id DESC',(g.user['id'],)).fetchall()
        return render_template('member_home.html',member=member,messages=messages,public_page=True)

    @bp.route('/panel/aprobaciones',methods=['GET','POST'])
    @logged
    def approvals():
        if not is_leader():abort(403)
        if request.method=='POST':
            action=request.form.get('action');decision=request.form.get('decision');item_id=request.form.get('id',type=int)
            if action not in ['membership','message'] or decision not in ['Aprobado','Rechazado']:abort(400)
            table='memberships' if action=='membership' else 'community_messages'
            item=db().execute(f'SELECT * FROM {table} WHERE id=?',(item_id,)).fetchone()
            if not item:abort(404)
            if not can_review(item['group_id']):abort(403)
            db().execute(f'UPDATE {table} SET status=?,reviewed_by=?,reviewed=? WHERE id=?',(decision,g.user['id'],now(),item_id))
            if action=='membership':
                # Solo activa cuentas creadas para miembros. Nunca concede cargos.
                db().execute('UPDATE users SET active=? WHERE id=?',(int(decision=='Aprobado'),item['user_id']))
            audit(f'{decision}: {action} #{item_id}',item['group_id']);db().commit();flash('Revisión guardada.','success');return redirect(url_for('community.approvals'))
        applications=[r for r in db().execute('SELECT ms.*,u.name,u.email,gr.name group_name FROM memberships ms JOIN users u ON u.id=ms.user_id JOIN groups gr ON gr.id=ms.group_id ORDER BY ms.id DESC') if can_review(r['group_id'])]
        messages=[r for r in db().execute('SELECT m.*,u.name,gr.name group_name FROM community_messages m JOIN users u ON u.id=m.user_id JOIN groups gr ON gr.id=m.group_id ORDER BY m.id DESC') if can_review(r['group_id'])]
        return render_template('approvals.html',applications=applications,messages=messages)

    @bp.route('/panel/identidad',methods=['GET','POST'])
    @logged
    def identity():
        if not is_leader():abort(403)
        scopes=[dict(r) for r in db().execute('SELECT * FROM groups') if can_review(r['id'])]
        if request.method=='POST':
            gid=request.form.get('group_id',type=int)
            if gid not in [r['id'] for r in scopes] or not can_review(gid):abort(403)
            try:
                color=request.form.get('color','');maps=request.form.get('maps_url','').strip()
                if not re.fullmatch('#[0-9a-fA-F]{6}',color):raise ValueError('Color inválido.')
                if maps:
                    parsed=urlsplit(maps)
                    if parsed.scheme!='https' or parsed.hostname not in ['www.google.com','google.com','maps.google.com','maps.app.goo.gl','goo.gl'] or parsed.username:raise ValueError('Usa un enlace HTTPS de Google Maps.')
                photo=None;file=request.files.get('photo')
                if file and file.filename:photo,_,_=save_image(file)
                db().execute('UPDATE groups SET color=?,description=?,church=?,address=?,maps_url=?,schedule=? WHERE id=?',(color,request.form.get('description','')[:2000],request.form.get('church','')[:200],request.form.get('address','')[:500],maps,request.form.get('schedule','')[:500],gid))
                if photo:db().execute('UPDATE groups SET photo=? WHERE id=?',(photo,gid))
                audit('Actualizó identidad pública y local',gid);db().commit();flash('Identidad actualizada.','success');return redirect(url_for('community.identity'))
            except ValueError as exc:flash(str(exc),'error')
        return render_template('identity.html',scopes=scopes)

    @bp.get('/iglesia/<int:group_id>/foto')
    def church_photo(group_id):
        group=db().execute('SELECT * FROM groups WHERE id=? AND active=1',(group_id,)).fetchone()
        if not group:abort(404)
        if group['photo']:return send_file(Path(app.config['UPLOAD_FOLDER'])/group['photo'])
        if 'jerusal' in group['name'].lower():return send_file(Path(app.static_folder)/'images/jerusalen.jpg')
        if group_id==1:return send_file(Path(app.static_folder)/'images/depec-logo.jpg')
        return send_file(Path(app.static_folder)/'images/church-placeholder.svg',mimetype='image/svg+xml')

    @bp.route('/panel/directiva',methods=['GET','POST'])
    @logged
    def profiles():
        if not is_leader():abort(403)
        assignments=[r for r in db().execute('SELECT a.*,u.name,gr.name group_name FROM assignments a JOIN users u ON u.id=a.user_id JOIN groups gr ON gr.id=a.group_id WHERE a.active=1') if r['user_id']==g.user['id'] or can_review(r['group_id'])]
        if request.method=='POST':
            uid=request.form.get('user_id',type=int);gid=request.form.get('group_id',type=int)
            if not any(a['user_id']==uid and a['group_id']==gid for a in assignments):abort(403)
            try:
                phone=re.sub(r'[\s()-]','',request.form.get('phone',''))
                if phone and not re.fullmatch(r'\+?[0-9]{6,16}',phone):raise ValueError('Teléfono inválido.')
                old=db().execute('SELECT photo FROM leader_profiles WHERE user_id=? AND group_id=?',(uid,gid)).fetchone();photo=old['photo'] if old else ''
                file=request.files.get('photo')
                if file and file.filename:photo,_,_=save_image(file)
                db().execute('INSERT INTO leader_profiles(user_id,group_id,message,phone,photo,published,featured) VALUES(?,?,?,?,?,?,?) ON CONFLICT(user_id,group_id) DO UPDATE SET message=excluded.message,phone=excluded.phone,photo=excluded.photo,published=excluded.published,featured=excluded.featured',(uid,gid,request.form.get('message','')[:600],phone,photo,int(request.form.get('published')=='1'),int(request.form.get('featured')=='1')))
                audit('Actualizó perfil público de directiva',gid);db().commit();flash('Perfil guardado. Solo se publica si marcas la autorización.','success');return redirect(url_for('community.profiles'))
            except ValueError as exc:flash(str(exc),'error')
        profiles={(r['user_id'],r['group_id']):dict(r) for r in db().execute('SELECT * FROM leader_profiles')}
        return render_template('profiles.html',assignments=assignments,profiles=profiles)

    @bp.get('/directiva/<int:user_id>/<int:group_id>/foto')
    def leader_photo(user_id,group_id):
        profile=db().execute('SELECT p.* FROM leader_profiles p WHERE p.user_id=? AND p.group_id=?',(user_id,group_id)).fetchone()
        if not profile or not profile['photo']:abort(404)
        visible=profile['published'] and db().execute('SELECT 1 FROM assignments a JOIN users u ON u.id=a.user_id WHERE a.user_id=? AND a.group_id=? AND a.active=1 AND u.active=1',(user_id,group_id)).fetchone()
        if not visible and not (g.user and (g.user['id']==user_id or can_review(group_id))):abort(403)
        return send_file(Path(app.config['UPLOAD_FOLDER'])/profile['photo'])

    app.register_blueprint(bp)
    return dict(public_context=public_context,is_leader=is_leader,can_review=can_review)
