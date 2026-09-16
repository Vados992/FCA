from copy import deepcopy
from pathlib import Path
import io
import zipfile
from fcea.core.canonical import canonical,digest,loads
from fcea.core.errors import ValidationError,IntegrityError,ConflictError
from fcea.examples.builders import example
from fcea.proof.packet import build_packet,verify_packet,reproduce_packet,read_packet
from fcea.review import review,release
from fcea.security.signing import verify
from fcea.operations import backup,restore
from fcea.service import Service
from tests.helpers import Case,record


class ProofReviewTests(Case):
    def test_proof_roundtrip_reconstructs_full_gate_chain(self):
        run=self.execute();packet=build_packet(self.service,run['id'],True)
        self.assertEqual(verify_packet(packet)['status'],'VERIFIED')
        result=reproduce_packet(packet)
        self.assertEqual(result['status'],'REPRODUCED')
        self.assertTrue(result['gates'] and result['falsification'] and result['counterfactuals'])

    def test_proof_contains_required_reviewable_objects(self):
        r=self.execute();files=read_packet(build_packet(self.service,r['id']))
        for name in ('claim.json','hypothesis.json','scope.json','timeline.json','evidence_manifest.json',
            'contradictory_evidence.json','source_dependency.json','model_spec.json','assumptions.json',
            'counterfactuals.json','causal_graph.json','closure_results.json','gate_records.json',
            'falsification_results.json','sensitivity.json','run_manifest.json','software_manifest.json',
            'review_record.json','hashes.txt','verdict.json','reproduction.md'):
            self.assertIn(name,files)

    def test_modified_packet_member_detected(self):
        r=self.execute();packet=build_packet(self.service,r['id']);src=zipfile.ZipFile(io.BytesIO(packet));out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as dst:
            for name in src.namelist(): dst.writestr(name,b'{}' if name=='verdict.json' else src.read(name))
        src.close()
        with self.assertRaises(IntegrityError): verify_packet(out.getvalue())

    def test_zip_path_traversal_rejected_before_extraction(self):
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as dst: dst.writestr('../outside','evil')
        with self.assertRaises(IntegrityError): verify_packet(out.getvalue())

    def test_restricted_source_blocks_public_export(self):
        b=example('policy-rct');b['sources'][0]['metadata']['redistributable']=False;r=self.execute(b)
        with self.assertRaises(ValidationError): build_packet(self.service,r['id'],True)
        packet=build_packet(self.service,r['id'])
        self.assertFalse(verify_packet(packet)['self_contained'])
        self.assertEqual(reproduce_packet(packet)['status'],'BLOCKED')

    def test_packet_does_not_leak_unrelated_graph_ids(self):
        r=self.execute(example('science'));self.service.import_bundle(example('integrity'))
        graph=loads(read_packet(build_packet(self.service,r['id']))['causal_graph.json'])
        self.assertNotIn('integrity',str(graph))

    def test_human_review_cannot_mutate_machine_verdict(self):
        r=self.execute();before=self.service.db.get(r['id'])['verdict']
        review(self.service,r['id'],'DOWNGRADE','Insufficient basis for the intended interpretation.','independent')
        self.assertEqual(self.service.db.get(r['id'])['verdict'],before)

    def test_release_requires_independent_reviewer(self):
        r=self.execute(actor='analyst')
        review(self.service,r['id'],'APPROVE','Self review.','analyst')
        with self.assertRaises(ValidationError): release(self.service,r['id'],b'k'*32,'publisher')

    def test_high_impact_requires_two_reviewers(self):
        b=example('policy-rct');record(b,'ClaimSpec')['high_impact']=True;r=self.execute(b)
        review(self.service,r['id'],'APPROVE','First independent review.','reviewer1')
        with self.assertRaises(ValidationError): release(self.service,r['id'],b'k'*32,'publisher')
        review(self.service,r['id'],'APPROVE','Second independent review.','reviewer2')
        result=release(self.service,r['id'],b'k'*32,'publisher')
        self.assertTrue(verify(result['content'],result['authentication'],b'k'*32))

    def test_hmac_authentication_detects_wrong_key_and_payload(self):
        r=self.execute();review(self.service,r['id'],'APPROVE','Synthetic engineering review.','reviewer')
        result=release(self.service,r['id'],b'k'*32,'publisher')
        with self.assertRaises(IntegrityError): verify(result['content'],result['authentication'],b'z'*32)
        changed=result['content']|{'visibility':'public'}
        with self.assertRaises(IntegrityError): verify(changed,result['authentication'],b'k'*32)

    def test_reviewer_downgrade_blocks_release(self):
        r=self.execute();review(self.service,r['id'],'DOWNGRADE','Scope interpretation is too broad.','reviewer')
        with self.assertRaises(ValidationError): release(self.service,r['id'],b'k'*32,'publisher')

    def test_failed_gate_prevents_release_despite_approval(self):
        b=example('policy-rct');record(b,'ProtocolSpec')['mode']='exploratory';r=self.execute(b)
        review(self.service,r['id'],'APPROVE','Approval cannot override a gate.','reviewer')
        with self.assertRaises(ValidationError): release(self.service,r['id'],b'k'*32,'publisher')

    def test_backup_restore_preserves_objects_raw_and_audit(self):
        r=self.execute();root=Path(self.tmp.name)
        backup(self.service,root/'backup')
        before=self.service.verify()
        restore(root/'backup',root/'restored')
        with Service(root/'restored') as s:
            self.assertEqual(s.verify(),before);self.assertEqual(s.db.get(r['id'])['verdict'],r['verdict'])

    def test_restore_cannot_overwrite_live_directory(self):
        self.execute();root=Path(self.tmp.name);backup(self.service,root/'backup')
        with self.assertRaises(ConflictError): restore(root/'backup',root)

    def test_corrupted_backup_is_rejected(self):
        self.execute();root=Path(self.tmp.name);backup(self.service,root/'backup')
        (root/'backup'/'fcea.sqlite3').write_bytes(b'invalid')
        with self.assertRaises(IntegrityError): restore(root/'backup',root/'restored')
