import shutil,subprocess,sys
from pathlib import Path


def test_annotated_tag_is_created_only_on_clean_commit(tmp_path):
    root=Path(__file__).parents[1]
    for name in ['VERSION','etiquetar_version.py']:shutil.copy(root/name,tmp_path/name)
    def git(*args):return subprocess.run(['git',*args],cwd=tmp_path,check=True,capture_output=True,text=True).stdout.strip()
    git('init');git('config','user.email','test@example.com');git('config','user.name','Prueba local')
    git('add','.');git('commit','-m','Prueba del hito')
    def tag():return subprocess.run([sys.executable,'etiquetar_version.py'],cwd=tmp_path,capture_output=True,text=True)
    (tmp_path/'pendiente.txt').write_text('pendiente')
    assert tag().returncode!=0 and not git('tag','--list')
    git('add','.');git('commit','-m','Completar revisión')
    assert tag().returncode==0
    assert git('cat-file','-t','v7.0.0')=='tag'
    original=git('rev-list','-n','1','v7.0.0')
    assert original==git('rev-parse','HEAD')
    assert tag().returncode==0
    (tmp_path/'pendiente.txt').write_text('nuevo commit')
    git('add','.');git('commit','-m','Cambio posterior')
    assert tag().returncode!=0
    assert git('rev-list','-n','1','v7.0.0')==original
