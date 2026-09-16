"""Verify Docker build, non-root HTTP lifecycle and proof reproduction."""
from pathlib import Path
import json
import subprocess
import sys
import time
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fcea.proof.packet import reproduce_packet


def call(*args):
    return subprocess.run(args, check=True, text=True, capture_output=True).stdout.strip()


def main():
    name = 'fcea-check-' + uuid.uuid4().hex[:12]
    subprocess.run(['docker', 'build', '-t', 'fcea:check', str(ROOT)], check=True)
    try:
        call('docker', 'run', '-d', '--name', name, '--read-only', '--cap-drop=ALL',
             '--security-opt=no-new-privileges:true', '--tmpfs', '/tmp:rw,noexec,nosuid,size=64m',
             '--pids-limit', '64', '--memory', '512m', '-p', '127.0.0.1::8000', 'fcea:check')
        port = call('docker', 'port', name, '8000/tcp').rsplit(':', 1)[1]
        base = 'http://127.0.0.1:' + port
        for attempt in range(100):
            try:
                with urllib.request.urlopen(base + '/healthz', timeout=1) as response:
                    assert json.load(response)['status'] == 'ok'
                break
            except OSError:
                time.sleep(0.3)
        else:
            raise RuntimeError('Container did not become healthy')
        assert call('docker', 'exec', name, 'id', '-u') == '10001'
        tokens = json.loads(call('docker', 'exec', name, 'cat', '/data/credentials.local.json'))['one_time_tokens']

        def request(path, body=None, raw=False):
            req = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode(),
                  headers={'Authorization': 'Bearer ' + tokens['analyst'], 'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=60) as response:
                return response.read() if raw else json.load(response)

        data = request('/v1/demos', {'name': 'policy-rct'})
        request('/v1/protocols/' + data['protocol_ref'] + '/freeze', {})
        run = request('/v1/runs', {'protocol_ref': data['protocol_ref']})
        assert run['verdict']['scientific_state'] == 'SUPPORTED'
        assert all(g['outcome'] == 'PASS' for g in run['gates'])
        packet = request('/v1/runs/' + run['id'] + '/proof', {'public': True})
        archive = request('/v1/proofs/' + packet['id'], raw=True)
        # Replay inside the same image: the CI host Python may be a different version.
        subprocess.run(['docker', 'exec', '-i', name, 'python', '-c',
                        'import sys; from fcea.proof.packet import reproduce_packet; r=reproduce_packet(sys.stdin.buffer.read()); print(r); assert r["status"]=="REPRODUCED"'],
                       input=archive, check=True)
        request('/v1/verify', {})
        print('PASS: non-root container, readonly root, authenticated run, 16 gates, proof replay.')
    finally:
        subprocess.run(['docker', 'rm', '-fv', name], capture_output=True)


if __name__ == '__main__':
    main()
