from dataclasses import dataclass
from pathlib import Path
import hashlib
import hmac
import secrets
from fcea.core.canonical import canonical,loads
from fcea.core.errors import AuthorizationError,ValidationError


@dataclass(frozen=True)
class Identity:
    name: str
    roles: frozenset[str]


ROLES={'reader','analyst','reviewer','release','admin'}


def load_identities(path):
    config=loads(Path(path).read_bytes())
    if set(config)!={'identities'} or not isinstance(config['identities'],list):
        raise ValidationError('Auth file requires an identities array')
    seen=set()
    for item in config['identities']:
        if set(item)!={'name','roles','token_sha256'} or not set(item['roles'])<=ROLES or not item['name']:
            raise ValidationError('Invalid identity record')
        if item['name'] in seen: raise ValidationError('Duplicate identity')
        seen.add(item['name'])
        if len(item['token_sha256'])!=64: raise ValidationError('Invalid token digest')
    if not seen: raise ValidationError('At least one configured identity required')
    return config['identities']


def authenticate(header,identities):
    if not header or not header.startswith('Bearer '):
        raise AuthorizationError('Bearer authentication required')
    token=header[7:]
    if len(token)<32 or len(token)>512:
        raise AuthorizationError('Invalid bearer credential')
    sha=hashlib.sha256(token.encode()).hexdigest()
    for entry in identities:
        if hmac.compare_digest(sha,entry['token_sha256']):
            return Identity(entry['name'],frozenset(entry['roles']))
    raise AuthorizationError('Invalid bearer credential')


def require(identity,*roles):
    if 'admin' not in identity.roles and not set(roles)&set(identity.roles):
        raise AuthorizationError('Role does not permit this operation')


def initialize_auth(path):
    target=Path(path)
    target.parent.mkdir(parents=True,exist_ok=True)
    identities=[]; tokens={}
    for name,roles in [('analyst',['reader','analyst']),('reviewer',['reader','reviewer']),
                       ('reviewer2',['reader','reviewer']),('release',['reader','release'])]:
        token=secrets.token_urlsafe(32); tokens[name]=token
        identities.append({'name':name,'roles':roles,'token_sha256':hashlib.sha256(token.encode()).hexdigest()})
    with target.open('xb') as f: f.write(canonical({'identities':identities}))
    target.chmod(0o600)
    return tokens
