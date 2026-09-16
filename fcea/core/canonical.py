"""Canonical JSON, finite-number checks, and timezone-aware timestamps."""
import hashlib
import json
import math
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum

from .errors import ValidationError


def plain(value):
    if is_dataclass(value):
        return plain(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        if any(not isinstance(k, str) for k in value):
            raise ValidationError("JSON object keys must be strings")
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise ValidationError("Non-finite number is not admissible")
    if value is None or type(value) in (str, int, float, bool):
        return value
    raise ValidationError(f"Unsupported JSON value: {type(value).__name__}")


def canonical(value):
    return json.dumps(plain(value), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else canonical(value)).hexdigest()


def loads(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValidationError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        result = json.loads(data, object_pairs_hook=pairs,
                            parse_constant=lambda x: (_ for _ in ()).throw(
                                ValidationError(f"Invalid numeric constant: {x}")))
        plain(result)
        return result
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise ValidationError(f"Invalid JSON: {exc}") from exc


def timestamp(value):
    if not isinstance(value, str):
        raise ValidationError("Timestamp must be an ISO 8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"Invalid timestamp: {value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValidationError("Timestamp requires an explicit timezone")
    return parsed.astimezone(timezone.utc)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
