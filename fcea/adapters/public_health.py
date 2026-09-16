from .base import Adapter
from .policy import PARAMS, IDENTIFICATION, analyze

PUBLIC_HEALTH = Adapter('public_health','public_health',('rct',),('CAUSAL_EFFECT','ASSOCIATION'),
    PARAMS,analyze,{'rct':IDENTIFICATION['rct']},
    ('ethics_approval','measurement_validity','selection_protocol'),
    limitations='Independent-row randomized-trial research endpoint only. Not a medical device, treatment recommender, safety adjudicator, or observational clinical-causality engine.')
