# Adding a domain adapter

Read `fcea/adapters/base.py`, `registry.py` and the method-specific examples first. An adapter is a versioned `Adapter` value with an ID/domain, allowed methods, allowed claim types, frozen parameter allowlist, declared validity and identification assumptions, callable analysis function and honest limitations.

`analyze(data, method, parameters, seed)` receives a table with 1–20,000 rows and returns an estimate, operational `scientific_state`, diagnostics and separate `uncertainty_components`; use an interval only when its sampling model is justified. Raise `ValidationError` for invalid inputs or out-of-domain methods. Do not return synthetic fallback numbers on failure. Control numerical complexity and iteration counts.

Implement a known-answer test, a falsifier/negative-control test, scope/time rejection cases, counterfactual behavior and proof replay. Add a fully synthetic import bundle and explain assumptions and failure modes in `METHODS.md`. Increment the adapter version and pin it in `ImplementationSpec`; incompatible semantics require a new implementation record and new frozen protocols.

Register the adapter statically in `registry.py`. There is no arbitrary executable plugin loader, expression evaluator, URL fetcher or adapter override of gates, provenance, review or release. The isolated reproduction worker imports the installed trusted package. Source data and archives cannot select Python to execute.

For new causal methods, extend the reviewed G8 identification rules with an explicit estimand/DAG and evidence-bearing assumptions. For new closure types, add a typed certificate and semantic validator; a graph cycle alone is not enough. Changes to global contract/gate semantics require core-version review, updated schemas and conformance tests.
