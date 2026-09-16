"""Run executable tests and independently replay all synthetic proof packets."""
from pathlib import Path
import argparse
import io
import json
import platform
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fcea.core.canonical import now
from fcea.examples.builders import NAMES, example
from fcea.service import Service, software_manifest, git_commit
from fcea.proof.packet import build_packet, verify_packet, reproduce_packet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='validation-output')
    args = parser.parse_args()
    target = Path(args.output)
    target.mkdir(parents=True, exist_ok=True)
    log = io.StringIO()
    started = time.perf_counter()
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'), top_level_dir=str(ROOT))
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    (target / 'tests.log').write_text(log.getvalue(), encoding='utf-8')
    report = {'profile': 'research-local', 'timestamp': now(), 'python': platform.python_version(),
              'platform': platform.platform(), 'git_commit': git_commit(), 'software': software_manifest(),
              'tests': {'run': result.testsRun, 'failures': len(result.failures),
                        'errors': len(result.errors), 'skipped': len(result.skipped)}, 'scenarios': [],
              'scope': 'Software verification with synthetic data; no independent external domain validation.'}
    with tempfile.TemporaryDirectory(prefix='fcea-validation-') as directory:
        with Service(directory) as service:
            for name in NAMES:
                bundle = example(name)
                service.import_bundle(bundle, 'validation-analyst')
                service.freeze(bundle['protocol_ref'], 'validation-analyst')
                run = service.run(bundle['protocol_ref'], 'validation-analyst')
                packet = build_packet(service, run['id'], public=True)
                checked = verify_packet(packet)
                replay = reproduce_packet(packet)
                outcome = {'name': name, 'synthetic': True, 'verdict': run['verdict']['scientific_state'],
                           'validity': run['verdict']['validity_state'], 'execution': run['verdict']['execution_state'],
                           'gates_passed': sum(g['outcome'] == 'PASS' for g in run['gates']),
                           'estimate': run['analysis']['estimate'] if run['analysis'] else None,
                           'interval': run['analysis'].get('interval') if run['analysis'] else None,
                           'packet_verified': checked['status'], 'packet_sha256': checked['sha256'],
                           'reproduction': replay}
                report['scenarios'].append(outcome)
                print(f"{name}: {outcome['verdict']}, {outcome['gates_passed']}/16 gates, {replay['status']}", flush=True)
            report['storage_integrity'] = service.verify()
    report['elapsed_seconds'] = round(time.perf_counter() - started, 3)
    passed = result.wasSuccessful() and all(s['gates_passed'] == 16 and s['verdict'] == 'SUPPORTED'
               and s['reproduction']['status'] == 'REPRODUCED' for s in report['scenarios'])
    report['status'] = 'PASS' if passed else 'FAIL'
    (target / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')
    print(f"{report['status']}: {result.testsRun} tests; {len(report['scenarios'])} scenarios; report: {target / 'report.json'}")
    if not passed:
        print(log.getvalue(), file=sys.stderr)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
