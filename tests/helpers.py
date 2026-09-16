from copy import deepcopy
import tempfile
import unittest
from fcea.service import Service
from fcea.examples.builders import example


def record(bundle,kind):
    return next(r['payload'] for r in bundle['records'] if r['kind']==kind)


def replace_ids(bundle,old,new):
    import json
    return json.loads(json.dumps(bundle).replace(old,new))


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.service=Service(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(self.service.close)

    def execute(self,bundle=None,actor='analyst'):
        bundle=bundle or example('policy-rct')
        self.service.import_bundle(bundle,actor)
        self.service.freeze(bundle['protocol_ref'],actor)
        return self.service.run(bundle['protocol_ref'],actor)

    def gate(self,run,identifier):
        return next(g for g in run['gates'] if g['gate_id']==identifier)
