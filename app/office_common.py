"""Permisos locales, documentos versionados y validación de la oficina digital."""
import io,json,sqlite3,zipfile
from datetime import date,datetime
from decimal import Decimal,InvalidOperation
from pathlib import Path
from uuid import uuid4
from flask import g,abort,request,flash,url_for,send_file
from werkzeug.utils import secure_filename
from PIL import Image
from .community_data import local_now

SCHEMA=Path(__file__).with_name('office_schema.sql')
OFFICE_MODULES={'documents','plans','meetings','requests','finance'}

class Office:
    def __init__(self,app,services):
        self.app=app
        for k,v in services.items():setattr(self,k,v)

    def organization(self):
        if not g.user:abort(403)
        if g.user['admin']:gid=1
        else:
            row=self.db().execute('SELECT group_id FROM assignments WHERE user_id=? AND active=1 ORDER BY CASE WHEN group_id=1 THEN 0 ELSE 1 END,id LIMIT 1',(g.user['id'],)).fetchone()
            if not row:abort(403)
            gid=row['group_id']
        return self.db().execute('SELECT * FROM groups WHERE id=?',(gid,)).fetchone()

    def can(self,gid,area='secretary',write=False):
        if not g.user:return False
        if g.user['admin']:return True
        roles={r['role'] for r in self.db().execute('SELECT role FROM assignments WHERE user_id=? AND group_id=? AND active=1',(g.user['id'],gid))}
        if area=='secretary' and not write:return bool(roles)
        permitted={'Presidente','Vicepresidente','Líder'}|({'Tesorero','Protesorero'} if area=='finance' else {'Secretario','Prosecretario'})
        return bool(roles&permitted)

    def require(self,gid,area='secretary',write=False):
        if not self.can(gid,area,write):abort(403)

    def leader(self):return bool(g.user and (g.user['admin'] or self.db().execute('SELECT 1 FROM assignments WHERE user_id=? AND active=1',(g.user['id'],)).fetchone()))

    def row(self,table,rid):
        row=self.db().execute(f'SELECT * FROM {table} WHERE id=?',(rid,)).fetchone()
        if not row:abort(404)
        return row

    def files(self,resource,rid):
        return self.db().execute('SELECT f.*,u.name uploader FROM office_files f JOIN users u ON u.id=f.created_by WHERE resource=? AND resource_id=? ORDER BY f.id DESC',(resource,rid)).fetchall()

    def upload(self,resource,rid,gid,required=False,field='attachment'):
        file=request.files.get(field)
        if not file or not file.filename:
            if required:raise ValueError('Selecciona el documento para continuar.')
            return None
        original=secure_filename(file.filename)[:170]
        ext=Path(original).suffix.lower()
        mime={'.pdf':'application/pdf','.docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document','.xlsx':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg'}
        if ext not in mime:raise ValueError('Usa PDF, DOCX, XLSX, PNG o JPG. Máximo 10 MB por envío.')
        raw=file.read(10*1024*1024+1)
        if not raw or len(raw)>10*1024*1024:raise ValueError('El documento está vacío o supera 10 MB.')
        try:
            if ext=='.pdf' and not raw.lstrip().startswith(b'%PDF-'):raise ValueError()
            if ext in ['.docx','.xlsx']:
                with zipfile.ZipFile(io.BytesIO(raw)) as z:
                    expected='word/document.xml' if ext=='.docx' else 'xl/workbook.xml'
                    if expected not in z.namelist() or sum(i.file_size for i in z.infolist())>50*1024*1024:raise ValueError()
            if ext in ['.png','.jpg','.jpeg']:
                with Image.open(io.BytesIO(raw)) as im:
                    if im.format not in ['PNG','JPEG'] or im.width*im.height>40_000_000:raise ValueError()
                    im.verify()
        except (ValueError,OSError,zipfile.BadZipFile):raise ValueError('El contenido no corresponde a un documento o imagen válido.')
        filename='office_'+uuid4().hex+ext;path=Path(self.app.config['UPLOAD_FOLDER'])/filename
        path.write_bytes(raw);g.setdefault('office_uploads',[]).append(path)
        return self.db().execute('INSERT INTO office_files(resource,resource_id,group_id,filename,original_name,mime,created_by,created) VALUES(?,?,?,?,?,?,?,?)',(resource,rid,gid,filename,original,mime[ext],g.user['id'],self.now())).lastrowid

    def commit(self,action,gid):
        self.audit(action,gid);self.db().commit();g.office_uploads=[]
        flash('Cambios guardados.','success')

    def fail(self,error):
        self.db().rollback()
        for path in g.pop('office_uploads',[]):path.unlink(missing_ok=True)
        flash('Revisa los datos: '+str(error) if isinstance(error,ValueError) else 'No se pudo guardar. Revisa los datos e inténtalo nuevamente.','error')

    def file_allowed(self,file):
        gid=file['group_id'];resource=file['resource'];rid=file['resource_id']
        if resource=='template':return self.leader()
        if self.can(gid,'finance' if resource=='movement' else 'secretary'):return True
        if resource=='credential':
            cred=self.row('office_credentials',rid);meeting=self.row('office_meetings',cred['meeting_id'])
            return self.can(meeting['group_id'])
        if resource=='plan':
            return self.can(1) and bool(self.db().execute('SELECT 1 FROM office_plan_deliveries WHERE file_id=?',(file['id'],)).fetchone())
        return False

    def money(self,value):
        try:
            amount=Decimal(str(value))
            if not amount.is_finite() or amount<=0 or amount>Decimal('999999999') or amount.as_tuple().exponent < -2:raise ValueError()
            return int(amount*100)
        except (ValueError,InvalidOperation):raise ValueError('Indica un monto mayor a cero y con hasta dos decimales.')

    def text(self,key,required=True,limit=12000):
        value=request.form.get(key,'').strip()
        if (required and not value) or len(value)>limit:raise ValueError('Revisa el campo '+key+'.')
        return value

    def day(self,value):
        try:return date.fromisoformat(value).isoformat()
        except (TypeError,ValueError):raise ValueError('Indica una fecha válida.')

    def timestamp(self,value):
        try:
            dt=datetime.fromisoformat(value)
            if dt.tzinfo:raise ValueError()
            return dt.isoformat(timespec='minutes')
        except (TypeError,ValueError):raise ValueError('Indica fecha y hora de Perú válidas.')

    def year(self,value):
        try:
            y=int(value)
            if not 2000<=y<=2200:raise ValueError()
            return y
        except (TypeError,ValueError):raise ValueError('Indica un año entre 2000 y 2200.')

    def open_campaign(self,campaign):return bool(campaign['active'] and campaign['deadline']>=local_now().isoformat(timespec='minutes'))
