# Architecture and implementation boundary

Basis: **FCEA-2026-V1.0-CORE**, FCEA v1.0, 3 September 2026, system architect **Vadym Tsinderhoz**. The complete supplied document is preserved in [reference/](reference/README.md). This implementation selects the specification's **Research Local** profile: one trusted local workspace, SQLite, immutable raw files, a Python service and an authenticated browser UI.

## End-to-end path

Acquisition hashes raw bytes. Extraction produces versioned evidence whose value can be regenerated from those bytes. Typed records bind the hypothesis, scope, model, implementation, assumptions, counterfactuals and falsification tests. A freeze record fixes all input hashes and exact prerequisite run IDs. The service evaluates a fixed gate dependency DAG; downstream gates cannot run through a failed prerequisite. A run stores three independent status axes, the numerical result and limitations. Proof export includes the frozen snapshot and verified code; replay reconstructs a new database and re-executes the gate chain. Human reviews and release authentication are separate append-only records.

## Layer map

| Layer | Implementation | Supported boundary |
|---|---|---|
| L0 Protocol freeze/system boundary | `service.py`, `ProtocolSpec`, `ProtocolFreeze`, G0 | Immutable inputs, cutoff, tests, seed and parameters; amendments use new IDs. Local timestamps are not an external preregistration authority. |
| L1 Typed ontology/contracts | `core/contracts.py`, `schemas/` | 17 strict input types, timezone-aware time, finite numbers, no unknown fields; runtime adds semantic/reference checks. |
| L2 Source integrity/acquisition | `storage/objects.py`, `SourceSpec` | Content-addressed SHA-256, exclusive creation, verified reads, acquisition metadata and redistribution flag. No truth guarantee from a hash. |
| L3 Provenance/chain of custody | `graphs/provenance.py`, audit chain | Recursive source/evidence ancestry and regenerated extraction. Parent roles are explicit; declared parenthood is reviewable. |
| L4 Normalization/resolution/quality | `core/normalization.py`, G4 | JSON Pointer, CSV and text; unit registry, duplicate row checks, identity normalization without automatic entity merging. No general NLP/entity-resolution service. |
| L5 Evidence graph | `graphs/graph.py`, `EvidenceLink` | Source/evidence lineage, supports/contradicts/neutral edges and distinct cross-graph references. |
| L6 Claim graph | `ClaimSpec`, `RunContext`, G15 | Mandatory conjunctions and alternative proof routes; prerequisite verdicts pinned at freeze; cycles rejected. |
| L7 Model graph | `ModelSpec`, `ImplementationSpec`, projections | Version-linked model, assumptions, fixed adapter method, explicit equations/estimand and code digests. |
| L8 Temporal graph/cutoff | `EventSpec`, `TemporalRelation`, G7 | Event intervals, strict causal ordering, recursive knowledge cutoff, per-decision market cutoff. Evidence valid-time bounds restrict supporting scope. |
| L9 Scope algebra | `core/scope.py`, G6/G15 | Named finite sets, time, assumptions, model family and precision; conservative containment. Widening requires new justified certificates; no automatic transportability proof. |
| L10 Validity/assumptions | G5/G8, `AssumptionSpec` | Evidence-bearing assumptions, numeric domain checks, allowlisted column predicates; no arbitrary executable expressions. |
| L11 Gates | `gates/engine.py`, `gates/checks.py` | All G0–G15, deterministic DAG, distinct FAIL/BLOCKED/INCONCLUSIVE/NOT_IMPLEMENTED, fail-closed promotion. |
| L12 Counterfactuals | G9/G11, adapter reruns | Frozen parameter alternatives with evidence basis, full ensemble records, sign/conclusion stability. No post-hoc change of inference thresholds. |
| L13 Causal identification | Policy/health methods, G8 | RCT/DiD/one-instrument IV, explicit DAG/estimand, assumption certificates and diagnostics. No general do-calculus or automatic causal discovery. |
| L14 Closure | `analysis/closure.py`, G10 | Time-unrolled feedback with evidence-bearing ordered events and exact supported causal edge runs. Oscillator recurrence is separately typed, not spacetime closure. |
| L15 Uncertainty | Adapter outputs, `analysis/statistics.py` | Sampling intervals, scenario ranges and method-specific unmodeled components kept separate. No global truth score. |
| L16 Falsification | `analysis/falsification.py`, G12 | Frozen negative controls/placebos/falsifiers, critical target distinction, Holm/BH. Null nonrejection is not equivalence. |
| L17 Contradictions/alternatives | `ResolutionSpec`, G13 | Material contradiction links cannot be hidden by a successful route; evidence-bearing, reviewed resolutions. Alternatives remain visible. |
| L18 Evidence independence | `graphs/independence.py` | Conservative connected clusters by shared source ancestry, hashes or dependency keys. Undeclared dependence cannot be inferred reliably. |
| L19 Escalation firewall | G15, `make_verdict` | Strength meet, scope/route checks, no automatic intent/guilt, no universal negative from an incomplete search. Exhaustive named finite universes supported. |
| L20 Federated adapters | `adapters/` | Eight registered versioned families with constrained contracts and no gate override; in-process federation, not a deployed multi-organization network. |
| L21 Proof/reproduction | `proof/packet.py`, isolated worker | Appendix C artifacts plus raw/snapshot/code; numerical and whole-packet replay; restricted raw explicitly omitted. |
| L22 Review/governance | `review.py`, RBAC | Immutable reviews, COI metadata, role separation at API, high-impact two-reviewer minimum; machine verdict never overwritten. |
| L23 Security/privacy/operations | `security/`, `api/`, `operations.py` | Bearer roles, localhost, bounded requests, safe extraction, local HMAC, audit/hash verification, backup/restore. See production gaps below. |
| L24 Verification/release/publication | `tests/`, `scripts/`, CI, release service | Known-answer and adverse-case tests, synthetic scenarios, proof replay, release prerequisites and public-export controls. No claim of external scientific validation. |

## Storage and contracts

SQLite format 1 stores immutable JSON payloads in `objects`, typed foreign references in `object_refs`, and a hash-chained append-only `audit_events` table. SQL triggers prevent updates/deletes through the normal database interface. Named relational views expose the specification's logical tables without maintaining inconsistent duplicate payloads. WAL, FULL synchronization and serialized writes support the local multi-threaded API. Raw files use their SHA-256 as identity. Backups use SQLite's backup API, copy raw files and include a manifest.

Wire contracts use one common `id`, integer `version` and optional `supersedes`, rather than the PDF's illustrative type-specific `claim_id`/`model_id` names. Execution-managed `RunRecord`, `ProtocolFreeze`, `ReviewRecord`, `ReleaseRecord` and `ProofPacketRecord` cannot be registered through the public generic-object endpoint. A `RunRecord` owns its gate/verdict records instead of duplicating mutable rows. Canonical encoding is **FCEA canonical JSON v1** (sorted UTF-8 JSON, finite values); it is not a claim of full RFC 8785 conformance.

Each object write is transactional and idempotent. Bundle import is ordered and idempotent but **not a single all-or-nothing transaction**: if a later record is rejected, previously validated records remain and the corrected import can be retried. There is no destructive editing or deletion API.

## Deliberate profile limitations

The source document describes a broader research and production architecture. This release does not pretend to implement institutional SSO/MFA, multi-tenant row isolation, distributed execution, a remote WORM store, externally anchored audit notarization, cloud KMS, public-key release signatures, encrypted storage management, automatic source connectors, real-time brokerage, general theorem proving, unrestricted scientific solvers or external domain validation. Deployment policies, incident response staffing, review independence and source licenses remain real operational responsibilities.

The filesystem owner is trusted. That owner can replace an entire database/audit history or run CLI under another `--actor`; local append-only controls cannot protect against a malicious OS administrator. HMAC authentication requires a protected shared secret and does not provide public nonrepudiation. The standard-library HTTP server is not an Internet production server. An institution must supply those controls, review the [threat model](../SECURITY.md), pin the interpreter/container digest, and validate its selected data/methods before promoting the deployment profile.

The complete [requirements traceability matrix](TRACEABILITY.md) and [failure-mode map](FMEA.md) distinguish executable controls from external duties. Repeated appendix template IDs are retained, not misrepresented as independent scientific validations.
