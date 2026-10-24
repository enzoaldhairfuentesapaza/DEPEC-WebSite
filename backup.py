"""Respaldo local: detener el servidor antes de ejecutarlo."""
from datetime import datetime
from pathlib import Path
import sqlite3
import tempfile
import zipfile

base=Path(__file__).resolve().parent
source=base/'instance'/'depec.sqlite'
if not source.exists():
    raise SystemExit('No existe la base de datos. Inicializa primero la aplicación.')
(base/'backups').mkdir(exist_ok=True)
output=base/'backups'/('depec-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.zip')
with tempfile.TemporaryDirectory() as temp:
    snapshot=Path(temp)/'depec.sqlite'
    with sqlite3.connect(source) as original,sqlite3.connect(snapshot) as target:
        original.backup(target)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        archive.write(snapshot,'depec.sqlite')
        for file in (base/'instance').rglob('*'):
            if file.is_file() and not file.name.startswith('depec.sqlite'):
                archive.write(file,file.relative_to(base/'instance'))
print('Respaldo creado:',output)
