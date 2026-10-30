"""Configuración pública de contacto por organización, sin destinatarios inventados."""
import json
import re
from urllib.parse import urlencode,quote

LIMITS={'label':32,'title':100,'message':600,'name':100,'hours':160,'whatsapp_message':400,'whatsapp':30,'phone':30,'email':160}
DEFAULTS=dict(enabled=True,label='Contáctanos',title='Hablemos',message='Consulta por nuestras actividades y cómo ser parte de nuestra comunidad.',name='',hours='',whatsapp_message='Hola, quisiera recibir información.',whatsapp='',phone='',email='')

def validate_contact(values):
    settings={'enabled':values.get('enabled') in [True,'1']}
    for key,limit in LIMITS.items():
        value=str(values.get(key,DEFAULTS[key])).strip()
        if len(value)>limit:raise ValueError(f'El campo {key} admite hasta {limit} caracteres.')
        settings[key]=value
    settings['label']=settings['label'] or 'Contáctanos'
    settings['title']=settings['title'] or 'Hablemos'
    for key in ['whatsapp','phone']:
        number=re.sub(r'[\s()\-]','',settings[key])
        if number and not re.fullmatch(r'\+?[1-9][0-9]{7,14}',number):
            raise ValueError('Escribe el teléfono con código de país; por ejemplo, +51 seguido de los 9 dígitos.')
        settings[key]=number.lstrip('+') if key=='whatsapp' else number
    if settings['email'] and not re.fullmatch(r'[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',settings['email']):
        raise ValueError('Escribe un correo válido, sin espacios ni saltos de línea.')
    return settings

def contact_settings(group):
    if not group:return dict(DEFAULTS)
    try:
        raw=json.loads(group['contact_settings'])
        if not isinstance(raw,dict):raise ValueError()
        return validate_contact({**DEFAULTS,**raw})
    except (ValueError,TypeError):return dict(DEFAULTS)

def public_contact(group):
    if not group or not group['active']:return None
    settings=contact_settings(group)
    if not settings['enabled']:return None
    return dict(settings,group_id=group['id'],group_name=group['name'],
                whatsapp_url='https://wa.me/'+settings['whatsapp']+'?'+urlencode({'text':settings['whatsapp_message']}) if settings['whatsapp'] else '',
                phone_url='tel:'+settings['phone'] if settings['phone'] else '',
                email_url='mailto:'+quote(settings['email'],safe='@') if settings['email'] else '')
