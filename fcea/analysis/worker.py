"""Isolated interpreter entry point: JSON in / JSON out; no plugins or user code."""
import sys
from fcea.core.canonical import canonical,loads
from fcea.adapters.registry import analyze_request


def main():
    request=loads(sys.stdin.buffer.read(16*1024*1024+1))
    result=analyze_request(request)
    sys.stdout.buffer.write(canonical(result))


if __name__=='__main__':
    main()
