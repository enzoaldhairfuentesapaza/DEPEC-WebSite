"""Cuenta de pruebas: conserva al operador y usa identidades con permisos reales."""
import secrets
from werkzeug.security import generate_password_hash
from .community_data import local_now
from .modules import ROLES

TEST_EMAIL='pruebas@depec.demo'
TEST_PASSWORD='DepecPruebas2026!'
TEST_ROLES=['Administrador',*ROLES,'Miembro','Visitante']

def create_test_operator(connection,email=TEST_EMAIL,password=TEST_PASSWORD,demo_only=False):
    if demo_only and not connection.execute("SELECT 1 FROM users WHERE email='admin@depec.demo' AND admin=1 AND active=1").fetchone():return False
    row=connection.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone()
    if row:
        # Una cuenta existente ajena al laboratorio nunca se eleva automáticamente.
        return bool(connection.execute('SELECT 1 FROM test_operators WHERE user_id=?',(row[0],)).fetchone())
    uid=connection.execute('INSERT INTO users(name,email,password,admin) VALUES(?,?,?,1)',('Pruebas globales · DEPEC',email,generate_password_hash(password))).lastrowid
    connection.execute('INSERT INTO test_operators(user_id) VALUES(?)',(uid,));connection.commit()
    return True

def operator_for_session(connection,session):
    uid=session.get('test_operator')
    if not uid:return None
    operator=connection.execute('SELECT u.* FROM users u JOIN test_operators t ON t.user_id=u.id WHERE u.id=? AND u.active=1 AND u.admin=1',(uid,)).fetchone()
    if not operator:return None
    effective=session.get('uid')
    if effective is not None and effective!=uid and not connection.execute('SELECT 1 FROM test_personas WHERE operator_id=? AND user_id=?',(uid,effective)).fetchone():return None
    return operator

def persona_for(connection,operator_id,group,role):
    stamp=local_now().isoformat(timespec='seconds')
    row=connection.execute('SELECT user_id FROM test_personas WHERE operator_id=? AND group_id=? AND role=?',(operator_id,group['id'],role)).fetchone()
    if row:uid=row[0]
    else:
        email='persona-'+secrets.token_hex(12)+'@depec.invalid'
        uid=connection.execute('INSERT INTO users(name,email,password) VALUES(?,?,?)',(f'PRUEBA · {role} · {group["name"]}',email,generate_password_hash(secrets.token_urlsafe(48)))).lastrowid
        connection.execute('INSERT INTO test_personas(operator_id,group_id,role,user_id) VALUES(?,?,?,?)',(operator_id,group['id'],role,uid))
    connection.execute('UPDATE users SET active=1,admin=0 WHERE id=?',(uid,))
    connection.execute('UPDATE assignments SET active=0 WHERE user_id=?',(uid,))
    connection.execute('UPDATE grants SET active=0 WHERE user_id=?',(uid,))
    if role=='Miembro':
        connection.execute("INSERT INTO memberships(user_id,group_id,status,created,reviewed_by,reviewed) VALUES(?,?,'Aprobado',?,?,?) ON CONFLICT(user_id) DO UPDATE SET status='Aprobado',group_id=excluded.group_id",(uid,group['id'],stamp,operator_id,stamp))
    else:
        assignment=connection.execute('SELECT id FROM assignments WHERE user_id=? AND group_id=? AND role=? LIMIT 1',(uid,group['id'],role)).fetchone()
        if assignment:connection.execute('UPDATE assignments SET active=1 WHERE id=?',(assignment[0],))
        else:connection.execute('INSERT INTO assignments(user_id,group_id,role,period) VALUES(?,?,?,?)',(uid,group['id'],role,str(local_now().year)))
    return uid
