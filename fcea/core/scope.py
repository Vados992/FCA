"""Finite named-set scopes; assumptions narrow scope by adding conditions."""
from .canonical import timestamp


def set_within(inner, outer):
    return outer == ['*'] or ('*' not in inner and set(inner) <= set(outer))


def within(inner, outer):
    reasons = []
    for field in ('domains', 'populations', 'regimes', 'model_families'):
        if not set_within(getattr(inner, field), getattr(outer, field)):
            reasons.append(f'scope:{field}')
    if not set(outer.assumptions) <= set(inner.assumptions):
        reasons.append('scope:assumptions_removed')
    if inner.precision != outer.precision and outer.precision != '*':
        reasons.append('scope:precision')
    if outer.start and (not inner.start or timestamp(inner.start) < timestamp(outer.start)):
        reasons.append('scope:start')
    if outer.end and (not inner.end or timestamp(inner.end) > timestamp(outer.end)):
        reasons.append('scope:end')
    return reasons


def evidence_within(inner, outer, evidence):
    """Evidence valid time can restrict, but never widen, its registered scope."""
    reasons = within(inner, outer)
    start, end = evidence.get('valid_start'), evidence.get('valid_end')
    if start and (not inner.start or timestamp(inner.start) < timestamp(start)):
        reasons.append('scope:evidence_valid_start')
    if end and (not inner.end or timestamp(inner.end) > timestamp(end)):
        reasons.append('scope:evidence_valid_end')
    return reasons


def strength_meet(vectors):
    if not vectors:
        return {k: False for k in ('provenance','independence','time','model','reproduction','scope')}
    keys = set(vectors[0])
    if any(set(v) != keys for v in vectors):
        raise ValueError('Strength vectors must use identical dimensions')
    return {k: min(v[k] for v in vectors) for k in sorted(keys)}
