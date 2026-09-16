import math
from statistics import NormalDist
from fcea.analysis.statistics import column,linear_fit,number
from fcea.core.errors import ValidationError
from .base import Adapter


def analyze(data,method,p,seed):
    x=column(data,p.get('fingerprint','fingerprint'))
    y=column(data,p.get('observed','observed'))
    scale=number(p.get('forcing_scale',1))
    if scale<=0:
        raise ValidationError('forcing_scale must be positive')
    fit=linear_fit([v*scale for v in x],y)
    alpha=number(p.get('alpha',0.05))
    if not 0<alpha<1 or len(x)<30:
        raise ValidationError('Asymptotic iid fit requires >=30 rows and valid alpha')
    z=NormalDist().inv_cdf(1-alpha/2)
    low,high=fit['slope']-z*fit['standard_error'],fit['slope']+z*fit['standard_error']
    return {'estimate':fit['slope'],'metric':'single_fingerprint_scaling',
            'interval':{'low':low,'high':high,'level':1-alpha,'kind':'asymptotic_normal_iid'},
            'scientific_state':'SUPPORTED' if low>0 else 'INCONCLUSIVE','diagnostics':fit,
            'uncertainty_components':{'sampling':'iid OLS approximation','forcing_scale':scale,
                'correlated_internal_variability':'not modeled; real correlated climate series are outside this adapter'}}


CLIMATE = Adapter('climate','climate',('single_fingerprint_iid',),('ASSOCIATION',),
    frozenset({'fingerprint','observed','forcing_scale','alpha'}),analyze,{},
    ('independent_residuals','fixed_fingerprint','measurement_validity'),
    limitations='Single fixed fingerprint, intercept and iid errors. This is not full optimal fingerprinting, multi-forcing attribution, or a climate policy conclusion.')
