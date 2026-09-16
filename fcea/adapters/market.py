import math
from statistics import fmean,stdev
from fcea.core.canonical import timestamp
from fcea.core.errors import ValidationError
from fcea.analysis.statistics import number
from .base import Adapter


def analyze(data,method,p,seed):
    periods = number(p.get('periods_per_year',252))
    cost = number(p.get('cost_bps',5))/10000
    slippage = number(p.get('slippage_bps',2))/10000
    borrow = number(p.get('annual_borrow_rate',0))/periods if periods>0 else -1
    riskfree = number(p.get('riskfree_per_period',0))
    leverage = number(p.get('max_abs_position',1))
    if min(periods,cost,slippage,borrow,leverage)<0 or periods==0 or leverage==0:
        raise ValidationError('Invalid market cost/frequency/leverage parameter')
    if 'test_start' not in p or 'training_end' not in p:
        raise ValidationError('Declare separate training_end and test_start')
    if timestamp(p['training_end'])>=timestamp(p['test_start']):
        raise ValidationError('Training must end before holdout starts')
    net,gross,turnover,leaks = [],[],[],[]
    previous,wealth,peak,maxdd = 0.0,1.0,1.0,0.0
    prior_end = None
    for i,row in enumerate(data):
        decision,known,end = [timestamp(row[k]) for k in ('decision_at','signal_known_at','return_end')]
        if known>decision or end<=decision or (prior_end and decision<prior_end):
            leaks.append(i)
        if decision<timestamp(p['test_start']):
            raise ValidationError('All supplied rows must belong to the frozen holdout')
        prior_end = end
        pos,ret = number(row['position']),number(row['asset_return'])
        if abs(pos)>leverage or ret < -1:
            raise ValidationError('Position/return outside model validity')
        traded = abs(pos-previous)
        g = pos*ret
        n = g-traded*(cost+slippage)-max(-pos,0)*borrow
        if n<=-1:
            raise ValidationError('Portfolio insolvency: simple-return compounding model invalid')
        net.append(n); gross.append(g); turnover.append(traded)
        previous=pos
        wealth*=1+n
        peak=max(peak,wealth)
        maxdd=max(maxdd,1-wealth/peak)
    if len(net)<2:
        raise ValidationError('At least two holdout periods required')
    excess = [v-riskfree for v in net]
    sd=stdev(excess)
    return {'estimate':wealth-1,'metric':'net_holdout_total_return',
        'scientific_state':'SUPPORTED' if wealth-1>number(p.get('minimum_return',0)) else 'NOT_SUPPORTED',
        'diagnostics':{'net_returns':net,'gross_returns':gross,'turnover':sum(turnover),
            'sharpe':fmean(excess)/sd*math.sqrt(periods) if sd>0 else None,'maximum_drawdown':maxdd,
            'periods':len(net),'temporal_leak_rows':leaks,'terminal_position':previous,
            'liquidation':'no terminal liquidation; terminal holding is disclosed'},
        'uncertainty_components':{'sampling':'descriptive backtest; no iid return confidence interval',
            'cost_sensitivity':'counterfactual ensemble','survivorship':'requires dataset certificate'}}


MARKET = Adapter('market','market',('backtest',),('ASSOCIATION',),
    frozenset({'periods_per_year','cost_bps','slippage_bps','annual_borrow_rate','riskfree_per_period',
               'max_abs_position','test_start','training_end','minimum_return'}),analyze,{},
    ('point_in_time_universe','survivorship_control','capacity_assessment'),
    limitations='Single-asset precomputed positions and simple returns in a frozen holdout; no live broker, execution, portfolio optimizer, or forward profitability claim.')
