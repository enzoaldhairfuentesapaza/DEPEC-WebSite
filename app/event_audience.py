"""Destinatarios y distribución de eventos, separados de la autoría."""
AUDIENCES=['Toda la DEPEC','Público de mi iglesia','Iglesias invitadas','Solo líderes de mi organización']

def audience_of(data):
    return data.get('audience') or ('Solo líderes de mi organización' if data.get('visibility')=='internal' else 'Toda la DEPEC')

def in_event_page(data,owner,scope):
    audience=audience_of(data)
    if scope is None:return True
    # Mantener la distribución de eventos anteriores hasta que se editen.
    if not data.get('audience'):return scope in [1,owner]
    if scope==owner:return True
    if audience=='Toda la DEPEC':return True
    if audience=='Iglesias invitadas':return scope in data.get('invited_groups',[])
    return False
