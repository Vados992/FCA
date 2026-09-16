# Requirements traceability

Appendix D of the supplied PDF has 48 identifiers: the same 12 normative statements recur four times. Every source identifier is preserved below. Repetition is not counted as independent validation. Mappings refer to executable Research Local controls; REQ-SEC production obligations are only partially satisfied by this deployment profile. See [ARCHITECTURE.md](ARCHITECTURE.md).

| Source requirement | Statement category | Implementation under `fcea/` | Executable tests under `tests/` | Verification / boundary |
|---|---|---|---|---|
| REQ-SRC-001 | Immutable source identity | `storage/objects.py` | `test_contracts.py; test_gates.py` | Hash reads and deliberate source corruption |
| REQ-PROV-002 | Reversible provenance | `graphs/provenance.py` | `test_contracts.py` | Extraction replay, forged values, ancestry and backdating |
| REQ-CLAIM-003 | Explicit typed claims/dependencies | `core/contracts.py; service.py` | `test_contracts.py; test_gates.py` | Nonvacuous routes, mandatory dependencies and alternatives |
| REQ-MODEL-004 | Versioned model and implementation | `gates/checks.py; adapters/registry.py` | `test_gates.py; test_numerics.py` | Pinned method versions, domain predicates, allowed parameters |
| REQ-TIME-005 | Valid time and knowledge cutoff | `graphs/provenance.py; gates/checks.py` | `test_gates.py; test_quantifiers_closure.py` | Recursive cutoff, validity interval, market lookahead and causal event order |
| REQ-SCOPE-006 | No unjustified scope widening | `core/scope.py; gates/checks.py` | `test_contracts.py; test_gates.py; test_quantifiers_closure.py` | Scope partial order, finite coverage, forbidden universal inference |
| REQ-GATE-007 | Mandatory failures block promotion | `gates/engine.py` | `test_gates.py; test_proof_review.py` | DAG cycle detection, blocked descendants and release rejection |
| REQ-CF-008 | Counterfactual and sensitivity route | `gates/checks.py` | `test_gates.py; test_numerics.py` | All frozen scenarios, sign changes, threshold tampering and supply disruption |
| REQ-CAUSAL-009 | Explicit estimand/identification | `adapters/policy.py; gates/checks.py` | `test_gates.py; test_quantifiers_closure.py` | DAG, assumptions, IV exclusion, DiD pretrend and exact causal edge binding |
| REQ-FALS-010 | Frozen falsifiers and negative controls | `analysis/falsification.py` | `test_gates.py; test_numerics.py` | Negative control invalidation, multiplicity and model/hypothesis distinction |
| REQ-REPRO-011 | Run manifest and reproduction route | `service.py; proof/packet.py` | `test_proof_review.py; test_quantifiers_closure.py` | Fresh-interpreter rerun, whole packet/closure replay and corruption rejection |
| REQ-SEC-012 | Least privilege and immutable audit | `api/server.py; security/; operations.py` | `test_api.py; test_proof_review.py` | Local RBAC, immutable audit, private exports, HMAC, backup restore; institutional controls external |
| REQ-SRC-013 | Immutable source identity | `storage/objects.py` | `test_contracts.py; test_gates.py` | Hash reads and deliberate source corruption |
| REQ-PROV-014 | Reversible provenance | `graphs/provenance.py` | `test_contracts.py` | Extraction replay, forged values, ancestry and backdating |
| REQ-CLAIM-015 | Explicit typed claims/dependencies | `core/contracts.py; service.py` | `test_contracts.py; test_gates.py` | Nonvacuous routes, mandatory dependencies and alternatives |
| REQ-MODEL-016 | Versioned model and implementation | `gates/checks.py; adapters/registry.py` | `test_gates.py; test_numerics.py` | Pinned method versions, domain predicates, allowed parameters |
| REQ-TIME-017 | Valid time and knowledge cutoff | `graphs/provenance.py; gates/checks.py` | `test_gates.py; test_quantifiers_closure.py` | Recursive cutoff, validity interval, market lookahead and causal event order |
| REQ-SCOPE-018 | No unjustified scope widening | `core/scope.py; gates/checks.py` | `test_contracts.py; test_gates.py; test_quantifiers_closure.py` | Scope partial order, finite coverage, forbidden universal inference |
| REQ-GATE-019 | Mandatory failures block promotion | `gates/engine.py` | `test_gates.py; test_proof_review.py` | DAG cycle detection, blocked descendants and release rejection |
| REQ-CF-020 | Counterfactual and sensitivity route | `gates/checks.py` | `test_gates.py; test_numerics.py` | All frozen scenarios, sign changes, threshold tampering and supply disruption |
| REQ-CAUSAL-021 | Explicit estimand/identification | `adapters/policy.py; gates/checks.py` | `test_gates.py; test_quantifiers_closure.py` | DAG, assumptions, IV exclusion, DiD pretrend and exact causal edge binding |
| REQ-FALS-022 | Frozen falsifiers and negative controls | `analysis/falsification.py` | `test_gates.py; test_numerics.py` | Negative control invalidation, multiplicity and model/hypothesis distinction |
| REQ-REPRO-023 | Run manifest and reproduction route | `service.py; proof/packet.py` | `test_proof_review.py; test_quantifiers_closure.py` | Fresh-interpreter rerun, whole packet/closure replay and corruption rejection |
| REQ-SEC-024 | Least privilege and immutable audit | `api/server.py; security/; operations.py` | `test_api.py; test_proof_review.py` | Local RBAC, immutable audit, private exports, HMAC, backup restore; institutional controls external |
| REQ-SRC-025 | Immutable source identity | `storage/objects.py` | `test_contracts.py; test_gates.py` | Hash reads and deliberate source corruption |
| REQ-PROV-026 | Reversible provenance | `graphs/provenance.py` | `test_contracts.py` | Extraction replay, forged values, ancestry and backdating |
| REQ-CLAIM-027 | Explicit typed claims/dependencies | `core/contracts.py; service.py` | `test_contracts.py; test_gates.py` | Nonvacuous routes, mandatory dependencies and alternatives |
| REQ-MODEL-028 | Versioned model and implementation | `gates/checks.py; adapters/registry.py` | `test_gates.py; test_numerics.py` | Pinned method versions, domain predicates, allowed parameters |
| REQ-TIME-029 | Valid time and knowledge cutoff | `graphs/provenance.py; gates/checks.py` | `test_gates.py; test_quantifiers_closure.py` | Recursive cutoff, validity interval, market lookahead and causal event order |
| REQ-SCOPE-030 | No unjustified scope widening | `core/scope.py; gates/checks.py` | `test_contracts.py; test_gates.py; test_quantifiers_closure.py` | Scope partial order, finite coverage, forbidden universal inference |
| REQ-GATE-031 | Mandatory failures block promotion | `gates/engine.py` | `test_gates.py; test_proof_review.py` | DAG cycle detection, blocked descendants and release rejection |
| REQ-CF-032 | Counterfactual and sensitivity route | `gates/checks.py` | `test_gates.py; test_numerics.py` | All frozen scenarios, sign changes, threshold tampering and supply disruption |
| REQ-CAUSAL-033 | Explicit estimand/identification | `adapters/policy.py; gates/checks.py` | `test_gates.py; test_quantifiers_closure.py` | DAG, assumptions, IV exclusion, DiD pretrend and exact causal edge binding |
| REQ-FALS-034 | Frozen falsifiers and negative controls | `analysis/falsification.py` | `test_gates.py; test_numerics.py` | Negative control invalidation, multiplicity and model/hypothesis distinction |
| REQ-REPRO-035 | Run manifest and reproduction route | `service.py; proof/packet.py` | `test_proof_review.py; test_quantifiers_closure.py` | Fresh-interpreter rerun, whole packet/closure replay and corruption rejection |
| REQ-SEC-036 | Least privilege and immutable audit | `api/server.py; security/; operations.py` | `test_api.py; test_proof_review.py` | Local RBAC, immutable audit, private exports, HMAC, backup restore; institutional controls external |
| REQ-SRC-037 | Immutable source identity | `storage/objects.py` | `test_contracts.py; test_gates.py` | Hash reads and deliberate source corruption |
| REQ-PROV-038 | Reversible provenance | `graphs/provenance.py` | `test_contracts.py` | Extraction replay, forged values, ancestry and backdating |
| REQ-CLAIM-039 | Explicit typed claims/dependencies | `core/contracts.py; service.py` | `test_contracts.py; test_gates.py` | Nonvacuous routes, mandatory dependencies and alternatives |
| REQ-MODEL-040 | Versioned model and implementation | `gates/checks.py; adapters/registry.py` | `test_gates.py; test_numerics.py` | Pinned method versions, domain predicates, allowed parameters |
| REQ-TIME-041 | Valid time and knowledge cutoff | `graphs/provenance.py; gates/checks.py` | `test_gates.py; test_quantifiers_closure.py` | Recursive cutoff, validity interval, market lookahead and causal event order |
| REQ-SCOPE-042 | No unjustified scope widening | `core/scope.py; gates/checks.py` | `test_contracts.py; test_gates.py; test_quantifiers_closure.py` | Scope partial order, finite coverage, forbidden universal inference |
| REQ-GATE-043 | Mandatory failures block promotion | `gates/engine.py` | `test_gates.py; test_proof_review.py` | DAG cycle detection, blocked descendants and release rejection |
| REQ-CF-044 | Counterfactual and sensitivity route | `gates/checks.py` | `test_gates.py; test_numerics.py` | All frozen scenarios, sign changes, threshold tampering and supply disruption |
| REQ-CAUSAL-045 | Explicit estimand/identification | `adapters/policy.py; gates/checks.py` | `test_gates.py; test_quantifiers_closure.py` | DAG, assumptions, IV exclusion, DiD pretrend and exact causal edge binding |
| REQ-FALS-046 | Frozen falsifiers and negative controls | `analysis/falsification.py` | `test_gates.py; test_numerics.py` | Negative control invalidation, multiplicity and model/hypothesis distinction |
| REQ-REPRO-047 | Run manifest and reproduction route | `service.py; proof/packet.py` | `test_proof_review.py; test_quantifiers_closure.py` | Fresh-interpreter rerun, whole packet/closure replay and corruption rejection |
| REQ-SEC-048 | Least privilege and immutable audit | `api/server.py; security/; operations.py` | `test_api.py; test_proof_review.py` | Local RBAC, immutable audit, private exports, HMAC, backup restore; institutional controls external |
