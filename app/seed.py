"""Datos totalmente ficticios. Se cargan solo mediante el comando seed-demo."""
import json
from datetime import date,datetime,timedelta
from werkzeug.security import generate_password_hash


def seed(db):
    if db.execute('SELECT count(*) FROM users').fetchone()[0]:
        raise RuntimeError('La base ya tiene usuarios. seed-demo exige una base nueva para no sobrescribir información.')
    organizations=[('DEPEC','DEPEC','#bd123b','Una comunidad, muchos caminos para servir.'),('SEC Israel','SEC','#c66a3b','Creciendo en fe y compartiendo el camino.'),('SEC Jorge Chávez','SEC','#78955c','Jóvenes con un corazón dispuesto a servir.'),('SEC Chiguata','SEC','#8f7aad','Encuentros que fortalecen nuestra comunidad.'),('SEC Jerusalén','SEC','#5a92a5','Construimos comunidad con alegría y propósito.'),('GJ Campo Marte','GJ','#c99b40','Pequeños pasos, grandes descubrimientos.'),('GJ Rosales','GJ','#bd7a8a','Un espacio para aprender, compartir y crecer.')]
    for name,kind,color,description in organizations:
        db.execute('INSERT INTO groups(name,kind,color,description,church,schedule) VALUES(?,?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET description=excluded.description,church=excluded.church,schedule=excluded.schedule',(name,kind,color,description,'' if kind=='DEPEC' else 'Iglesia '+name.replace('SEC ','').replace('GJ ',''),'' if kind=='DEPEC' else 'Sábados · horario de ejemplo por confirmar'))
    accounts=[('Administración demo','admin@depec.demo',1),('Presidencia Israel','israel@depec.demo',0),('Secretaría Israel','secretaria@depec.demo',0),('Tesorería Israel','tesoreria@depec.demo',0),('Presidencia DEPEC','presidencia@depec.demo',0),('Vocal Israel','vocal@depec.demo',0)]
    for name,email,admin in accounts:
        db.execute('INSERT INTO users(name,email,password,admin) VALUES(?,?,?,?)',(name,email,generate_password_hash('DepecDemo2026!'),admin))
    for uid,gid,role in [(2,2,'Presidente'),(3,2,'Secretario'),(4,2,'Tesorero'),(5,1,'Presidente'),(6,2,'Vocal')]:
        db.execute('INSERT INTO assignments(user_id,group_id,role,period) VALUES(?,?,?,?)',(uid,gid,role,str(date.today().year)))
    def add(module,gid,data):
        stamp=datetime.now().isoformat(timespec='seconds')
        return db.execute('INSERT INTO records(module,group_id,data,author_id,created,updated) VALUES(?,?,?,1,?,?)',(module,gid,json.dumps(data),stamp,stamp)).lastrowid
    current=date.today()
    firstnames=['Andrea','Mateo','Lucía','Gabriel','Valeria','Daniel','Camila','Samuel']
    for gid in range(2,8):
        for n in range(8):
            add('members',gid,dict(title=f'{firstnames[n]} Demo {gid}-{n+1}',date=f'{2000+n:04d}-{current.month:02d}-{min(28,current.day+n):02d}',email='',phone='',category='Bautizado' if n%3 else 'No bautizado',baptism_date='',joined=current.replace(day=1).isoformat(),status='Activo',guardian='Contacto ficticio por registrar' if n>=6 else '',public_birthday='Sí',body='Registro de demostración. No corresponde a una persona real.'))
        day=current+timedelta(days=(gid-1)*2)
        event=add('events',gid,dict(title=['','', 'Noche de encuentro y alabanza','Jornada de servicio','Encuentro juvenil en Chiguata','Taller: juntos crecemos','Tarde de juegos y amistad','Un sábado para compartir'][gid],body='Actividad ficticia para explorar el calendario. Compartiremos un tiempo de integración, reflexión y comunidad.',date=day.isoformat()+'T17:00',end_date=day.isoformat()+'T19:00',location='Local de la iglesia · por confirmar',category='Encuentro',visibility='public',status='Programado',capacity='40'))
        add('posts',gid,dict(title='¡Hay un lugar para ti!',body='Estamos preparando un nuevo encuentro para compartir como comunidad. Consulta el calendario de nuestro grupo y acompáñanos.\n\nEsta publicación es parte de la demostración del sistema.',date=(current-timedelta(days=1)).isoformat()+'T09:00',category='Invitación',visibility='public',status='Publicado'))
        for title,kind,amount,cat in [('Ofrenda de la semana','Ingreso','185.50','Ofrenda'),('Aporte para encuentro','Ingreso','120.00','Aporte'),('Material para dinámica','Egreso','47.80','Materiales')]:
            add('finance',gid,dict(title=title,category=kind,amount=amount,date=current.isoformat(),account='Efectivo',subcategory=cat,status='Aprobado',event_id=str(event),body='Movimiento ficticio de demostración.'))
        add('documents',gid,dict(title='Plan de trabajo · borrador',category='Plan de trabajo',date=current.isoformat(),period=str(current.year),status='Borrador',body='Ejemplo de registro documental. Adjunta un archivo para probar la descarga privada.'))
        add('plans',gid,dict(title='Encuentro de integración',body='Fortalecer los vínculos entre integrantes y dar la bienvenida a nuevos miembros.',responsible='Directiva del grupo',date=day.isoformat(),amount='250.00',period=str(current.year),status='En proceso'))
        add('requests',gid,dict(title='Presentar plan de trabajo',body='La DEPEC solicita adjuntar el plan de trabajo del próximo periodo. Solicitud ficticia.',date=(current+timedelta(days=14)).isoformat(),status='Pendiente'))
        add('tasks',gid,dict(title='Confirmar lugar y materiales',body='Coordinar los preparativos del próximo encuentro.',responsible='Presidencia y vocales',date=(current+timedelta(days=3)).isoformat(),status='Pendiente'))
        add('meetings',gid,dict(title='Reunión de coordinación de directiva',date=(current+timedelta(days=1)).isoformat()+'T19:00',location='Local de la iglesia',body='Agenda: revisar el plan de trabajo, asignar responsables y coordinar el próximo evento.',status='Convocada'))
    add('events',1,dict(title='Encuentro general DEPEC',body='Un encuentro para todas las SEC y GJ. Actividad ficticia de demostración.',date=(current+timedelta(days=18)).isoformat()+'T10:00',end_date=(current+timedelta(days=18)).isoformat()+'T16:00',location='Sede por confirmar',category='Encuentro',visibility='public',status='Programado',capacity='0'))
    for title in ['Campamento de líderes','Agradecidos al Rey 2026']:
        db.execute('INSERT INTO albums(group_id,title,description,created_by,created) VALUES(1,?,?,1,?)',(title,'Álbum de ejemplo. Los líderes pueden aportar aquí las fotografías del encuentro.',datetime.now().isoformat(timespec='seconds')))
    db.commit()
    from .retro_demo import seed_visual_demo,seed_birthday_demo
    seed_visual_demo(db)
    seed_birthday_demo(db)

    from .role_lab import create_test_operator
    create_test_operator(db,demo_only=True)
