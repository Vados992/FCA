"""Strict wire contracts. References point to immutable IDs, never mutable 'latest'."""
from dataclasses import dataclass, field, fields, MISSING
from typing import Any, Literal, get_args, get_origin, get_type_hints, Union
import re
import types

from .canonical import plain, timestamp
from .errors import ValidationError


@dataclass(frozen=True, kw_only=True)
class Record:
    id: str
    version: int = 1
    supersedes: str | None = None


@dataclass(frozen=True, kw_only=True)
class ScopeSpec(Record):
    domains: list[str]
    populations: list[str]
    regimes: list[str]
    model_families: list[str]
    precision: str
    start: str | None = None
    end: str | None = None
    assumptions: list[str] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True)
class SourceSpec(Record):
    origin: str
    known_at: str
    legal_basis: str
    sha256: str
    media_type: Literal["application/json", "text/csv", "text/plain", "application/octet-stream"]
    acquired_at: str
    redistributable: bool = False
    parent_refs: list[str] = field(default_factory=list)
    dependency_keys: list[str] = field(default_factory=list)
    synthetic: bool = False


@dataclass(frozen=True, kw_only=True)
class EvidenceItem(Record):
    source_ref: str
    scope_ref: str
    known_at: str
    transform: Literal["json.pointer.v1", "csv.rows.v1", "text.v1"]
    selector: str = ""
    value: Any = None
    units: str = "1"
    parent_refs: list[str] = field(default_factory=list)
    valid_start: str | None = None
    valid_end: str | None = None
    uncertainty: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class HypothesisSpec(Record):
    proposition: str
    null: str
    alternatives: list[str]
    falsification_tests: list[str]


@dataclass(frozen=True, kw_only=True)
class ClaimSpec(Record):
    proposition: str
    claim_type: Literal["OBSERVATION", "ASSOCIATION", "CAUSAL_EFFECT", "MECHANISM", "EXISTENTIAL", "UNIVERSAL_NEGATIVE", "MODEL_COMPATIBILITY", "INTENT", "LEGAL_GUILT"]
    scope_ref: str
    hypothesis_ref: str
    model_ref: str
    mandatory_dependencies: list[str]
    proof_routes: list[list[str]] = field(default_factory=list)
    optional_dependencies: list[str] = field(default_factory=list)
    required_gates: list[str] = field(default_factory=list)
    prohibited_inferences: list[str] = field(default_factory=lambda: ["intent", "legal_guilt", "universal_generalization"])
    high_impact: bool = False
    closure_ref: str | None = None
    coverage_ref: str | None = None


@dataclass(frozen=True, kw_only=True)
class EvidenceLink(Record):
    evidence_ref: str
    claim_ref: str
    role: Literal["supports", "contradicts", "neutral"]
    material: bool = True


@dataclass(frozen=True, kw_only=True)
class AssumptionSpec(Record):
    key: str
    statement: str
    status: Literal["SUPPORTED", "FAILED", "UNKNOWN"]
    evidence_refs: list[str]
    rationale: str
    causal_only: bool = False


@dataclass(frozen=True, kw_only=True)
class ImplementationSpec(Record):
    adapter_id: str
    adapter_version: str
    method: str
    core_version: str


@dataclass(frozen=True, kw_only=True)
class ModelSpec(Record):
    family: str
    scope_ref: str
    implementation_ref: str
    equations: str
    assumption_refs: list[str]
    estimand: str | None = None
    validity_predicates: list[dict[str, Any]] = field(default_factory=list)
    causal_graph: dict[str, list[str]] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class CounterfactualSpec(Record):
    description: str
    changes: dict[str, Any]
    evidence_refs: list[str]


@dataclass(frozen=True, kw_only=True)
class TestSpec(Record):
    target: Literal["hypothesis", "model"]
    kind: Literal["falsifier", "negative_control", "placebo"]
    evidence_ref: str
    metric: Literal["mean", "max_abs", "difference", "count", "z_pvalue"]
    column: str
    accept: Literal["lte", "gte", "abs_lte", "no_rejection"]
    threshold: float
    critical: bool = True
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class EventSpec(Record):
    entity: str
    earliest: str
    latest: str
    known_at: str
    evidence_refs: list[str]


@dataclass(frozen=True, kw_only=True)
class TemporalRelation(Record):
    from_ref: str
    to_ref: str
    relation: Literal["precedes", "overlaps", "contains", "uncertain_order"]


@dataclass(frozen=True, kw_only=True)
class ClosureSpec(Record):
    closure_type: Literal["time_unrolled_feedback"]
    event_refs: list[str]
    edge_verdict_refs: list[str]


@dataclass(frozen=True, kw_only=True)
class CoverageSpec(Record):
    scope_ref: str
    universe: list[str]
    observations_ref: str
    key_column: str
    witness_column: str
    justification_ref: str


@dataclass(frozen=True, kw_only=True)
class ResolutionSpec(Record):
    contradiction_link_ref: str
    evidence_refs: list[str]
    rationale: str
    review_ref: str


@dataclass(frozen=True, kw_only=True)
class ProtocolSpec(Record):
    research_question: str
    claim_ref: str
    dataset_ref: str
    cutoff: str
    parameters: dict[str, Any]
    seed: int
    counterfactual_refs: list[str]
    test_refs: list[str]
    temporal_relation_refs: list[str] = field(default_factory=list)
    mode: Literal["confirmatory", "exploratory"] = "confirmatory"
    registration: Literal["retrospective", "prospective"] = "retrospective"
    required_gates: list[str] = field(default_factory=list)
    minimum_independent_clusters: int = 1
    multiplicity: Literal["none", "holm", "benjamini_hochberg"] = "holm"
    alpha: float = 0.05
    robustness_sign_required: bool = True
    reproduction_atol: float = 0.0
    reproduction_rtol: float = 0.0
    required_reviewers: int = 1
    edge_from_ref: str | None = None
    edge_to_ref: str | None = None


CONTRACTS = {c.__name__: c for c in [ScopeSpec, SourceSpec, EvidenceItem, HypothesisSpec, ClaimSpec,
    EvidenceLink, AssumptionSpec, ImplementationSpec, ModelSpec, CounterfactualSpec, TestSpec,
    EventSpec, TemporalRelation, ClosureSpec, CoverageSpec, ResolutionSpec, ProtocolSpec]}
ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}$"


def typed(value, annotation, path):
    origin, args = get_origin(annotation), get_args(annotation)
    if annotation is Any:
        return plain(value)
    if origin in (Union, types.UnionType):
        for candidate in args:
            try:
                return typed(value, candidate, path)
            except ValidationError:
                continue
        raise ValidationError(f"{path}: incompatible value")
    if origin is Literal:
        if value not in args or type(value) is not type(args[0]):
            raise ValidationError(f"{path}: expected one of {args}")
        return value
    if origin is list:
        if type(value) is not list:
            raise ValidationError(f"{path}: expected array")
        return [typed(v, args[0], f"{path}[{i}]") for i, v in enumerate(value)]
    if origin is dict:
        if type(value) is not dict:
            raise ValidationError(f"{path}: expected object")
        return {typed(k, args[0], path): typed(v, args[1], path + '.' + str(k)) for k, v in value.items()}
    if annotation is float and type(value) in (int, float):
        plain(float(value))
        return float(value)
    if type(value) is not annotation:
        raise ValidationError(f"{path}: expected {annotation.__name__}")
    return value


def decode(kind, payload):
    if kind not in CONTRACTS or type(payload) is not dict:
        raise ValidationError(f"Unknown contract or invalid object: {kind}")
    cls = CONTRACTS[kind]
    hints = get_type_hints(cls)
    extra = set(payload) - set(hints)
    if extra:
        raise ValidationError(f"{kind}: unknown fields {sorted(extra)}")
    values = {k: typed(v, hints[k], k) for k, v in payload.items()}
    for f in fields(cls):
        if f.default is MISSING and f.default_factory is MISSING and f.name not in values:
            raise ValidationError(f"{kind}: missing {f.name}")
    obj = cls(**values)
    validate(obj)
    return obj


def validate(obj):
    if not re.fullmatch(ID_PATTERN, obj.id) or obj.version < 1:
        raise ValidationError("Invalid record ID or version")
    for key, val in plain(obj).items():
        if (key.endswith('_at') or key in ('start', 'end', 'cutoff', 'earliest', 'latest', 'valid_start', 'valid_end')) and val is not None:
            timestamp(val)
        if key.endswith('_ref') and val is not None and not re.fullmatch(ID_PATTERN, val):
            raise ValidationError(f"Invalid reference: {key}")
        if key.endswith('_refs') and len(val) != len(set(val)):
            raise ValidationError(f"Duplicate references: {key}")
    for a, b in [('start', 'end'), ('earliest', 'latest'), ('valid_start', 'valid_end')]:
        x, y = getattr(obj, a, None), getattr(obj, b, None)
        if x and y and timestamp(x) > timestamp(y):
            raise ValidationError(f"Reversed interval: {a}/{b}")
    if isinstance(obj, ScopeSpec):
        for name in ('domains', 'populations', 'regimes', 'model_families'):
            value = getattr(obj, name)
            if not value or any(not v.strip() for v in value) or len(value) != len(set(value)) or ('*' in value and len(value) != 1):
                raise ValidationError(f"Invalid scope set: {name}")
        if not obj.precision:
            raise ValidationError("Precision regime required")
    if isinstance(obj, SourceSpec) and not re.fullmatch(r'[0-9a-f]{64}', obj.sha256):
        raise ValidationError("SHA-256 requires 64 lowercase hex digits")
    if isinstance(obj, ProtocolSpec):
        if not 0 < obj.alpha < 1 or not 1 <= obj.minimum_independent_clusters <= 10000:
            raise ValidationError("Invalid alpha or corroboration threshold")
        if not 0 <= obj.seed < 2**63 or not 1 <= obj.required_reviewers <= 20:
            raise ValidationError("Invalid seed/reviewer count")
        if obj.reproduction_atol < 0 or obj.reproduction_rtol < 0:
            raise ValidationError("Reproduction tolerances must be nonnegative")
    if isinstance(obj, ClaimSpec):
        if not obj.mandatory_dependencies and not obj.proof_routes:
            raise ValidationError("Claims require a nonempty proof route")
        if any(not r for r in obj.proof_routes):
            raise ValidationError("Vacuous proof routes are forbidden")
    if isinstance(obj, (ProtocolSpec, ClaimSpec)):
        if any(g not in [f'G{i}' for i in range(16)] for g in obj.required_gates):
            raise ValidationError("Unknown gate ID")


def schema_for(kind):
    def schema(t):
        origin, args = get_origin(t), get_args(t)
        if t is Any:
            return {}
        if origin in (Union, types.UnionType):
            return {'anyOf': [schema(x) for x in args]}
        if origin is Literal:
            return {'enum': list(args), 'type': 'string'}
        if origin is list:
            return {'type': 'array', 'items': schema(args[0])}
        if origin is dict:
            return {'type': 'object', 'additionalProperties': schema(args[1])}
        return {'type': {str:'string', int:'integer', float:'number', bool:'boolean', type(None):'null'}[t]}
    cls = CONTRACTS[kind]
    hints = get_type_hints(cls)
    properties = {k: schema(v) for k, v in hints.items()}
    properties['id']['pattern'] = ID_PATTERN
    properties['version']['minimum'] = 1
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'title': kind,
            'type': 'object', 'additionalProperties': False, 'properties': properties,
            'required': [f.name for f in fields(cls) if f.default is MISSING and f.default_factory is MISSING]}
