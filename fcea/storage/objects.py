from pathlib import Path
import os
import re

from fcea.core.canonical import digest
from fcea.core.errors import IntegrityError, ValidationError


class RawStore:
    MAX_BYTES = 16 * 1024 * 1024

    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, sha):
        if not isinstance(sha, str) or not re.fullmatch('[0-9a-f]{64}', sha):
            raise ValidationError('Invalid content address')
        return self.root / sha[:2] / sha

    def put(self, data):
        if not isinstance(data, bytes) or len(data) > self.MAX_BYTES:
            raise ValidationError('Source must be bytes, at most 16 MiB')
        sha = digest(data)
        path = self.path(sha)
        path.parent.mkdir(exist_ok=True)
        try:
            with path.open('xb') as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            path.chmod(0o444)
        except FileExistsError:
            self.get(sha)
        return sha

    def get(self, sha):
        path = self.path(sha)
        if path.is_symlink() or path.parent.is_symlink():
            raise IntegrityError('Symlinks are forbidden in raw storage')
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise IntegrityError(f'Raw object unavailable: {sha}') from exc
        if digest(data) != sha:
            raise IntegrityError(f'Raw object hash mismatch: {sha}')
        return data
