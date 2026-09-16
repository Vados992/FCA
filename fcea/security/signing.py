"""HMAC-SHA256 is a shared-secret authenticator, explicitly not a public-key signature."""
from pathlib import Path
import hmac
import hashlib
import secrets
from fcea.core.canonical import canonical
from fcea.core.errors import ValidationError,IntegrityError


def generate_key(path):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f: f.write(secrets.token_bytes(32))
    p.chmod(0o600)


def read_key(path):
    key=Path(path).read_bytes()
    if len(key)<32: raise ValidationError('Release authentication requires >=32 random key bytes')
    return key


def sign(payload,key):
    if len(key)<32: raise ValidationError('Release key is too short')
    return {'algorithm':'HMAC-SHA256','key_id':hashlib.sha256(key).hexdigest()[:16],
            'tag':hmac.new(key,canonical(payload),hashlib.sha256).hexdigest()}


def verify(payload,authentication,key):
    expected=sign(payload,key)
    if authentication.get('algorithm')!='HMAC-SHA256' or authentication.get('key_id')!=expected['key_id'] or not hmac.compare_digest(authentication.get('tag',''),expected['tag']):
        raise IntegrityError('Release authentication failed')
    return True
