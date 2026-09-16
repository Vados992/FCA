from dataclasses import dataclass
from typing import Callable
from fcea.core.errors import ValidationError


@dataclass(frozen=True)
class Adapter:
    id: str
    domain: str
    methods: tuple[str,...]
    claim_types: tuple[str,...]
    parameters: frozenset[str]
    analyze_fn: Callable
    identification: dict[str, tuple[str,...]]
    validity_assumptions: tuple[str,...] = ()
    version: str = '1.0.0'
    limitations: str = ''

    def analyze(self, data, method, parameters, seed):
        if method not in self.methods:
            raise ValidationError(f'Unsupported method for {self.id}: {method}')
        extra = set(parameters) - self.parameters
        if extra:
            raise ValidationError(f'Unknown {self.id} parameters: {sorted(extra)}')
        if not isinstance(data,list) or not data or len(data)>20000 or any(not isinstance(row,dict) for row in data):
            raise ValidationError('Adapter input must contain 1–20000 typed rows')
        result = self.analyze_fn(data,method,parameters,seed)
        result.update(adapter_id=self.id,adapter_version=self.version,method=method,limitations=self.limitations)
        return result

    def manifest(self):
        return {'adapter_id':self.id,'version':self.version,'domain':self.domain,
                'methods':list(self.methods),'claim_types':list(self.claim_types),
                'parameters':sorted(self.parameters),'identification_assumptions':self.identification,
                'validity_assumptions':list(self.validity_assumptions),'limitations':self.limitations,
                'core_controls':'mandatory; no override interface'}
