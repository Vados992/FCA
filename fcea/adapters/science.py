from statistics import fmean
from fcea.analysis.statistics import column,number
from fcea.core.errors import ValidationError
from .base import Adapter


def analyze(data,method,p,seed):
    if method=='finite_predicate':
        key=p.get('key','member'); witness=p.get('witness','witness')
        members=[row.get(key) for row in data]
        if any(not isinstance(x,str) or not x for x in members) or len(members)!=len(set(members)):
            raise ValidationError('Finite predicate requires distinct named members')
        values=[row.get(witness) for row in data]
        if any(type(v) is not bool for v in values):
            raise ValidationError('Finite witness values must be JSON booleans')
        quantifier=p.get('quantifier','none')
        if quantifier not in ('none','exists'): raise ValidationError('Invalid finite quantifier')
        count=sum(values)
        supported=count==0 if quantifier=='none' else count>0
        return {'estimate':float(count),'metric':'finite_witness_count',
            'scientific_state':'SUPPORTED' if supported else 'FALSIFIED' if quantifier=='none' else 'NOT_SUPPORTED',
            'diagnostics':{'members':members,'witness_members':[m for m,v in zip(members,values) if v],
                'quantifier':quantifier,'expected_size':p.get('expected_size')},
            'uncertainty_components':{'coverage':'requires exhaustive finite-domain certificate','measurement':'upstream evidence validity'},
            'interpretation':'Quantification is restricted to a named finite universe, never an unbounded population.'}
    observed = column(data,p.get('observed','observed'))
    predicted = column(data,p.get('predicted','predicted'))
    sigma = column(data,p.get('sigma','sigma'))
    if any(x<=0 for x in sigma):
        raise ValidationError('Measurement standard deviations must be positive')
    if 'max_standardized_residual' not in p:
        raise ValidationError('Freeze a family-aware max_standardized_residual threshold')
    threshold = number(p['max_standardized_residual'])
    if threshold<=0:
        raise ValidationError('Residual threshold must be positive')
    offset = number(p.get('prediction_offset',0))
    residual = [(a-b-offset)/s for a,b,s in zip(observed,predicted,sigma)]
    maximum = max(abs(v) for v in residual)
    return {'estimate':fmean(residual),'metric':'mean_standardized_residual',
            'scientific_state':'SUPPORTED' if maximum<=threshold else 'FALSIFIED',
            'diagnostics':{'max_standardized_residual':maximum,'chi_square_diagnostic':sum(v*v for v in residual),
                           'threshold':threshold,'observations':len(data)},
            'uncertainty_components':{'measurement_sigma':sigma,'model_misspecification':'not eliminated'},
            'interpretation':'Compatibility with fixed predictions in the tested rows; this does not certify theory truth.'}


SCIENCE = Adapter('science','science',('prediction_check','finite_predicate'),('MODEL_COMPATIBILITY','UNIVERSAL_NEGATIVE','EXISTENTIAL'),
    frozenset({'observed','predicted','sigma','max_standardized_residual','prediction_offset','key','witness','quantifier','expected_size'}),analyze,{},
    ('measurement_validity',),limitations='Fixed predictions and supplied measurement standard deviations; no automatic equation solver or theorem prover.')
