import math
import random
from statistics import fmean, variance, NormalDist

from fcea.core.errors import ValidationError


def number(value):
    if type(value) not in (str, int, float):
        raise ValidationError('Expected finite numeric observation')
    try:
        result = float(value)
    except ValueError as exc:
        raise ValidationError('Invalid numeric observation') from exc
    if not math.isfinite(result):
        raise ValidationError('NaN and infinity are forbidden')
    return result


def column(rows, key):
    try:
        return [number(row[key]) for row in rows]
    except (KeyError,TypeError) as exc:
        raise ValidationError(f'Missing numeric column: {key}') from exc


def quantile(values, q):
    if not values or not 0 <= q <= 1:
        raise ValidationError('Invalid quantile inputs')
    xs = sorted(values)
    index = (len(xs)-1)*q
    lower = int(index)
    return xs[lower] + (xs[min(lower+1,len(xs)-1)]-xs[lower])*(index-lower)


def bootstrap(groups, estimator, seed, samples=400, alpha=0.05):
    if type(samples) is not int or not 100 <= samples <= 2000 or not 0 < alpha < 1:
        raise ValidationError('Use 100–2000 bootstrap draws and 0 < alpha < 1')
    if not groups or any(len(g)<2 for g in groups) or sum(map(len,groups))*samples > 4_000_000:
        raise ValidationError('Bootstrap groups need >=2 rows; run exceeds local budget or is empty')
    rng = random.Random(seed)
    estimates = []
    for _ in range(samples):
        estimates.append(number(estimator([[g[rng.randrange(len(g))] for _ in g] for g in groups])))
    return {'low':quantile(estimates,alpha/2),'high':quantile(estimates,1-alpha/2),
            'level':1-alpha,'kind':'percentile_bootstrap','draws':samples,'seed':seed,
            'resampling_unit':'independent row within each declared group'}


def mean_difference(treated, control):
    if not treated or not control:
        raise ValidationError('Both treatment groups are required')
    return fmean(treated) - fmean(control)


def covariance(x,y):
    if len(x)!=len(y) or len(x)<2:
        raise ValidationError('Covariance requires paired observations')
    mx,my = fmean(x),fmean(y)
    return math.fsum((a-mx)*(b-my) for a,b in zip(x,y))/(len(x)-1)


def wald_iv(rows, instrument='z', exposure='x', outcome='y'):
    z,x,y = column(rows,instrument),column(rows,exposure),column(rows,outcome)
    zx,zz = covariance(z,x),covariance(z,z)
    if zz <= 0 or abs(zx) <= 1e-12:
        raise ValidationError('Instrument lacks variation or a first stage')
    slope = zx/zz
    intercept = fmean(x)-slope*fmean(z)
    sse = math.fsum((b-intercept-slope*a)**2 for a,b in zip(z,x))
    if len(x)<=2:
        raise ValidationError('At least three IV rows are required')
    explained = slope*slope*zz*(len(z)-1)
    # Infinite F is represented by perfect_first_stage, not invalid JSON Infinity.
    fstat = None if sse <= 1e-25 else explained/(sse/(len(x)-2))
    return {'estimate':covariance(z,y)/zx,'first_stage_f':fstat,
            'perfect_first_stage':sse<=1e-25,'first_stage_slope':slope}


def linear_fit(x,y):
    if len(x)<3 or len(x)!=len(y):
        raise ValidationError('Linear regression requires >=3 paired rows')
    xx = math.fsum((v-fmean(x))**2 for v in x)
    if xx <= 1e-20:
        raise ValidationError('Singular design')
    beta = math.fsum((a-fmean(x))*(b-fmean(y)) for a,b in zip(x,y))/xx
    intercept = fmean(y)-beta*fmean(x)
    residuals = [b-intercept-beta*a for a,b in zip(x,y)]
    sigma2 = math.fsum(v*v for v in residuals)/(len(x)-2)
    return {'slope':beta,'intercept':intercept,'standard_error':math.sqrt(sigma2/xx),
            'residuals':residuals,'rmse':math.sqrt(fmean(v*v for v in residuals))}


def adjust_pvalues(values, method):
    if any(not 0<=p<=1 for p in values):
        raise ValidationError('p-values must lie in [0,1]')
    n = len(values)
    if method == 'none':
        if n>1:
            raise ValidationError('Multiple statistical tests require a correction')
        return values[:]
    order = sorted(range(n),key=lambda i:values[i])
    out = [0.0]*n
    if method == 'holm':
        running = 0.0
        for rank,i in enumerate(order):
            running = max(running,min(1.0,(n-rank)*values[i]))
            out[i] = running
    elif method == 'benjamini_hochberg':
        running = 1.0
        for rank in range(n-1,-1,-1):
            i = order[rank]
            running = min(running,values[i]*n/(rank+1))
            out[i] = running
    else:
        raise ValidationError('Unknown multiple-testing policy')
    return out


def mean_z_pvalue(values, null=0.0):
    if len(values)<30:
        raise ValidationError('Asymptotic mean z-test requires at least 30 independent observations')
    se = math.sqrt(variance(values)/len(values))
    delta = abs(fmean(values)-null)
    return (1.0 if delta==0 else 0.0) if se==0 else math.erfc(delta/(se*math.sqrt(2)))


def conclusion(estimate, interval, threshold, direction):
    if direction not in ('positive','negative','two_sided'):
        raise ValidationError('direction must be positive, negative, or two_sided')
    if threshold < 0:
        raise ValidationError('Effect threshold is an absolute nonnegative magnitude')
    lo,hi = interval['low'],interval['high']
    support = (lo>threshold if direction=='positive' else hi < -threshold if direction=='negative'
               else lo>threshold or hi < -threshold)
    incompatible = (hi < -threshold if direction=='positive' else lo>threshold if direction=='negative' else False)
    return 'SUPPORTED' if support else 'FALSIFIED' if incompatible else 'INCONCLUSIVE'


def sign_stability(values, reference):
    sign = lambda x: (x>0)-(x<0)
    return sum(sign(x)==sign(reference) for x in values)/len(values) if values else None


def equal_numeric(a,b,atol=0.0,rtol=0.0):
    if type(a) in (int,float) and type(b) in (int,float):
        return math.isfinite(a) and math.isfinite(b) and abs(a-b)<=atol+rtol*abs(b)
    if type(a) is not type(b):
        return False
    if isinstance(a,dict):
        return a.keys()==b.keys() and all(equal_numeric(a[k],b[k],atol,rtol) for k in a)
    if isinstance(a,list):
        return len(a)==len(b) and all(equal_numeric(x,y,atol,rtol) for x,y in zip(a,b))
    return a==b
