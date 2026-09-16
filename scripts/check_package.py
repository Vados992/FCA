"""Build a wheel and verify it outside the checkout in a clean virtual environment.

Build prerequisites: python -m pip install -r requirements-build.txt
No runtime dependencies or network access are used for the isolated install.
"""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import venv

ROOT = Path(__file__).resolve().parents[1]


def call(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, text=True, **kwargs)


def main():
    with tempfile.TemporaryDirectory(prefix='fcea-package-') as directory:
        tmp = Path(directory)
        wheels = tmp / 'wheels'
        wheels.mkdir()
        call([sys.executable, '-m', 'pip', 'wheel', '--no-deps', '--no-build-isolation', '--wheel-dir', str(wheels), str(ROOT)])
        wheel = next(wheels.glob('fcea-*.whl'))
        venv.EnvBuilder(with_pip=True).create(tmp / 'venv')
        python = tmp / 'venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        call([str(python), '-m', 'pip', 'install', '--no-index', '--no-deps', str(wheel)], cwd=tmp)
        probe = "from pathlib import Path; import fcea; from fcea.core.contracts import CONTRACTS; from fcea.examples.builders import NAMES; from fcea.service import software_manifest; p=Path(fcea.__file__).parent; assert (p/'storage/001.sql').is_file(); assert (p/'dashboard/app.js').is_file(); print(fcea.__version__,len(CONTRACTS),len(NAMES),software_manifest()['code_digest'])"
        print('Installed wheel:', call([str(python), '-I', '-c', probe], cwd=tmp).stdout.strip())
        result = call([str(python), '-I', '-m', 'fcea', '--data-dir', str(tmp / 'data'), 'demo', '--all'], cwd=tmp)
        values = json.loads(result.stdout)['results']
        assert len(values) == 10 and all(r['gates_passed'] == 16 for r in values)
        call([str(python), '-I', '-m', 'fcea', '--data-dir', str(tmp / 'data'), 'verify'], cwd=tmp)
        print('PASS: clean installed wheel, all 10 scenarios, all 16 gates, integrity verified.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
