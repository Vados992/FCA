from statistics import fmean
from fcea.analysis.statistics import number,column,bootstrap,mean_difference,wald_iv,conclusion
from fcea.core.errors import ValidationError
from .base import Adapter


PARAMS = frozenset({'treatment','outcome','pre','pre_previous','instrument','exposure',
    'bootstrap_samples','alpha','effect_threshold','direction','bias_offset','min_first_stage_f','pretrend_tolerance'})
IDENTIFICATION = {'rct':('random_assignment','consistency','no_interference'),
    'did':('parallel_trends','no_anticipation','no_interference','stable_composition'),
    'iv':('exclusion','instrument_independence','monotonicity')}


def analyze(data,method,p,seed):
    alpha = number(p.get('alpha',0.05))
    draws = p.get('bootstrap_samples',400)
    outcome = p.get('outcome','y')
    bias = number(p.get('bias_offset',0))
    diagnostics = {'sample_size':len(data),'identification':'requires separate assumption certificates'}
    if method in ('rct','did'):
        treatment = p.get('treatment','treatment')
        grouped = {0:[],1:[]}
        for row in data:
            label = number(row.get(treatment))
            if label not in (0,1):
                raise ValidationError('Treatment must be coded 0/1')
            grouped[int(label)].append(row)
        def values(rows):
            ys = column(rows,outcome)
            if method=='did':
                return [a-b for a,b in zip(ys,column(rows,p.get('pre','pre')))]
            return ys
        treated,control = values(grouped[1]),values(grouped[0])
        estimate = mean_difference(treated,control)-bias
        interval = bootstrap([treated,control],lambda gs:mean_difference(*gs)-bias,seed,draws,alpha)
        diagnostics.update(treated=len(treated),control=len(control))
        if method=='did':
            previous = p.get('pre_previous','pre_previous')
            treated_trend = [a-b for a,b in zip(column(grouped[1],p.get('pre','pre')),column(grouped[1],previous))]
            control_trend = [a-b for a,b in zip(column(grouped[0],p.get('pre','pre')),column(grouped[0],previous))]
            pretrend = mean_difference(treated_trend,control_trend)
            if 'pretrend_tolerance' not in p:
                raise ValidationError('DiD requires a frozen, scale-specific pretrend_tolerance')
            tolerance = number(p['pretrend_tolerance'])
            if tolerance<0:
                raise ValidationError('Pretrend tolerance must be nonnegative')
            diagnostics.update(pretrend_difference=pretrend,pretrend_pass=abs(pretrend)<=tolerance,
                               pretrend_interpretation='Tolerance diagnostic does not prove parallel counterfactual trends')
    else:
        keys = (p.get('instrument','z'),p.get('exposure','x'),outcome)
        estimate_data = wald_iv(data,*keys)
        estimate = estimate_data['estimate']-bias
        interval = bootstrap([data],lambda gs:wald_iv(gs[0],*keys)['estimate']-bias,seed,draws,alpha)
        diagnostics.update(estimate_data)
        threshold = number(p.get('min_first_stage_f',10))
        diagnostics['first_stage_pass'] = estimate_data['perfect_first_stage'] or estimate_data['first_stage_f']>=threshold
    return {'estimate':estimate,'interval':interval,'estimand':'LATE' if method=='iv' else 'ATT' if method=='did' else 'ATE',
            'scientific_state':conclusion(estimate,interval,number(p.get('effect_threshold',0)),p.get('direction','positive')),
            'diagnostics':diagnostics,'uncertainty_components':{'sampling':interval,'counterfactual_bias_offset':bias,
                'unmeasured_confounding':'not estimated; identification and sensitivity required'}}


POLICY = Adapter('policy','policy',('rct','did','iv'),('CAUSAL_EFFECT','ASSOCIATION','MECHANISM'),PARAMS,analyze,IDENTIFICATION,
    limitations='RCT: independent rows. DiD: balanced two-period outcomes plus one pre-period diagnostic; no staggered adoption. IV: one instrument and one exposure; no multivariable 2SLS. No automatic causal identification.')
