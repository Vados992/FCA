# Failure modes and residual obligations

Map of the supplied Appendix E's twenty failure modes to the Research Local implementation. This is an engineering control map, not a quantitative risk certification.

| Source | Failure mode | Implemented control | Residual obligation |
|---|---|---|---|
| F-01 | False identity merge | No automatic entity merge; normalized keys retain explicit original source | Domain identity resolution and sampling review |
| F-02 | Source echo | Shared ancestry/hash/dependency-key clusters; corroboration threshold | Disclose dependence not observable in records |
| F-03 | Cutoff leakage | Recursive knowledge cutoff, evidence valid time, market decision cutoff | Honest time-of-availability source metadata |
| F-04 | Out-of-domain model | Model scope, assumptions, numerical predicates and method allowlist | Validate regime certificates empirically |
| F-05 | Correlation promoted to causation | Explicit method, DAG, estimand and G8 | Defend untestable assumptions and omitted variables |
| F-06 | Benefit/access promoted to intent | Intent/guilt claim types prohibited by adapters/firewall | Appropriate legal/domain review outside system |
| F-07 | Post-hoc counterfactual | Frozen hashes; no runtime parameter override; threshold changes rejected | External preregistration timestamp if needed |
| F-08 | Uncontrolled multiplicity | Frozen test family; Holm/BH; no multi-test `none` | Justify family and correction dependence assumptions |
| F-09 | Contradictory evidence omitted | Material links global across routes; new links invalidate frozen root run | Discover and register adverse evidence honestly |
| F-10 | Hidden manual override | Separate immutable reviews; machine verdict unchanged | Protect OS owner and review process |
| F-11 | Schema drift | Strict shape/version/method validation; generated schemas checked in CI | Plan future migrations rather than editing historical payloads |
| F-12 | Irreproducible environment | Input/code/interpreter manifests, isolated rerun, whole proof replay | Preserve exact interpreter/OS/image and restricted sources |
| F-13 | One misleading truth score | Distinct state axes/uncertainty components; componentwise strength meet | Interpret metrics in their declared domain |
| F-14 | Graph cycle treated as feedback | Ordered events and exact causal edge certificates; adverse closure tests | Validate each edge's scientific assumptions |
| F-15 | Unsupported generalization | Scope partial order; bounded finite-universe certificates | New evidence/transportability justification for widening |
| F-16 | Source poisoning | Raw hashes, replayable extraction, controls, contradictions and source clusters | Adversarial source validation; hashing does not establish truth |
| F-17 | Parser semantic change | Versioned allowlisted transforms, extraction equality and regression tests | Review new parsers with representative source corpus |
| F-18 | Unusable backups | Automated restore and tamper tests, manifest verification | Scheduled real-environment restore drills and key recovery |
| F-19 | Sensitive publication | Restricted-source/derived-input public export block, role checks | Classify sources correctly; review separately redacted datasets |
| F-20 | Reviewer bias/conflict | COI metadata, distinct identities, high-impact two-reviewer minimum | Genuine independence and organizational governance |
