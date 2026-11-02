"""Libro de caja por organización, proyectos, deudas y reportes en céntimos."""
import calendar,io,json,secrets,sqlite3
from datetime import date
from decimal import Decimal
from flask import Blueprint,abort,g,request,redirect,render_template,url_for,send_file,flash
from .community_data import local_now


def register_treasury(app,o):
    bp=Blueprint('treasury',__name__,url_prefix='/tesoreria');db=o.db;logged=o.logged
    app.jinja_env.filters['soles']=lambda cents:f'{Decimal(cents)/100:,.2f}'

    def options(gid):
        projects=db().execute('SELECT * FROM finance_projects WHERE group_id=? ORDER BY name',(gid,)).fetchall()
        categories=sorted({'Ofrendas','Donaciones','Música','Logística','Decoración','Transporte','Alimentación','Saldo inicial','Otros'}|{r['name'] for r in db().execute('SELECT name FROM finance_categories WHERE group_id=?',(gid,))}|{r['d'].get('subcategory','Otros') for r in ledger(gid)})
        return projects,categories

    def project_id(gid,value):
        if not value:return None
        try:pid=int(value)
        except (ValueError,TypeError):raise ValueError('Proyecto inválido.')
        if o.row('finance_projects',pid)['group_id']!=gid:abort(403)
        return pid

    def ledger(gid):
        output=[]
        projects={r['id']:r['name'] for r in db().execute('SELECT id,name FROM finance_projects WHERE group_id=?',(gid,))}
        for row in db().execute("SELECT * FROM records WHERE module='finance' AND group_id=? ORDER BY id DESC",(gid,)):
            item=dict(row);d=json.loads(row['data']);item['d']=d
            item['cents']=int(Decimal(d.get('amount','0'))*100)
            body=d.get('body','');title=d.get('title','')
            item['description']=body if body.startswith(title) else (title+' · '+body if body and title else body or title)
            item['project']=projects.get(d.get('project_id'),'Sin proyecto')
            item['settlement']=bool(db().execute('SELECT 1 FROM finance_settlements WHERE record_id=?',(row['id'],)).fetchone())
            output.append(item)
        return output

    def debt_rows(gid,end='9999-12-31',pid=None):
        result=[]
        for row in db().execute('SELECT d.*,p.name project FROM finance_debts d LEFT JOIN finance_projects p ON p.id=d.project_id WHERE d.group_id=? AND d.day<=? ORDER BY d.day DESC,d.id DESC',(gid,end)):
            if pid and row['project_id']!=pid:continue
            item=dict(row)
            paid=db().execute("SELECT s.amount_cents,r.data FROM finance_settlements s JOIN records r ON r.id=s.record_id WHERE s.debt_id=? AND s.voided=0",(row['id'],)).fetchall()
            item['paid']=sum(r['amount_cents'] for r in paid if json.loads(r['data'])['date']<=end)
            item['remaining']=item['amount_cents']-item['paid'];result.append(item)
        return result

    def token():
        value=request.form.get('token') or secrets.token_urlsafe(24)
        if not 20<=len(value)<=100:raise ValueError('El envío expiró. Recarga el formulario.')
        if db().execute('SELECT 1 FROM finance_tokens WHERE token=?',(value,)).fetchone():raise ValueError('Este envío ya fue registrado. No se duplicó el movimiento.')
        db().execute('INSERT INTO finance_tokens VALUES(?,?,?)',(value,g.user['id'],o.now()))

    def page(template,org,**data):
        return render_template('office/'+template,org=org,brand_group=org,current_scope=org['id'],module='finance',office=o,**data)

    def report(gid,args):
        year=str(args.get('year',local_now().year));month=str(args.get('month',''));start='';end='9999-12-31'
        if year!='all':
            y=o.year(year)
            try:
                m=int(month) if month else None
                start=date(y,m or 1,1).isoformat();end=date(y,m or 12,calendar.monthrange(y,m or 12)[1]).isoformat()
            except (ValueError,TypeError):raise ValueError('Mes inválido.')
        if args.get('from'):start=o.day(args['from'])
        if args.get('to'):end=o.day(args['to'])
        if start and start>end:raise ValueError('La fecha inicial debe ser anterior al cierre.')
        pid=project_id(gid,args.get('project'));category=args.get('category','');query=args.get('q','').casefold()
        all_items=ledger(gid);approved=[r for r in all_items if r['d'].get('status')=='Aprobado']
        sign=lambda r:r['cents'] if r['d'].get('category')=='Ingreso' else -r['cents']
        opening=sum(sign(r) for r in approved if start and r['d'].get('date','')<start)
        closing=sum(sign(r) for r in approved if r['d'].get('date','')<=end)
        selected=[r for r in all_items if (not start or r['d'].get('date','')>=start) and r['d'].get('date','')<=end and (not pid or r['d'].get('project_id')==pid) and (not category or r['d'].get('subcategory')==category) and query in r['description'].casefold()]
        selected.sort(key=lambda r:(r['d'].get('date',''),r['id']))
        income=sum(r['cents'] for r in selected if r['d'].get('status')=='Aprobado' and r['d'].get('category')=='Ingreso')
        expense=sum(r['cents'] for r in selected if r['d'].get('status')=='Aprobado' and r['d'].get('category')=='Egreso')
        monthly={};categories={};projects={}
        for r in selected:
            if r['d'].get('status')!='Aprobado':continue
            for collection,key in [(monthly,r['d']['date'][:7]),(categories,r['d'].get('subcategory','Otros')),(projects,r['project'])]:
                values=collection.setdefault(key,[0,0]);values[0 if r['d']['category']=='Ingreso' else 1]+=r['cents']
        debts=debt_rows(gid,end,pid)
        return dict(year=year,month=month,start=start,end=end,project=pid,category=category,items=selected,income=income,expense=expense,net=income-expense,opening=opening,closing=closing,monthly=sorted(monthly.items()),by_category=sorted(categories.items()),by_project=sorted(projects.items()),debts=debts,receivable=sum(d['remaining'] for d in debts if d['kind']=='Por cobrar'),payable=sum(d['remaining'] for d in debts if d['kind']=='Por pagar'))

    @bp.get('')
    @logged
    def index():
        org=o.organization();o.require(org['id'],'finance')
        try:data=report(org['id'],request.args)
        except ValueError as exc:abort(400,str(exc))
        projects,categories=options(org['id'])
        export_url=url_for('treasury.excel',**{k:request.args[k] for k in ['year','month','from','to','project','category','q'] if k in request.args})
        return page('treasury.html',org,report=data,projects=projects,categories=categories,export_url=export_url)

    def movement(rid=None):
        old=o.row('records',rid) if rid else None
        if old and old['module']!='finance':abort(404)
        requested=request.form.get('group_id',type=int) or request.args.get('group',type=int)
        org=o.row('groups',old['group_id']) if old else o.row('groups',requested) if requested else o.organization();gid=org['id'];o.require(gid,'finance',True)
        data=json.loads(old['data']) if old else dict(date=local_now().date().isoformat(),category='Ingreso',account='Efectivo',status='Aprobado')
        linked=db().execute('SELECT 1 FROM finance_settlements WHERE record_id=?',(rid,)).fetchone() if rid else None
        if linked or data.get('status')=='Anulado':abort(403,'Los pagos se corrigen desde su deuda; los movimientos anulados se conservan como historial.')
        if request.method=='POST':
            try:
                if request.form.get('group_id') and request.form.get('group_id',type=int)!=gid:abort(403)
                kind=request.form.get('kind',request.form.get('category','Ingreso'))
                state=request.form.get('status','Aprobado')
                if kind not in ['Ingreso','Egreso'] or state not in ['Pendiente','Aprobado']:raise ValueError('Selecciona ingreso/egreso y un estado válido.')
                description=request.form.get('description',request.form.get('body','')).strip() or request.form.get('title','').strip()
                if not description or len(description)>12000:raise ValueError('Escribe una descripción del movimiento (hasta 12000 caracteres).')
                amount=o.money(request.form.get('amount'));day=o.day(request.form.get('date'))
                pid=project_id(gid,request.form.get('project_id'))
                category=request.form.get('subcategory','Otros').strip()
                if not category or len(category)>100:raise ValueError('Selecciona una categoría válida.')
                account=request.form.get('account','Efectivo')
                if account not in ['Efectivo','Banco']:raise ValueError('Cuenta inválida.')
                event_id=request.form.get('event_id',type=int)
                if event_id:
                    event=o.row('records',event_id)
                    if event['module']!='events' or event['group_id']!=gid:raise ValueError('El evento debe pertenecer a tu organización.')
                if pid:event_id=o.row('finance_projects',pid)['event_id']
                token()
                data.update(title=description[:120],body=description,amount=f'{Decimal(amount)/100:.2f}',date=day,category=kind,subcategory=category,account=account,project_id=pid,event_id=event_id or '',status=state)
                if old:db().execute('UPDATE records SET data=?,updated=? WHERE id=?',(json.dumps(data),o.now(),rid))
                else:rid=db().execute("INSERT INTO records(module,group_id,data,author_id,created,updated) VALUES('finance',?,?,?,?,?)",(gid,json.dumps(data),g.user['id'],o.now(),o.now())).lastrowid
                o.upload('movement',rid,gid);o.commit('Guardó movimiento de caja #'+str(rid),gid)
                return redirect(url_for('treasury.index'))
            except (ValueError,sqlite3.IntegrityError) as exc:o.fail(exc)
        projects,categories=options(gid)
        return page('movement.html',org,data=data,rid=old['id'] if old else None,projects=projects,categories=categories,submission_token=secrets.token_urlsafe(24))

    @bp.route('/movimientos/nuevo',methods=['GET','POST'])
    @logged
    def new_movement():return movement()

    @bp.route('/movimientos/<int:rid>',methods=['GET','POST'])
    @logged
    def edit_movement(rid):return movement(rid)

    def void_movement(rid):
        record=o.row('records',rid)
        if record['module']!='finance':abort(404)
        o.require(record['group_id'],'finance',True)
        data=json.loads(record['data']);data['status']='Anulado'
        db().execute('UPDATE records SET data=?,updated=? WHERE id=?',(json.dumps(data),o.now(),rid))
        db().execute('UPDATE finance_settlements SET voided=1 WHERE record_id=?',(rid,))
        o.commit('Anuló movimiento de caja #'+str(rid),record['group_id'])
        return redirect(url_for('treasury.index'))

    @bp.post('/movimientos/<int:rid>/anular')
    @logged
    def void(rid):return void_movement(rid)

    @bp.route('/organizar',methods=['GET','POST'])
    @logged
    def organize():
        org=o.organization();gid=org['id'];o.require(gid,'finance',True)
        if request.method=='POST':
            try:
                name=o.text('name',limit=100)
                if request.form.get('action')=='project':
                    event_id=request.form.get('event_id',type=int)
                    if event_id:
                        event=o.row('records',event_id)
                        if event['module']!='events' or event['group_id']!=gid:abort(403)
                    db().execute('INSERT INTO finance_projects(group_id,name,event_id) VALUES(?,?,?)',(gid,name,event_id))
                elif request.form.get('action')=='category':db().execute('INSERT INTO finance_categories(group_id,name) VALUES(?,?)',(gid,name))
                else:abort(400)
                o.commit('Creó agrupación de tesorería: '+name,gid);return redirect(url_for('.organize'))
            except (ValueError,sqlite3.IntegrityError) as exc:o.fail(exc)
        projects,categories=options(gid)
        events=[dict(id=r['id'],title=json.loads(r['data']).get('title','')) for r in db().execute("SELECT id,data FROM records WHERE module='events' AND group_id=? ORDER BY id DESC",(gid,))]
        return page('finance_organize.html',org,projects=projects,categories=categories,events=events)

    @bp.route('/deudas',methods=['GET','POST'])
    @logged
    def debts():
        org=o.organization();gid=org['id'];o.require(gid,'finance')
        if request.method=='POST':
            try:
                kind=o.text('kind')
                if kind not in ['Por cobrar','Por pagar']:raise ValueError('Tipo de deuda inválido.')
                day=o.day(request.form.get('date'));due=o.day(request.form['due']) if request.form.get('due') else ''
                if due and due<day:raise ValueError('El vencimiento no puede ser anterior al registro.')
                token()
                did=db().execute('INSERT INTO finance_debts(group_id,kind,counterparty,description,amount_cents,day,due,project_id,created_by,created) VALUES(?,?,?,?,?,?,?,?,?,?)',(gid,kind,o.text('counterparty',limit=200),o.text('description'),o.money(request.form.get('amount')),day,due,project_id(gid,request.form.get('project_id')),g.user['id'],o.now())).lastrowid
                o.commit('Registró deuda #'+str(did),gid);return redirect(url_for('.debt',did=did))
            except (ValueError,sqlite3.IntegrityError) as exc:o.fail(exc)
        return page('debts.html',org,debts=debt_rows(gid),projects=options(gid)[0],submission_token=secrets.token_urlsafe(24))

    @bp.route('/deudas/<int:did>',methods=['GET','POST'])
    @logged
    def debt(did):
        item=o.row('finance_debts',did);org=o.organization()
        if item['group_id']!=org['id']:abort(403)
        gid=org['id'];o.require(gid,'finance')
        if request.method=='POST':
            try:
                # Serializa pagos y evita que dos peticiones excedan el saldo.
                db().execute('BEGIN IMMEDIATE')
                balance=next(d for d in debt_rows(gid) if d['id']==did)['remaining']
                amount=o.money(request.form.get('amount'))
                if amount>balance:raise ValueError('El pago supera el saldo pendiente.')
                day=o.day(request.form.get('date'))
                if day<item['day']:raise ValueError('El pago no puede ser anterior a la deuda.')
                account=request.form.get('account','Efectivo')
                if account not in ['Efectivo','Banco']:raise ValueError('Cuenta inválida.')
                token();kind='Ingreso' if item['kind']=='Por cobrar' else 'Egreso'
                description=('Cobro' if kind=='Ingreso' else 'Pago')+' de deuda #'+str(did)+' · '+item['counterparty']
                data=dict(title=description,body=description,category=kind,amount=f'{Decimal(amount)/100:.2f}',date=day,account=account,subcategory='Deudas',project_id=item['project_id'],status='Aprobado')
                rid=db().execute("INSERT INTO records(module,group_id,data,author_id,created,updated) VALUES('finance',?,?,?,?,?)",(gid,json.dumps(data),g.user['id'],o.now(),o.now())).lastrowid
                db().execute('INSERT INTO finance_settlements(debt_id,record_id,amount_cents,created) VALUES(?,?,?,?)',(did,rid,amount,o.now()))
                o.upload('movement',rid,gid);o.commit('Registró pago de deuda #'+str(did),gid)
                return redirect(url_for('.debt',did=did))
            except (ValueError,sqlite3.IntegrityError) as exc:o.fail(exc)
        detail=next(d for d in debt_rows(gid) if d['id']==did)
        payments=[dict(id=r['id'],record_id=r['record_id'],voided=r['voided'],amount_cents=r['amount_cents'],d=json.loads(r['data'])) for r in db().execute('SELECT s.*,r.data FROM finance_settlements s JOIN records r ON r.id=s.record_id WHERE s.debt_id=? ORDER BY s.id DESC',(did,))]
        return page('debt.html',org,debt=detail,payments=payments,submission_token=secrets.token_urlsafe(24))

    @bp.get('/reporte.xlsx')
    @logged
    def excel():
        org=o.organization();o.require(org['id'],'finance')
        try:data=report(org['id'],request.args)
        except ValueError as exc:abort(400,str(exc))
        from .treasury_export import export_workbook
        stream=export_workbook(org,data)
        return send_file(stream,as_attachment=True,download_name='tesoreria_'+str(org['id'])+'_'+str(data['year'])+'.xlsx',mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    app.register_blueprint(bp)
    return dict(index=index,movement=movement,void=void_movement,report=report)
