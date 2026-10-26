"""Escenario visual solicitado. Solo se carga automáticamente en bases de demostración."""
import json
import sqlite3
from datetime import timedelta
from pathlib import Path
from werkzeug.security import generate_password_hash
from .community_data import local_now

JC_TITLE='Más que una iglesia, una familia que camina junta'
JC_DESCRIPTION='Nos conocemos bien, compartimos la vida sin filtros y nos une el gozo de adorar juntos. Aquí siempre hay un lugar para ti.'
JC_VERSE={'reference':'Colosenses 3:14','text':'Sobre todo, vístanse de amor, que es el vínculo perfecto que nos une a todos.','version':'Texto proporcionado por la comunidad'}

def seed_visual_demo(db):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='site_settings'").fetchone():return False
    if db.execute("SELECT 1 FROM site_settings WHERE key='retro-demo-v04'").fetchone():return False
    owner=db.execute("SELECT id FROM users WHERE email='admin@depec.demo'").fetchone()
    if not owner:return False
    demo_hash=generate_password_hash('DepecDemo2026!')
    owner=owner[0];stamp=local_now().isoformat(timespec='seconds');current=local_now()
    jc=db.execute("SELECT id FROM groups WHERE lower(name) LIKE '%jorge%ch%vez%' OR name='SEC Jorge Chávez'").fetchone()
    if not jc:return False
    jc=jc[0]
    db.execute("UPDATE groups SET color='#3453d1',hero_title=?,hero_description=?,description=?,verse_mode='custom',custom_verses=?,maps_url=?,address=?,schedule=?,church=? WHERE id=? AND hero_title=''",(JC_TITLE,JC_DESCRIPTION,JC_DESCRIPTION,json.dumps([JC_VERSE]),'https://maps.app.goo.gl/KSo2PasAcs3HdyU36','Local de la Iglesia Jorge Chávez · ver ubicación exacta en Google Maps','Sábados, 18:00 h · horario de ejemplo por confirmar','Iglesia Jorge Chávez',jc))
    db.execute("UPDATE groups SET hero_title='La fe nos une. Juntos, crecemos.',hero_description='Somos jóvenes de varias iglesias de Arequipa sureste. Nuestras SEC y GJ comparten la fe, la amistad y el deseo de servir a Cristo y a su iglesia.',address='Dirección de ejemplo: Avenida La Amistad 123, Arequipa',anniversary_note='Fecha de demostración; pendiente de confirmar',founded_date='2006-11-15' WHERE id=1 AND hero_title=''")
    colors=['#cc254b','#f06c30','#3453d1','#8c43c3','#0c8d75','#edc744','#d84c93']
    for i,row in enumerate(db.execute('SELECT id FROM groups ORDER BY id').fetchall()):
        if row[0]!=jc:db.execute('UPDATE groups SET color=? WHERE id=?',(colors[i%len(colors)],row[0]))
    roles=['Presidente','Vicepresidente','Secretario','Tesorero','Vocal','Líder']
    names=['Lucas Rojas','Sofía Torres','Mateo Salas','Valeria Paredes','Gabriel Luna','Camila Soto']
    for gid in [1,jc]:
        for i,(name,role) in enumerate(zip(names,roles)):
            email=f'lider-{gid}-{i}@demo.depec.local'
            uid=db.execute('INSERT INTO users(name,email,password) VALUES(?,?,?)',(name+' · DEMO',email,demo_hash)).lastrowid
            db.execute('INSERT INTO assignments(user_id,group_id,role,period) VALUES(?,?,?,?)',(uid,gid,role,str(current.year)))
            picture='demo:demo/lider-hombre.png' if i%2==0 else 'demo:demo/lider-mujer.png'
            db.execute('INSERT INTO leader_profiles(user_id,group_id,message,photo,published,featured) VALUES(?,?,?,?,1,?)',(uid,gid,['Crecer juntos también es cuidar unos de otros.','Tu historia importa; caminemos en comunidad.','Servimos con alegría, fe y amistad.'][i%3],picture,int(role=='Líder')))
    for i in range(12):
        gid=jc if i<8 else 2
        name=['Ariana','Diego','Mariana','Nicolás','Daniela','Sebastián','Elisa','Tomás','Paola','Joaquín','Renata','Andrés'][i]
        uid=db.execute('INSERT INTO users(name,email,password) VALUES(?,?,?)',(name+' Ejemplo · DEMO',f'miembro-{i}@demo.depec.local',demo_hash)).lastrowid
        db.execute("INSERT INTO memberships(user_id,group_id,status,created,reviewed_by,reviewed) VALUES(?,?,'Aprobado',?,?,?)",(uid,gid,stamp,owner,stamp))
        db.execute("INSERT INTO member_profiles(user_id,message,verse_ref,verse_text,likes,gifts,dislikes,avatar,published,status,updated,reviewed_by,demo) VALUES(?,?,?,?,?,?,?,?,1,'Aprobado',?,?,1)",(uid,['Me gusta encontrar a Dios en las pequeñas cosas.','La música y la comunidad hacen más bonito el camino.','Siempre hay una oportunidad para servir.'][i%3],'Filipenses 4:13','Todo lo puedo en Cristo que me fortalece.',['Música, caminatas y compartir un café','Lectura, deportes y aprender cosas nuevas'][i%2],['Escuchar y acompañar','Música y servicio','Enseñar con paciencia'][i%3],'La falta de respeto y dejar a alguien fuera',['luz','paloma','biblia','pez','cruz'][i%5],stamp,owner))
        if i<3:
            db.execute("INSERT INTO community_messages(user_id,group_id,body,status,created,reviewed_by,reviewed) VALUES(?,?,?,'Aprobado',?,?,?)",(uid,gid,['Mensaje de ejemplo: aquí encontré amistad, alegría y ganas de servir.','Mensaje ficticio: compartir nuestra fe hace más bonito el camino.','Mensaje de demostración: siempre hay un lugar para aprender y crecer.'][i],stamp,owner,stamp))
    titles=['Una noche para agradecer','Entre amigos y café','Manos que sirven','Jóvenes con propósito','Tarde de juegos y fe','Voces de esperanza']
    for gid in [1,jc]:
        for i,title in enumerate(titles):
            day=current+timedelta(days=2+i*3)
            static=f'demo/afiche-{i+1}.svg';wide=i in [1,4]
            data=dict(title=title+' · DEMO',body='Evento ficticio de demostración: un tiempo para compartir, aprender y fortalecer nuestra amistad. Fecha y horario generados para probar el diseño.',date=day.replace(hour=18,minute=0,second=0).isoformat(timespec='minutes'),end_date=day.replace(hour=20,minute=0,second=0).isoformat(timespec='minutes'),location='Local de la Iglesia Jorge Chávez · ver ubicación exacta en Google Maps' if gid==jc else 'Dirección de ejemplo: Avenida La Amistad 123, Arequipa',event_address='',category=['Encuentro','Taller','Otro'][i%3],visibility='public',status='Reprogramado' if i==3 else 'Programado',capacity='40',poster_static=static,image_width=1200 if wide else 720,image_height=620 if wide else 1000,media_kind='Afiche',demo=True)
            rid=db.execute('INSERT INTO records(module,group_id,data,author_id,created,updated) VALUES(\'events\',?,?,?,?,?)',(gid,json.dumps(data),owner,stamp,stamp)).lastrowid
            db.execute('INSERT INTO media_files(group_id,record_id,title,kind,static_name,width,height,uploaded_by,visibility,created) VALUES(?,?,?,\'Afiche\',?,?,?,?,\'public\',?)',(gid,rid,title+' · DEMO',static,data['image_width'],data['image_height'],owner,stamp))
        for title in ['Campamento de líderes · DEMO','Agradecidos al Rey 2026 · DEMO','Juntos hacemos comunidad · DEMO']:
            aid=db.execute('INSERT INTO albums(group_id,title,description,created_by,created) VALUES(?,?,?,?,?)',(gid,title,'Álbum ficticio para mostrar el diseño. Sus fotografías son escenas generadas con IA.',owner,stamp)).lastrowid
            for picture in ['encuentro','servicio','amistad']:
                db.execute('INSERT INTO media_files(group_id,album_id,title,kind,static_name,width,height,uploaded_by,visibility,created) VALUES(?,?,?,\'Fotografía\',?,1536,1024,?,\'public\',?)',(gid,aid,'Escena de ejemplo · IA',f'demo/{picture}.png',owner,stamp))
    db.execute('INSERT INTO media_files(group_id,title,kind,static_name,width,height,uploaded_by,visibility,created) VALUES(?,\'Nuestra familia de Jorge Chávez\',\'Fotografía\',\'images/jorge-chavez.jpg\',640,641,?,\'public\',?)',(jc,owner,stamp))
    db.execute("INSERT INTO site_settings(key,value) VALUES('retro-demo-v04',?)",(stamp,));db.commit();return True
