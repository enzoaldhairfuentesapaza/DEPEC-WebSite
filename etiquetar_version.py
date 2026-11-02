"""Crea una etiqueta anotada sobre el commit actual, sin modificar la historia."""
import argparse
import subprocess
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--push',action='store_true',help='Publicar también la etiqueta en origin.')
    args=parser.parse_args()
    root=Path(__file__).resolve().parent
    def git(*arguments):return subprocess.run(['git',*arguments],cwd=root,check=True,capture_output=True,text=True).stdout.strip()
    tag='v'+(root/'VERSION').read_text(encoding='utf-8').strip()
    try:
        git('rev-parse','--show-toplevel')
        if git('status','--porcelain'):
            raise RuntimeError('Primero guarda los cambios: git add . y git commit -m "feat: secretaria y tesoreria digital". Luego vuelve a ejecutar este script.')
        if git('tag','--list',tag):
            if git('rev-list','-n','1',tag)!=git('rev-parse','HEAD'):raise RuntimeError('La etiqueta '+tag+' ya existe en otro commit. No se modificó.')
            print('La etiqueta ya identifica este commit: '+tag)
        else:
            git('tag','-a',tag,'-m','Secretaría y Tesorería digital: planes, actas, credenciales, correspondencia y caja con reportes Excel')
            print('Etiqueta anotada creada: '+tag)
        if args.push:
            git('push','origin',tag);print('Etiqueta publicada en origin.')
        else:print('Para publicarla: git push origin '+tag)
    except (subprocess.CalledProcessError,RuntimeError,FileNotFoundError) as exc:
        message=exc.stderr.strip() if isinstance(exc,subprocess.CalledProcessError) else str(exc)
        raise SystemExit('No se creó/publicó la etiqueta: '+message)

if __name__=='__main__':main()
