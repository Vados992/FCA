from pathlib import Path
import shutil
from fcea.core.canonical import canonical,digest,loads
from fcea.core.errors import IntegrityError,ValidationError
from fcea.service import Service


def backup(service,target):
    target=Path(target)
    target.mkdir(parents=True,exist_ok=False,mode=0o700)
    with service.db.lock:
        service.verify()
        service.db.backup_database(target/'fcea.sqlite3')
        shutil.copytree(service.raw.root,target/'raw')
        hashes={str(p.relative_to(target)).replace('\\','/'):digest(p.read_bytes()) for p in target.rglob('*') if p.is_file()}
        (target/'backup-manifest.json').write_bytes(canonical({'format':'fcea-backup-1','files':hashes}))
    return {'status':'BACKED_UP','files':len(hashes),'path':str(target)}


def restore(source,target):
    source,target=Path(source),Path(target)
    manifest=loads((source/'backup-manifest.json').read_bytes())
    if manifest.get('format')!='fcea-backup-1': raise ValidationError('Unknown backup format')
    for name,sha in manifest['files'].items():
        path=source/name
        if not path.resolve().is_relative_to(source.resolve()) or path.is_symlink() or digest(path.read_bytes())!=sha:
            raise IntegrityError('Backup manifest mismatch or unsafe path')
    if target.exists(): raise ConflictError('Restore target must not exist')
    target.mkdir(parents=True,mode=0o700)
    for name in manifest['files']:
        dest=target/name; dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source/name,dest)
    with Service(target) as restored: restored.verify()
    return {'status':'RESTORED','path':str(target)}


from fcea.core.errors import ConflictError
