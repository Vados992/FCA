# Status semantics

Every run has independent `execution_state`, `scientific_state` and `validity_state`. Read all three and the gate blockers. A successful process exit does not imply a supported scientific claim.

| Axis | Values and meaning |
|---|---|
| Execution | `COMPLETE`: the gated evaluation finished; `BLOCKED`: prerequisites prevent a complete evaluation; `ERROR`: unexpected execution/programming failure |
| Scientific | `SUPPORTED`: the declared operational criterion is supported conditionally in scope; `CERTIFIED_WITHIN_SCOPE`: exhaustive finite-domain certificate; `FALSIFIED`: valid operational falsifier contradicts the specified hypothesis; `NOT_SUPPORTED`: specified positive criterion is not met; `INCONCLUSIVE`: unresolved research requirement; `UNRESOLVED`: the evidence/provenance/execution basis does not permit inference |
| Validity | `VALID`, `OUTSIDE_DOMAIN`, `MODEL_INVALID`, `DATA_INSUFFICIENT`, `PROVENANCE_FAILURE`, `TEMPORAL_FAILURE`, `IDENTIFICATION_FAILURE` |
| Gate | `PASS`, `FAIL`, `INCONCLUSIVE`, `BLOCKED`, `NOT_IMPLEMENTED` |

A gate that is inapplicable to a claim records PASS **with an explicit applicability diagnostic**; e.g., causal identification is not required for a documentary observation. This does not grant a causal certificate. Gates are never silently skipped through `required_gates` configuration; all 16 core gates participate in every run.

Proof routes are disjunctions of conjunctions. Mandatory dependencies apply to every route. Failed optional alternatives do not contaminate a complete valid alternative route, but material contradictions remain relevant globally. Evidence strengths are componentwise meets (provenance, independence, time, model, reproduction and scope), not a weighted global truth probability.

The service tests declared operational semantics and structural restrictions. It cannot read arbitrary prose and establish its logical equivalence to an estimator or experimental design. Analysts and reviewers must check this correspondence. Assumptions with an evidence reference are inspectable declarations, not automatically proven facts. No adapter may promote association/access/benefit to intent or legal guilt; unsupported domains and methods are rejected.

Reviews are immutable objects with rationale and conflict-of-interest metadata. Review disposition, machine state and authenticated release are distinct. APPROVE cannot turn INCONCLUSIVE into SUPPORTED. A changed hypothesis, parameter, source or scope requires a new version and protocol. Releases require current integrity, reproducibility, required gates and independent approvers; high-impact claims require at least two reviewers.
