from fcea.core.errors import ValidationError
from .policy import POLICY
from .science import SCIENCE
from .market import MARKET
from .supply import SUPPLY
from .climate import CLIMATE
from .physics import PHYSICS
from .integrity import INTEGRITY
from .public_health import PUBLIC_HEALTH

ADAPTERS = {a.id:a for a in (POLICY,SCIENCE,MARKET,SUPPLY,CLIMATE,PHYSICS,INTEGRITY,PUBLIC_HEALTH)}


def get_adapter(identifier):
    try:
        return ADAPTERS[identifier]
    except KeyError as exc:
        raise ValidationError(f'Unknown adapter: {identifier}') from exc


def analyze_request(request):
    return get_adapter(request['adapter_id']).analyze(request['data'],request['method'],request['parameters'],request['seed'])
