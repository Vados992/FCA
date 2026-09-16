import math
import random
from datetime import datetime,timedelta,timezone
from fcea.adapters.registry import ADAPTERS
from fcea.core.errors import ValidationError

NAMES=('policy-rct','policy-did','policy-iv','science','market','supply','climate','physics','integrity','public-health')


def example(name):
    if name not in NAMES: raise ValidationError('Unknown built-in example')
    rng=random.Random(9281)
    adapter_id='public_health' if name=='public-health' else name.split('-')[0]
    adapter=ADAPTERS[adapter_id]
    method=name.split('-')[1] if name.startswith('policy-') else adapter.methods[0]
    n=80; parameters={}; estimand=None
    if adapter_id in ('policy','public_health'):
        labels=[0,1]*(n//2); rng.shuffle(labels)
        data=[]
        for i,treatment in enumerate(labels):
            latent=rng.gauss(4,0.6); noise=rng.gauss(0,0.3)
            if method=='iv':
                z=rng.gauss(0,1); x=1.5*z+rng.gauss(0,0.25); y=2*x+rng.gauss(0,0.15)
                row={'id':f'row-{i}','z':z,'x':x,'y':y}
            else:
                row={'id':f'row-{i}','treatment':treatment,'y':latent+1+2*treatment+noise,
                     'pre':latent,'pre_previous':latent-1+rng.gauss(0,0.02)}
            data.append(row)
        parameters={'bootstrap_samples':200,'effect_threshold':0.2,'direction':'positive','alpha':0.05,'bias_offset':0.0}
        if method=='did': parameters['pretrend_tolerance']=0.1
        if method=='iv': parameters['min_first_stage_f']=10
        estimand='LATE' if method=='iv' else 'ATT' if method=='did' else 'ATE'
        changes={'bias_offset':0.1}; claim_type='CAUSAL_EFFECT'
    elif adapter_id=='science':
        data=[{'id':f'row-{i}','observed':1+i/10+rng.gauss(0,0.01),'predicted':1+i/10,'sigma':0.05} for i in range(40)]
        parameters={'max_standardized_residual':4,'prediction_offset':0.0}
        changes={'prediction_offset':0.01}; claim_type='MODEL_COMPATIBILITY'
    elif adapter_id=='market':
        start=datetime(2025,1,2,tzinfo=timezone.utc)
        data=[]
        for i in range(40):
            t=start+timedelta(days=i)
            data.append({'id':f'row-{i}','decision_at':t.isoformat(),'signal_known_at':(t-timedelta(hours=1)).isoformat(),
                'return_end':(t+timedelta(days=1)).isoformat(),'position':1.0,'asset_return':0.004+rng.gauss(0,0.001)})
        parameters={'training_end':'2024-12-01T00:00:00Z','test_start':'2025-01-01T00:00:00Z',
                    'cost_bps':5,'slippage_bps':2,'periods_per_year':365,'minimum_return':0}
        changes={'cost_bps':25}; claim_type='ASSOCIATION'
    elif adapter_id=='supply':
        data=[{'id':'SA','from':'S','to':'A','capacity':6},{'id':'SB','from':'S','to':'B','capacity':4},
              {'id':'AT','from':'A','to':'T','capacity':5},{'id':'BT','from':'B','to':'T','capacity':4},
              {'id':'AB','from':'A','to':'B','capacity':1}]
        parameters={'source':'S','sink':'T','required_flow':3,'disabled_edges':[]}
        changes={'disabled_edges':['SA']}; claim_type='MODEL_COMPATIBILITY'
    elif adapter_id=='climate':
        data=[{'id':f'row-{i}','fingerprint':i/20,'observed':0.3+1.2*i/20+rng.gauss(0,0.05)} for i in range(60)]
        parameters={'alpha':0.05,'forcing_scale':1.0}; changes={'forcing_scale':1.1}; claim_type='ASSOCIATION'
    elif adapter_id=='physics':
        data=[{'id':f'row-{i}','t':i*2*math.pi/64,'x':math.cos(i*2*math.pi/64),'v':-math.sin(i*2*math.pi/64)} for i in range(65)]
        parameters={'omega':1.0,'mass':1.0,'closure_tolerance':1e-6,'energy_relative_tolerance':1e-6,'model_residual_tolerance':1e-6}
        changes={'mass':1.1}; claim_type='EXISTENTIAL'
    else:
        data=[{'id':'edge-1','from':'Entity-A','to':'Contract-X','relation':'recorded_contract'},
              {'id':'edge-2','from':'Contract-X','to':'Entity-B','relation':'recorded_payment'}]
        parameters={'start':'Entity-A','end':'Entity-B','max_hops':6}; changes={'max_hops':3}; claim_type='OBSERVATION'
    prefix=name.replace('-','_')
    ref=lambda value:prefix+'.'+value
    assumption_keys=list(adapter.validity_assumptions)+list(adapter.identification.get(method,()))
    if method=='iv': assumption_keys+=['instrument_relevance_documentation']
    assumption_keys=list(dict.fromkeys(assumption_keys))
    records=[]
    def add(record_kind,**payload): records.append({'kind':record_kind,'payload':payload})
    source_data={'data':data,'negative_control':[{'id':f'nc-{i}','zero':0.0} for i in range(40)],
        'design':[{'id':'design','synthetic':True,'generator':'fcea.examples.builders.v1','seed':9281,
                   'assumptions':assumption_keys,'note':'Declared properties of the synthetic generator, not empirical certificates.'}]}
    source={'metadata':{'id':ref('source'),'origin':'synthetic://fcea/'+name,'known_at':'2025-12-31T00:00:00Z',
        'legal_basis':'Author-generated synthetic benchmark data','media_type':'application/json',
        'redistributable':True,'synthetic':True,'dependency_keys':['fcea-synthetic-generator-seed-9281']},'content':source_data}
    add('ScopeSpec',id=ref('scope'),domains=[adapter.domain],populations=['synthetic-'+name],
        regimes=['synthetic'],model_families=[adapter_id+'.'+method],precision='synthetic-units-v1',
        start='2025-01-01T00:00:00Z',end='2026-01-01T00:00:00Z',assumptions=assumption_keys)
    for identifier,selector in [('data','/data'),('negative','/negative_control'),('design','/design')]:
        add('EvidenceItem',id=ref(identifier),source_ref=ref('source'),scope_ref=ref('scope'),
            known_at='2025-12-31T00:00:00Z',transform='json.pointer.v1',selector=selector,units='1')
    for key in assumption_keys:
        add('AssumptionSpec',id=ref('assumption.'+key),key=key,statement=key.replace('_',' '),status='SUPPORTED',
            evidence_refs=[ref('design')],rationale='Synthetic generator fixes this condition; independent domain validation is required for real data.',
            causal_only=key in adapter.identification.get(method,()))
    add('ImplementationSpec',id=ref('implementation'),adapter_id=adapter_id,adapter_version='1.0.0',method=method,core_version='1.0.0')
    add('ModelSpec',id=ref('model'),family=adapter_id+'.'+method,scope_ref=ref('scope'),implementation_ref=ref('implementation'),
        equations='See docs/METHODS.md and the pinned implementation.',assumption_refs=[ref('assumption.'+k) for k in assumption_keys],estimand=estimand,
        causal_graph=({'z':[],'x':['z'],'y':['x']} if method=='iv' else {'treatment':[],'y':['treatment']}) if adapter_id in ('policy','public_health') else {})
    add('TestSpec',id=ref('test.negative'),target='model',kind='negative_control',evidence_ref=ref('negative'),
        metric='max_abs',column='zero',accept='abs_lte',threshold=1e-9)
    add('HypothesisSpec',id=ref('hypothesis'),proposition='The frozen operational test passes in the synthetic scope.',
        null='No effect or incompatibility under the specified operational metric.',
        alternatives=['Generator/model mismatch','Measurement or selection error','Counterfactual sensitivity'],
        falsification_tests=[ref('test.negative')])
    add('ClaimSpec',id=ref('claim'),proposition=f'Synthetic {name} benchmark meets its declared operational criterion.',
        claim_type=claim_type,scope_ref=ref('scope'),hypothesis_ref=ref('hypothesis'),model_ref=ref('model'),
        mandatory_dependencies=[ref('data')])
    add('EvidenceLink',id=ref('support'),evidence_ref=ref('data'),claim_ref=ref('claim'),role='supports')
    add('CounterfactualSpec',id=ref('counterfactual'),description='Preregistered alternative parameter scenario for this synthetic benchmark.',
        changes=changes,evidence_refs=[ref('design')])
    add('ProtocolSpec',id=ref('protocol'),research_question=f'Reproduce the {name} synthetic operational test.',
        claim_ref=ref('claim'),dataset_ref=ref('data'),cutoff='2026-01-01T00:00:00Z',parameters=parameters,seed=3819,
        counterfactual_refs=[ref('counterfactual')],test_refs=[ref('test.negative')],
        robustness_sign_required=adapter_id not in ('science','physics'),registration='retrospective')
    return {'schema_version':'1.0','description':'SYNTHETIC; no empirical validation claim.',
            'sources':[source],'records':records,'protocol_ref':ref('protocol'),
            'expected':{'scientific_state':'SUPPORTED','validity_state':'VALID','all_gates':'PASS'}}
