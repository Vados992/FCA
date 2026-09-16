import math
import unittest
from fcea.analysis.statistics import bootstrap,mean_difference,adjust_pvalues,wald_iv,linear_fit,conclusion,equal_numeric
from fcea.adapters.registry import ADAPTERS
from fcea.adapters.supply import max_flow
from fcea.core.errors import ValidationError
from fcea.examples.builders import example
from tests.helpers import record


class NumericalTests(unittest.TestCase):
    def test_mean_difference_known_answer(self):
        self.assertEqual(mean_difference([3,5],[1,3]),2)

    def test_bootstrap_seed_reproducibility(self):
        groups=[[1,3,5,7],[2,4,6,8]]
        a=bootstrap(groups,lambda g:mean_difference(*g),123,200)
        self.assertEqual(a,bootstrap(groups,lambda g:mean_difference(*g),123,200))
        self.assertNotEqual(a['low'],bootstrap(groups,lambda g:mean_difference(*g),789,200)['low'])

    def test_bootstrap_resource_bounds(self):
        with self.assertRaises(ValidationError): bootstrap([[1,2]],lambda g:0,1,10000000)

    def test_holm_known_family(self):
        self.assertEqual(adjust_pvalues([0.01,0.04,0.03],'holm'),[0.03,0.06,0.06])

    def test_bh_known_family(self):
        self.assertEqual(adjust_pvalues([0.01,0.04,0.03],'benjamini_hochberg'),[0.03,0.04,0.04])

    def test_uncontrolled_multiple_tests_rejected(self):
        with self.assertRaises(ValidationError): adjust_pvalues([0.1,0.2],'none')

    def test_iv_recovers_exact_instrumented_effect(self):
        rows=[{'z':float(i),'x':2.0*i,'y':6.0*i+7} for i in range(20)]
        result=wald_iv(rows)
        self.assertAlmostEqual(result['estimate'],3)
        self.assertTrue(result['perfect_first_stage'])

    def test_constant_instrument_rejected(self):
        with self.assertRaises(ValidationError): wald_iv([{'z':1,'x':i,'y':i} for i in range(5)])

    def test_linear_regression_known_answer(self):
        result=linear_fit([1,2,3,4],[5,8,11,14])
        self.assertAlmostEqual(result['slope'],3);self.assertAlmostEqual(result['intercept'],2)

    def test_did_known_effect_and_pretrend(self):
        b=example('policy-did');p=record(b,'ProtocolSpec')['parameters']
        rows=[{'id':str(i),'treatment':i%2,'pre_previous':i,'pre':i+1,'y':i+2+3*(i%2)} for i in range(40)]
        result=ADAPTERS['policy'].analyze(rows,'did',p,123)
        self.assertEqual(result['estimate'],3)
        self.assertEqual(result['diagnostics']['pretrend_difference'],0)

    def test_market_charges_initial_trade_and_borrow(self):
        data=[{'id':str(i),'decision_at':f'2025-01-0{i+2}T00:00:00Z','signal_known_at':f'2025-01-0{i+1}T00:00:00Z',
            'return_end':f'2025-01-0{i+3}T00:00:00Z','position':-1,'asset_return':0} for i in range(2)]
        params={'training_end':'2024-01-01T00:00:00Z','test_start':'2025-01-01T00:00:00Z',
                'cost_bps':10,'slippage_bps':0,'annual_borrow_rate':0.252,'periods_per_year':252}
        r=ADAPTERS['market'].analyze(data,'backtest',params,1)
        self.assertAlmostEqual(r['diagnostics']['net_returns'][0],-0.002)
        self.assertAlmostEqual(r['diagnostics']['net_returns'][1],-0.001)
        self.assertAlmostEqual(r['diagnostics']['maximum_drawdown'],1-0.998*0.999)

    def test_maxflow_min_cut_known_answer(self):
        b=example('supply');edges=b['sources'][0]['content']['data']
        r=max_flow(edges,'S','T')
        self.assertEqual(r['max_flow'],9)
        for node,value in r['balances'].items():
            if node not in ('S','T'): self.assertAlmostEqual(value,0)

    def test_maxflow_disruption_changes_real_flow(self):
        b=example('supply');p=record(b,'ProtocolSpec')['parameters']|{'disabled_edges':['SA']}
        r=ADAPTERS['supply'].analyze(b['sources'][0]['content']['data'],'max_flow',p,1)
        self.assertEqual(r['estimate'],4)

    def test_invalid_capacity_rejected(self):
        with self.assertRaises(ValidationError): max_flow([{'from':'S','to':'T','capacity':-1}],'S','T')

    def test_science_incompatible_predictions_are_falsified(self):
        data=[{'observed':10,'predicted':0,'sigma':1}]
        r=ADAPTERS['science'].analyze(data,'prediction_check',{'max_standardized_residual':4},1)
        self.assertEqual(r['scientific_state'],'FALSIFIED')

    def test_physics_energy_and_recurrence(self):
        b=example('physics');r=ADAPTERS['physics'].analyze(b['sources'][0]['content']['data'],'oscillator_recurrence',record(b,'ProtocolSpec')['parameters'],1)
        self.assertLess(r['estimate'],1e-12);self.assertTrue(r['diagnostics']['model_valid'])

    def test_no_universal_negative_from_failed_search(self):
        self.assertEqual(conclusion(0,{'low':-1,'high':1},0,'two_sided'),'INCONCLUSIVE')

    def test_unknown_adapter_parameter_not_ignored(self):
        b=example('science')
        with self.assertRaises(ValidationError):
            ADAPTERS['science'].analyze(b['sources'][0]['content']['data'],'prediction_check',{'truth_probability':1},1)

    def test_reproduction_tolerance_is_explicit(self):
        self.assertFalse(equal_numeric(1.0,1.0001));self.assertTrue(equal_numeric(1.0,1.0001,atol=0.001))
