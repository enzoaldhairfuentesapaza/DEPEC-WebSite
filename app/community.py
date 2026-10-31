"""Álbumes, archivos, perfiles y membresía aprobada. Permisos siempre en servidor."""
import re
import json
import math
import unicodedata
from datetime import date
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4
from flask import Blueprint, abort, flash, g, redirect, render_template, request, send_file, url_for
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from .community_data import daily_verse, picture_info, group_verse, anniversary, local_now, normalize_map_embed, local_map
from .retro import register_retro
from .announcements import active_announcements
from .community_data import LIMA


def register_community(app, services):
    bp=Blueprint('community',__name__)
    db,allowed,logged,audit,now,roles_for=[services[k] for k in ['db','allowed','logged','audit','now','roles_for']]

    def is_leader():
        return bool(g.user and (g.user['admin'] or db().execute('SELECT 1 FROM assignments WHERE user_id=? AND active=1',(g.user['id'],)).fetchone()))

    def can_review(gid):
        return bool(g.user and (g.user['admin'] or {'Presidente','Vicepresidente','Secretario','Prosecretario','Líder'} & roles_for(gid)))

    def can_manage_palette():
        return bool(g.user and (g.user['admin'] or roles_for(1)))

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
            if record['module']=='events' and not services['event_access'](record,public=True):return False
            if record['module']=='events' and d.get('image_mode') in ['Sin imagen','Imagen genérica']:return False
            if record['module'] in ['posts','gallery'] and (d.get('status')!='Publicado' or (record['module']=='posts' and d.get('date','')>now())):return False
        return True

    def public_files(scope=None,album=None,limit=None):
        where=[];parameters=[]
        if scope is not None:where.append('m.group_id=?');parameters.append(scope)
        if album is not None:where.append('m.album_id=?');parameters.append(album)
        rows=db().execute('SELECT m.*,u.name uploader,gr.name church_name,a.title album_title FROM media_files m JOIN users u ON u.id=m.uploaded_by JOIN groups gr ON gr.id=m.group_id LEFT JOIN albums a ON a.id=m.album_id'+(' WHERE '+' AND '.join(where) if where else '')+' ORDER BY m.created DESC,m.id DESC',parameters)
        output=[]
        for row in rows:
            if file_visible(row):
                output.append(dict(row))
                if limit is not None and len(output)>=limit:break
        return output

    def album_cards(scope,query='',page=1,per_page=12):
        def fold(value):
            return ''.join(ch for ch in unicodedata.normalize('NFKD',str(value).casefold()) if not unicodedata.combining(ch))
        db().create_function('fold_text',1,fold,deterministic=True)
        search=fold(query).replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
        where="a.group_id=? AND a.visibility='public' AND gr.active=1 AND fold_text(a.title||' '||a.description) LIKE ? ESCAPE '\\'"
        parameters=(scope,'%'+search+'%')
        total=db().execute('SELECT count(*) FROM albums a JOIN groups gr ON gr.id=a.group_id WHERE '+where,parameters).fetchone()[0]
        pages=max(1,math.ceil(total/per_page))
        if page<1 or page>pages:abort(404)
        rows=db().execute('SELECT a.*,gr.name group_name FROM albums a JOIN groups gr ON gr.id=a.group_id WHERE '+where+' ORDER BY a.id DESC LIMIT ? OFFSET ?',(*parameters,per_page,(page-1)*per_page)).fetchall()
        # Cuenta/portada sin cargar todas las fotografías de todos los álbumes.
        visible="""m.album_id=? AND m.visibility='public' AND
            (m.record_id IS NULL OR (r.id IS NOT NULL AND json_extract(r.data,'$.visibility')='public'
            AND (r.module!='events' OR coalesce(json_extract(r.data,'$.image_mode'),'') NOT IN ('Sin imagen','Imagen genérica'))
            AND (r.module NOT IN ('posts','gallery') OR json_extract(r.data,'$.status')='Publicado')
            AND (r.module!='posts' OR coalesce(json_extract(r.data,'$.date'),'')<=?)))"""
        output=[]
        for row in rows:
            item=dict(row);args=(row['id'],now())
            item['photo_count']=db().execute('SELECT count(*) FROM media_files m LEFT JOIN records r ON r.id=m.record_id WHERE '+visible,args).fetchone()[0]
            cover=db().execute('SELECT m.id,m.title FROM media_files m LEFT JOIN records r ON r.id=m.record_id WHERE '+visible+' ORDER BY m.created DESC,m.id DESC LIMIT 1',args).fetchone()
            item['cover']=dict(cover) if cover else None;output.append(item)
        return dict(albums=output,total=total,page=page,pages=pages)

    def leaders(scope):
        return [dict(r) for r in db().execute('SELECT a.role,u.id user_id,u.name,p.message,p.phone,p.photo,p.featured FROM assignments a JOIN users u ON u.id=a.user_id JOIN leader_profiles p ON p.user_id=u.id AND p.group_id=a.group_id WHERE a.group_id=? AND a.active=1 AND u.active=1 AND p.published=1 ORDER BY a.id',(scope,))]

    def messages(scope):
        return db().execute('SELECT m.*,u.name,gr.name group_name,gr.color FROM community_messages m JOIN users u ON u.id=m.user_id JOIN groups gr ON gr.id=m.group_id JOIN memberships ms ON ms.user_id=u.id AND ms.status=\'Aprobado\' WHERE m.status=\'Aprobado\' AND u.active=1 AND (?=1 OR m.group_id=?) ORDER BY m.id DESC LIMIT 12',(scope,scope)).fetchall()

    def public_context(scope):
        people=leaders(scope);ranking={'Presidente':0,'Vicepresidente':1,'Secretario':2,'Prosecretario':3,'Tesorero':4,'Protesorero':5,'Vocal':6}
        group=db().execute('SELECT * FROM groups WHERE id=?',(scope,)).fetchone()
        return dict(announcements=active_announcements(db(),scope),announcements_now_ms=int(local_now().replace(tzinfo=LIMA).timestamp()*1000),page_settings=group,local_map=local_map(group) if group['kind']!='DEPEC' else None,birthday_people=[p for p in retro['public_birthdays'](scope) if p['month']==local_now().month],page_members=retro['public_members'](scope) if scope!=1 else [],anniversary_info=anniversary(group),hero_files=public_files(scope,limit=8),albums=album_cards(scope,per_page=3)['albums'],testimonials=messages(scope),main_leaders=sorted([p for p in people if p['role'] in ranking],key=lambda p:ranking[p['role']]),other_leaders=sorted([p for p in people if p['role'] not in ranking],key=lambda p:not p['featured']),verse=group_verse(group))

    @bp.get('/albumes')
    def albums_directory():
        scope=request.args.get('group',1,type=int)
        group=db().execute('SELECT * FROM groups WHERE id=? AND active=1',(scope,)).fetchone()
        if not group:abort(404)
        query=request.args.get('q','').strip()
        try:page=int(request.args.get('page','1'))
        except ValueError:abort(400)
        if len(query)>120 or page<1:abort(400)
        result=album_cards(scope,query,page)
        return render_template('albums_directory.html',public_page=True,selected=group,query=query,**result)

    @bp.route('/panel/colores',methods=['GET','POST'])
    @logged
    def palette():
        if not can_manage_palette():abort(403)
        if request.method=='POST':
            gid=request.form.get('group_id',type=int);color=request.form.get('color','')
            group=db().execute('SELECT * FROM groups WHERE id=? AND active=1',(gid,)).fetchone()
            if not group:abort(404)
            if not re.fullmatch('#[0-9a-fA-F]{6}',color):
                flash('Selecciona un color válido.','error')
            else:
                db().execute('UPDATE groups SET color=? WHERE id=?',(color,gid))
                audit('Actualizó color de '+group['name'],gid);db().commit()
                flash('Color actualizado en la página, eventos, calendario y contacto.','success')
                return redirect(url_for('community.palette'))
        return render_template('palette.html',organizations=db().execute('SELECT * FROM groups WHERE active=1 ORDER BY id').fetchall())

    @bp.get('/archivos/<int:file_id>')
    def asset(file_id):
        item=db().execute('SELECT * FROM media_files WHERE id=?',(file_id,)).fetchone()
        if not item:abort(404)
        event_permission=False
        if item['record_id']:
            record=services['get_record'](item['record_id'])
            if record['module']=='events':
                if not services['event_access'](record):abort(403)
                event_permission=record['d'].get('image_mode') not in ['Sin imagen','Imagen genérica'] and (item['visibility']=='public' or bool(g.user and record['d'].get('visibility')=='internal'))
        if not event_permission and not file_visible(item) and not (g.user and (item['uploaded_by']==g.user['id'] or allowed(item['group_id'],'gallery'))):abort(403)
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
        scopes=[dict(r) for r in db().execute('SELECT * FROM groups WHERE active=1') if allowed(r['id'],'gallery')]
        all_albums=[dict(r) for r in db().execute('SELECT * FROM albums ORDER BY id DESC') if (r['group_id']==1 and (r['visibility']=='public' or allowed(1,'gallery'))) or allowed(r['group_id'],'gallery')]
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
        items=[dict(r) for r in db().execute('SELECT m.*,u.name uploader,gr.name church_name,a.title album_title FROM media_files m JOIN users u ON u.id=m.uploaded_by JOIN groups gr ON gr.id=m.group_id LEFT JOIN albums a ON a.id=m.album_id ORDER BY m.id DESC') if allowed(r['group_id'],'gallery') or (r['album_id'] and file_visible(r) and any(a['id']==r['album_id'] and a['group_id']==1 for a in all_albums))]
        return render_template('files.html',items=items,scopes=scopes,all_albums=all_albums)

    @bp.route('/solicitar-registro',methods=['GET','POST'])
    def join():
        return app.extensions['member_registry']['editor'](join=True)

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
            if action not in ['membership','message','profile'] or decision not in ['Aprobado','Rechazado']:abort(400)
            table='memberships' if action=='membership' else 'member_profiles' if action=='profile' else 'community_messages'
            key='user_id' if action=='profile' else 'id'
            item=db().execute('SELECT p.*,ms.group_id FROM member_profiles p JOIN memberships ms ON ms.user_id=p.user_id WHERE p.user_id=?',(item_id,)).fetchone() if action=='profile' else db().execute(f'SELECT * FROM {table} WHERE id=?',(item_id,)).fetchone()
            if not item:abort(404)
            if not can_review(item['group_id']):abort(403)
            db().execute(f'UPDATE {table} SET status=?,reviewed_by=?,reviewed=? WHERE {key}=?',(decision,g.user['id'],now(),item_id))
            if action=='membership':
                # Solo activa cuentas creadas para miembros. Nunca concede cargos.
                db().execute('UPDATE users SET active=? WHERE id=?',(int(decision=='Aprobado'),item['user_id']))
            audit(f'{decision}: {action} #{item_id}',item['group_id']);db().commit();flash('Revisión guardada.','success');return redirect(url_for('community.approvals'))
        applications=[r for r in db().execute('SELECT ms.*,u.name,u.email,gr.name group_name FROM memberships ms JOIN users u ON u.id=ms.user_id JOIN groups gr ON gr.id=ms.group_id ORDER BY ms.id DESC') if can_review(r['group_id'])]
        messages=[r for r in db().execute('SELECT m.*,u.name,gr.name group_name,gr.color FROM community_messages m JOIN users u ON u.id=m.user_id JOIN groups gr ON gr.id=m.group_id ORDER BY m.id DESC') if can_review(r['group_id'])]
        profiles=[r for r in db().execute('SELECT p.*,p.user_id id,u.name,ms.group_id,gr.name group_name FROM member_profiles p JOIN users u ON u.id=p.user_id JOIN memberships ms ON ms.user_id=p.user_id JOIN groups gr ON gr.id=ms.group_id ORDER BY p.updated DESC') if can_review(r['group_id'])]
        return render_template('approvals.html',applications=applications,messages=messages,profile_reviews=profiles)

    @bp.route('/panel/contacto',methods=['GET','POST'])
    @logged
    def contact():
        from .contact import contact_settings,validate_contact
        scopes=[dict(r) for r in db().execute('SELECT * FROM groups WHERE active=1') if can_review(r['id'])]
        if not scopes:abort(403)
        gid=request.form.get('group_id',type=int) if request.method=='POST' else request.args.get('group',type=int)
        if gid is None and request.method=='GET':gid=scopes[0]['id']
        group=next((gr for gr in scopes if gr['id']==gid),None)
        if not group:abort(403)
        settings=contact_settings(group)
        if request.method=='POST':
            try:
                settings=validate_contact(request.form)
                db().execute('UPDATE groups SET contact_settings=? WHERE id=?',(json.dumps(settings),gid))
                audit('Actualizó burbuja de contacto pública',gid);db().commit()
                flash('Contacto actualizado. Los cambios ya aparecen en la página de esta organización.','success')
                return redirect(url_for('community.contact',group=gid))
            except ValueError as exc:
                settings={**settings,**{key:request.form.get(key,'') for key in settings}}
                settings['enabled']=request.form.get('enabled')=='1'
                flash(str(exc),'error')
        return render_template('contact.html',scopes=scopes,selected=group,settings=settings)

    @bp.route('/panel/identidad',methods=['GET','POST'])
    @logged
    def identity():
        if not is_leader():abort(403)
        scopes=[dict(r) for r in db().execute('SELECT * FROM groups') if can_review(r['id'])]
        if request.method=='POST':
            gid=request.form.get('group_id',type=int)
            if gid not in [r['id'] for r in scopes] or not can_review(gid):abort(403)
            try:
                color=request.form.get('color','') if can_manage_palette() else next(gr['color'] for gr in scopes if gr['id']==gid);maps=request.form.get('maps_url','').strip()
                if not re.fullmatch('#[0-9a-fA-F]{6}',color):raise ValueError('Color inválido.')
                if db().execute('SELECT kind FROM groups WHERE id=?',(gid,)).fetchone()[0]=='DEPEC':maps=''
                if maps:
                    parsed=urlsplit(maps)
                    if parsed.scheme!='https' or parsed.hostname not in ['www.google.com','google.com','maps.google.com','maps.app.goo.gl','goo.gl'] or parsed.username:raise ValueError('Usa un enlace HTTPS de Google Maps.')
                existing=db().execute('SELECT * FROM groups WHERE id=?',(gid,)).fetchone()
                embed=normalize_map_embed(request.form.get('maps_embed_url',existing['maps_embed_url']))
                hero_title=request.form.get('hero_title',existing['hero_title']).strip()
                hero_description=request.form.get('hero_description',existing['hero_description']).strip()
                mode=request.form.get('verse_mode',existing['verse_mode'])
                if mode not in ['daily','custom','off']:raise ValueError('Modo de versículo inválido.')
                verses=json.loads(existing['custom_verses'])
                if 'verse_lines' in request.form:
                    verses=[]
                    for line in request.form['verse_lines'].splitlines():
                        if not line.strip():continue
                        parts=line.split('|',1)
                        if len(parts)!=2 or not all(p.strip() for p in parts):raise ValueError('Escribe cada versículo como Referencia | Texto.')
                        if len(parts[0])>100 or len(parts[1])>1000:raise ValueError('Versículo demasiado largo.')
                        verses.append(dict(reference=parts[0].strip(),text=parts[1].strip(),version='Texto de la comunidad'))
                if mode=='custom' and not verses:raise ValueError('Añade al menos un versículo para la lista propia.')
                if len(verses)>50 or len(hero_title)>180 or len(hero_description)>1500:raise ValueError('Revisa el tamaño del título, descripción y lista de versículos.')
                founded=request.form.get('founded_date',existing['founded_date'])
                if founded and date.fromisoformat(founded)>local_now().date():raise ValueError('La fecha de fundación no puede ser futura.')
                db().execute('UPDATE groups SET hero_title=?,hero_description=?,verse_mode=?,custom_verses=?,founded_date=?,anniversary_note=? WHERE id=?',(hero_title,hero_description,mode,json.dumps(verses),founded,request.form.get('anniversary_note',existing['anniversary_note'])[:250],gid))
                photo=None;file=request.files.get('photo')
                if file and file.filename:photo,_,_=save_image(file)
                db().execute('UPDATE groups SET color=?,description=?,church=?,address=?,maps_url=?,schedule=? WHERE id=?',(color,request.form.get('description','')[:2000],request.form.get('church','')[:200],request.form.get('address','')[:500],maps,request.form.get('schedule','')[:500],gid))
                if existing['kind']=='DEPEC':
                    db().execute("UPDATE groups SET church='',address='',schedule='',maps_url='',maps_embed_url='' WHERE id=?",(gid,))
                else:db().execute('UPDATE groups SET maps_embed_url=? WHERE id=?',(embed,gid))
                if photo:db().execute('UPDATE groups SET photo=? WHERE id=?',(photo,gid))
                audit('Actualizó identidad pública y local',gid);db().commit();flash('Identidad actualizada.','success');return redirect(url_for('community.identity'))
            except ValueError as exc:flash(str(exc),'error')
        return render_template('identity.html',scopes=scopes)

    @bp.post('/panel/identidad/resolver-mapa')
    @logged
    def resolve_location():
        gid=request.form.get('group_id',type=int)
        if not can_review(gid):abort(403)
        group=db().execute('SELECT * FROM groups WHERE id=?',(gid,)).fetchone()
        if not group or group['kind']=='DEPEC':abort(400)
        from .map_locations import resolve_map_embed
        try:
            embed=resolve_map_embed(group['maps_url'])
            db().execute('UPDATE groups SET maps_embed_url=? WHERE id=?',(embed,gid))
            audit('Actualizó mapa desde enlace de Google Maps',gid);db().commit()
            flash('Mapa actualizado con las coordenadas del enlace.','success')
        except Exception:
            flash('No pudimos obtener las coordenadas. Tu enlace se conserva; puedes pegar el código de Compartir → Insertar un mapa.','error')
        return redirect(url_for('community.identity'))

    @bp.get('/iglesia/<int:group_id>/foto')
    def church_photo(group_id):
        group=db().execute('SELECT * FROM groups WHERE id=? AND active=1',(group_id,)).fetchone()
        if not group:abort(404)
        if group['photo']:return send_file(Path(app.config['UPLOAD_FOLDER'])/group['photo'])
        if 'jerusal' in group['name'].lower():return send_file(Path(app.static_folder)/'images/jerusalen.jpg')
        if 'jorge' in group['name'].lower():return send_file(Path(app.static_folder)/'images/jorge-chavez.jpg')
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
        if profile['photo'].startswith('demo:'):return send_file(Path(app.static_folder)/profile['photo'][5:])
        return send_file(Path(app.config['UPLOAD_FOLDER'])/profile['photo'])

    retro=register_retro(app,dict(db=db,logged=logged,audit=audit,now=now,save_image=save_image,can_review=can_review))
    app.register_blueprint(bp)
    return dict(public_context=public_context,is_leader=is_leader,can_review=can_review,can_manage_palette=can_manage_palette)
