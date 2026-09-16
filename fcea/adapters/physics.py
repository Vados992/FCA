import math
from fcea.analysis.statistics import column,number
from fcea.core.errors import ValidationError
from .base import Adapter


def analyze(data,method,p,seed):
    t,x,v=column(data,'t'),column(data,'x'),column(data,'v')
    omega=number(p.get('omega',1)); mass=number(p.get('mass',1))
    closure=number(p.get('closure_tolerance',1e-6)); energy_tol=number(p.get('energy_relative_tolerance',1e-6))
    if len(t)<3 or any(b<=a for a,b in zip(t,t[1:])) or min(omega,mass)<=0 or min(closure,energy_tol)<0:
        raise ValidationError('Invalid ordered oscillator trajectory or tolerances')
    energies=[0.5*mass*(b*b+omega*omega*a*a) for a,b in zip(x,v)]
    if energies[0]<=1e-20:
        raise ValidationError('Zero-energy stationary state is not an oscillatory orbit')
    drift=max(abs(e-energies[0])/energies[0] for e in energies)
    endpoint=math.hypot(x[-1]-x[0],(v[-1]-v[0])/omega)
    amplitude=math.sqrt(x[0]**2+(v[0]/omega)**2)
    residual=max(math.hypot(a-(x[0]*math.cos(omega*(z-t[0]))+v[0]/omega*math.sin(omega*(z-t[0]))),
                           (b-(-x[0]*omega*math.sin(omega*(z-t[0]))+v[0]*math.cos(omega*(z-t[0]))))/omega)
                 for z,a,b in zip(t,x,v))/amplitude
    period_count=(t[-1]-t[0])*omega/(2*math.pi)
    valid=drift<=energy_tol and residual<=number(p.get('model_residual_tolerance',1e-6))
    return {'estimate':endpoint,'metric':'phase_space_endpoint_distance',
            'scientific_state':'SUPPORTED' if endpoint<=closure and valid and period_count>=0.99 else 'NOT_SUPPORTED',
            'diagnostics':{'relative_energy_drift':drift,'normalized_model_residual':residual,
                'model_valid':valid,'period_count':period_count,'closure_tolerance':closure},
            'uncertainty_components':{'numerical_tolerances':dict(p),'measurement':'provided by upstream source'},
            'interpretation':'A bounded phase-space recurrence in a harmonic oscillator; no closed timelike curve or time-travel inference.'}


PHYSICS = Adapter('physics','physics',('oscillator_recurrence',),('MODEL_COMPATIBILITY','EXISTENTIAL'),
    frozenset({'omega','mass','closure_tolerance','energy_relative_tolerance','model_residual_tolerance'}),analyze,{},
    ('oscillator_regime',),limitations='Fixed-frequency harmonic oscillator trajectory validation. No general relativity solver, arbitrary theorem proving, or spacetime causal-loop certification.')
