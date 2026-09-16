"""Allowlisted parsers and dimensional normalization; no code execution in transforms."""
import csv
import io
import math
import re
import unicodedata

from .canonical import loads
from .errors import ValidationError


UNITS = {'1':('dimensionless',1.0,0.0), '%':('dimensionless',0.01,0.0),
    'm':('length',1.0,0.0), 'cm':('length',0.01,0.0), 'mm':('length',0.001,0.0),
    'kg':('mass',1.0,0.0), 'g':('mass',0.001,0.0), 's':('time',1.0,0.0),
    'min':('time',60.0,0.0), 'h':('time',3600.0,0.0),
    'K':('temperature',1.0,0.0), 'degC':('temperature',1.0,273.15),
    'USD':('USD',1.0,0.0), 'EUR':('EUR',1.0,0.0), 'count':('count',1.0,0.0)}


def convert(value, source_unit, target_unit):
    if source_unit not in UNITS or target_unit not in UNITS:
        raise ValidationError('Unknown unit; extend the reviewed unit registry')
    a, b = UNITS[source_unit], UNITS[target_unit]
    if a[0] != b[0]:
        raise ValidationError('Incompatible dimensions; currency conversion requires a dated model')
    if type(value) not in (int,float) or not math.isfinite(value):
        raise ValidationError('Finite numeric value required')
    return {'raw_value': value, 'raw_unit': source_unit, 'value': (value*a[1]+a[2]-b[2])/b[1], 'unit': target_unit}


def normalize_identity(text):
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().split())


def extract(raw, transform, selector=''):
    if transform == 'json.pointer.v1':
        value = loads(raw)
        if selector:
            if not selector.startswith('/'):
                raise ValidationError('JSON pointer must start with /')
            for token in selector[1:].split('/'):
                if re.search(r'~(?![01])', token):
                    raise ValidationError('Invalid JSON pointer escape')
                token = token.replace('~1','/').replace('~0','~')
                try:
                    if isinstance(value, list):
                        if not token.isdigit() or (len(token)>1 and token[0]=='0'):
                            raise ValueError('Noncanonical array index')
                        value = value[int(token)]
                    elif isinstance(value, dict):
                        value = value[token]
                    else:
                        raise ValueError('Cannot traverse scalar')
                except (KeyError,IndexError,ValueError) as exc:
                    raise ValidationError('Unresolvable JSON pointer') from exc
        return value
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeError as exc:
        raise ValidationError('Text/CSV source must be UTF-8') from exc
    if transform == 'text.v1':
        if selector:
            raise ValidationError('Text extraction does not accept a selector')
        return text
    if transform == 'csv.rows.v1':
        if selector:
            raise ValidationError('CSV extraction does not accept a selector')
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValidationError('CSV header must be nonempty and unique')
        rows = list(reader)
        if any(None in row or any(v is None for v in row.values()) for row in rows):
            raise ValidationError('Ragged CSV rows')
        return rows
    raise ValidationError(f'Unknown transform: {transform}')
