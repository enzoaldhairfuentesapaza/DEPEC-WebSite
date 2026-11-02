"""Excel imprimible, con importes numéricos y textos tratados como datos."""
import io
from openpyxl import Workbook
from openpyxl.styles import Font,PatternFill,Alignment
from openpyxl.worksheet.page import PageMargins
from openpyxl.utils import get_column_letter


def export_workbook(org,data):
    wb=Workbook();wb.remove(wb.active)
    def sheet(name,headers,rows,money_columns=()):
        ws=wb.create_sheet(name);ws.append([org['name']+' · '+name]);ws.append(['Periodo: '+(data['start'] or 'Inicio')+' al '+data['end']]);ws.append(headers);ws['A1'].data_type='s';ws['A2'].data_type='s'
        for row in rows:
            ws.append(row)
            # Evita ejecutar fórmulas suministradas en descripciones o nombres.
            for cell,value in zip(ws[ws.max_row],row):
                if isinstance(value,str):cell.data_type='s'
        for row in ws.iter_rows(min_row=4):
            for cell in row:cell.alignment=Alignment(vertical='top',wrap_text=True)
            for col in money_columns:row[col-1].number_format='"S/ "#,##0.00;[Red]-"S/ "#,##0.00'
        for cell in ws[3]:cell.fill=PatternFill('solid',fgColor='A91E42');cell.font=Font(color='FFFFFF',bold=True)
        ws['A1'].font=Font(size=16,bold=True,color='A91E42');ws.freeze_panes='A4';ws.auto_filter.ref=f'A3:{get_column_letter(len(headers))}{max(ws.max_row,3)}'
        for i,header in enumerate(headers,1):ws.column_dimensions[get_column_letter(i)].width=45 if header in ['Descripción','Concepto','Proyecto','Categoría','Contraparte'] else 20
        ws.sheet_properties.pageSetUpPr.fitToPage=True;ws.page_setup.orientation='landscape';ws.page_setup.paperSize=ws.PAPERSIZE_A4;ws.page_setup.fitToWidth=1;ws.page_setup.fitToHeight=0;ws.print_title_rows='1:3';ws.page_margins=PageMargins(left=.3,right=.3,top=.5,bottom=.5,header=.2,footer=.2);ws.oddFooter.center.text='Página &P de &N'
        return ws
    summary=[['Ingresos del filtro',data['income']/100],['Egresos del filtro',data['expense']/100],['Resultado del filtro',data['net']/100],['Saldo de caja previo al periodo (organización completa)',data['opening']/100],['Saldo de caja al cierre (organización completa)',data['closing']/100],['Deudas por cobrar al cierre',data['receivable']/100],['Deudas por pagar al cierre',data['payable']/100],['Proyecto filtrado',str(data['project'] or 'Todos')],['Categoría filtrada',data['category'] or 'Todas'],['Criterio','Solo Aprobados integran los totales. Pendientes y anulados se conservan como detalle. Las deudas no son efectivo hasta su pago.']]
    sheet('Resumen',['Concepto','Valor'],summary,(2,))
    sheet('Movimientos',['ID','Fecha','Tipo','Descripción','Proyecto','Categoría','Cuenta','Estado','Ingreso','Egreso'],[[r['id'],r['d'].get('date',''),r['d'].get('category',''),r['description'],r['project'],r['d'].get('subcategory',''),r['d'].get('account',''),r['d'].get('status',''),r['cents']/100 if r['d']['category']=='Ingreso' else 0,r['cents']/100 if r['d']['category']=='Egreso' else 0] for r in data['items']],(9,10))
    for name,key,column in [('Mensual','monthly','Mes'),('Por categoría','by_category','Categoría'),('Por proyecto','by_project','Proyecto')]:
        sheet(name,[column,'Ingresos','Egresos','Resultado'],[[label,values[0]/100,values[1]/100,(values[0]-values[1])/100] for label,values in data[key]],(2,3,4))
    sheet('Deudas',['ID','Tipo','Contraparte','Descripción','Proyecto','Fecha','Vencimiento','Total','Pagado al cierre','Pendiente al cierre'],[[d['id'],d['kind'],d['counterparty'],d['description'],d['project'] or '',d['day'],d['due'],d['amount_cents']/100,d['paid']/100,d['remaining']/100] for d in data['debts']],(8,9,10))
    stream=io.BytesIO();wb.save(stream);stream.seek(0);return stream
