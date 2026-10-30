"""Perfiles públicos voluntarios de miembros y utilidades retro."""
from flask import Blueprint, abort, flash, g, redirect, render_template, request, send_file, url_for
from pathlib import Path
from datetime import date
from .birthday_calendar import birthday_calendar
from .community_data import local_now

AVATARS={'luz':'Luz','paloma':'Paloma','biblia':'Biblia','pez':'Pez','cruz':'Cruz'}

def register_retro(app,services):
    bp=Blueprint('retro',__name__)
    db,logged,audit,now=[services[k] for k in ['db','logged','audit','now']]

    def public_members(scope):
        return [dict(r) for r in db().execute("SELECT p.*,u.name,gr.name group_name,ms.group_id FROM member_profiles p JOIN users u ON u.id=p.user_id JOIN memberships ms ON ms.user_id=u.id JOIN groups gr ON gr.id=ms.group_id WHERE p.published=1 AND p.status='Aprobado' AND ms.status='Aprobado' AND u.active=1 AND (?=1 OR ms.group_id=?) ORDER BY u.name",(scope,scope))]

    def public_birthdays(scope):
        output=[]
        for person in public_members(scope):
            if not person['birthday_public'] or not person['birthday_md']:continue
            try:born=date.fromisoformat('2000-'+person['birthday_md'])
            except ValueError:continue
            group=db().execute('SELECT color,active FROM groups WHERE id=?',(person['group_id'],)).fetchone()
            if not group or not group['active']:continue
            output.append(dict(id=person['user_id'],name=person['name'],group_name=person['group_name'],color=group['color'],month=born.month,day=born.day,demo=bool(person['demo'])))
        return output

    @bp.get('/cumpleanos')
    def public_birthday_calendar():
        scope=request.args.get('group',type=int) or 1
        if not db().execute('SELECT 1 FROM groups WHERE id=? AND active=1',(scope,)).fetchone():abort(404)
        try:context=birthday_calendar(public_birthdays(scope),request.args.get('month'))
        except (ValueError,OverflowError):abort(400)
        return render_template('birthdays.html',public_page=True,**context)

    @bp.route('/mi-perfil',methods=['GET','POST'])
    @logged
    def member_profile():
        member=db().execute("SELECT ms.*,gr.name group_name FROM memberships ms JOIN groups gr ON gr.id=ms.group_id WHERE ms.user_id=? AND ms.status='Aprobado'",(g.user['id'],)).fetchone()
        if not member:abort(403)
        old=db().execute('SELECT * FROM member_profiles WHERE user_id=?',(g.user['id'],)).fetchone()
        profile=dict(old) if old else {}
        if request.method=='POST':
            try:
                avatar=request.form.get('avatar','luz')
                if avatar not in AVATARS:raise ValueError('Selecciona uno de los avatares disponibles.')
                fields={key:request.form.get(key,'').strip() for key in ['message','verse_ref','verse_text','likes','gifts','dislikes']}
                if any(len(v)>600 for v in fields.values()):raise ValueError('Cada campo admite hasta 600 caracteres.')
                month=request.form.get('birthday_month','').strip();day=request.form.get('birthday_day','').strip()
                birthday_public=int(request.form.get('birthday_public')=='1')
                birthday_md=''
                if month or day:
                    birthday=date(2000,int(month),int(day))
                    birthday_md=birthday.strftime('%m-%d')
                if birthday_public and not birthday_md:raise ValueError('Elige el día y mes para compartir tu cumpleaños.')
                photo=profile.get('photo','')
                if request.form.get('use_avatar')=='1':photo=''
                file=request.files.get('photo')
                if file and file.filename:photo,_,_=services['save_image'](file)
                published=int(request.form.get('published')=='1')
                db().execute("INSERT INTO member_profiles(user_id,message,verse_ref,verse_text,likes,gifts,dislikes,avatar,photo,published,status,updated) VALUES(?,?,?,?,?,?,?,?,?,?,'Pendiente',?) ON CONFLICT(user_id) DO UPDATE SET message=excluded.message,verse_ref=excluded.verse_ref,verse_text=excluded.verse_text,likes=excluded.likes,gifts=excluded.gifts,dislikes=excluded.dislikes,avatar=excluded.avatar,photo=excluded.photo,published=excluded.published,status='Pendiente',updated=excluded.updated,reviewed_by=NULL",(g.user['id'],fields['message'],fields['verse_ref'],fields['verse_text'],fields['likes'],fields['gifts'],fields['dislikes'],avatar,photo,published,now()))
                db().execute('UPDATE member_profiles SET birthday_md=?,birthday_public=? WHERE user_id=?',(birthday_md,birthday_public,g.user['id']))
                audit('Actualizó su perfil público para revisión',member['group_id']);db().commit();flash('Perfil guardado. Tus líderes revisarán los cambios antes de publicarlos.','success');return redirect(url_for('retro.member_profile'))
            except ValueError as exc:flash(str(exc),'error')
        return render_template('member_profile.html',member=member,profile=profile,avatars=AVATARS,public_page=True)

    @bp.get('/miembros/<int:user_id>/foto')
    def member_photo(user_id):
        item=db().execute("SELECT p.*,ms.group_id,ms.status member_status,u.active FROM member_profiles p JOIN memberships ms ON ms.user_id=p.user_id JOIN users u ON u.id=p.user_id WHERE p.user_id=?",(user_id,)).fetchone()
        if not item:abort(404)
        public=item['published'] and item['status']=='Aprobado' and item['member_status']=='Aprobado' and item['active']
        if not public and not (g.user and (g.user['id']==user_id or services['can_review'](item['group_id']))):abort(403)
        if item['photo']:
            if item['demo'] and item['photo'].startswith('demo:'):return send_file(Path(app.static_folder)/item['photo'][5:])
            return send_file(Path(app.config['UPLOAD_FOLDER'])/item['photo'])
        avatar=item['avatar'] if item['avatar'] in AVATARS else 'luz'
        return send_file(Path(app.static_folder)/'avatars'/f'{avatar}.svg',mimetype='image/svg+xml')

    app.register_blueprint(bp)
    return dict(public_members=public_members,public_birthdays=public_birthdays)
