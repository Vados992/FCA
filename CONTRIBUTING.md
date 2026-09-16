# Contributing

Run `python -m unittest discover -s tests -v` and `python scripts/validate.py --output validation-output` before proposing changes. Regenerate schemas and examples with `python scripts/generate_artifacts.py` after contract or fixture changes.

Changes to inference semantics require a method version, a known-answer test, an adversarial test, a methods explanation, and an explicit scope. New adapters must use the fixed core gate interface; see [the adapter guide](docs/ADAPTERS.md). Do not add gates that silently turn missing evidence into PASS or average away mandatory failures.

Never commit source credentials, local databases, private evidence, release keys, or tokens. Bundled examples must be redistributable and explicitly synthetic. Preserve architecture attribution and the Apache 2.0 license. Software review is separate from independent scientific review of a method or dataset.

Amend immutable records with a new ID, increasing version, and `supersedes`. Schema migration changes need a new migration; do not rewrite an already-deployed migration. This is the first database format, version 1.
