"""Cultos recurrentes y excepciones de una fecha, independientes de eventos."""
from datetime import date, time
from flask import request, g, abort, redirect, url_for, flash
DAYS=['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']

def register_worship(app,db,allowed,logged):
    @app.before_request
    def prepare_worship():
        db().execute('CREATE TABLE IF NOT EXISTS worship_schedule(group_id INTEGER PRIMARY KEY REFERENCES groups(id),weekday INTEGER NOT NULL,hour TEXT NOT NULL)')
        db().execute("CREATE TABLE IF NOT EXISTS worship_days(group_id INTEGER NOT NULL REFERENCES groups(id),day TEXT NOT NULL,cancelled INTEGER NOT NULL DEFAULT 0,note TEXT NOT NULL DEFAULT '',PRIMARY KEY(group_id,day))")
        # Ejemplo solicitado; nunca reemplaza un horario ya personalizado.
        db().execute("INSERT OR IGNORE INTO worship_schedule SELECT id,6,'15:30' FROM groups WHERE id=3 AND name LIKE '%Ch%'")
        db().commit()

    def schedules(scope=None,private=False):
        return [dict(r) for r in db().execute('SELECT w.*,gr.name,gr.color FROM worship_schedule w JOIN groups gr ON gr.id=w.group_id WHERE gr.active=1') if (not scope or r['group_id']==scope) and (not private or allowed(r['group_id'],'events'))]

    def occurrences(weeks,scope,private):
        result={}
        for row in schedules(None if scope==1 else scope,private):
            for week in weeks:
                for day in week:
                    if day.weekday()!=row['weekday']:continue
                    change=db().execute('SELECT * FROM worship_days WHERE group_id=? AND day=?',(row['group_id'],day.isoformat())).fetchone()
                    item=dict(row);item.update(day=day.isoformat(),cancelled=bool(change and change['cancelled']),note=change['note'] if change else '')
                    result.setdefault(day.isoformat(),[]).append(item)
        return result

    @app.context_processor
    def worship_context():
        return dict(worship_schedule=lambda gid:schedules(gid),worship_weekdays=DAYS)

    @app.post('/calendar/culto')
    @logged
    def save_worship():
        gid=request.form.get('group_id',type=int)
        if not gid or gid==1 or not allowed(gid,'events',True):abort(403)
        if not db().execute('SELECT 1 FROM groups WHERE id=? AND active=1',(gid,)).fetchone():abort(404)
        try:
            action=request.form.get('action')
            if action=='schedule':
                weekday=int(request.form['weekday']);hour=request.form['hour']
                if weekday not in range(7):raise ValueError()
                time.fromisoformat(hour)
                if len(hour)!=5:raise ValueError()
                db().execute('INSERT INTO worship_schedule VALUES(?,?,?) ON CONFLICT(group_id) DO UPDATE SET weekday=excluded.weekday,hour=excluded.hour',(gid,weekday,hour))
                db().execute('UPDATE groups SET schedule=? WHERE id=?',(DAYS[weekday]+' · '+hour,gid))
            elif action in ['day','reset']:
                day=date.fromisoformat(request.form['day']).isoformat()
                schedule=db().execute('SELECT * FROM worship_schedule WHERE group_id=?',(gid,)).fetchone()
                if not schedule or date.fromisoformat(day).weekday()!=schedule['weekday']:raise ValueError()
                if action=='reset':db().execute('DELETE FROM worship_days WHERE group_id=? AND day=?',(gid,day))
                else:
                    note=request.form.get('note','').strip()
                    if len(note)>300 or (request.form.get('cancelled') and not note):raise ValueError()
                    db().execute('INSERT INTO worship_days VALUES(?,?,?,?) ON CONFLICT(group_id,day) DO UPDATE SET cancelled=excluded.cancelled,note=excluded.note',(gid,day,int(bool(request.form.get('cancelled'))),note))
            else:raise ValueError()
            db().commit();flash('Calendario de cultos actualizado.','success')
        except (ValueError,KeyError):
            db().rollback();flash('Revisa el horario o la fecha. Para cancelar escribe un motivo (máximo 300 caracteres).','error')
        return redirect(url_for('calendar_view',group=gid,month=request.form.get('month') or None))
    return occurrences
