# FCA / FCEA

**Federated Causal Evidence & Falsification Architecture · v1.0.0 · Research Local**

System architect: **Vadym Tsinderhoz**

[![FCEA validation](https://github.com/Vados992/FCA/actions/workflows/ci.yml/badge.svg)](https://github.com/Vados992/FCA/actions/workflows/ci.yml)

[Русская инструкция](docs/README_RU.md) · [Architecture](docs/ARCHITECTURE.md) · [Methods](docs/METHODS.md) · [API](docs/API.md) · [Validation](docs/VALIDATION.md)

A runnable implementation of the supplied [FCEA v1.0 architecture](docs/reference/FCEA_v1.0_Architecture_Vadym_Tsinderhoz.pdf). It stores immutable evidence, freezes research protocols, executes numerical domain methods through 16 mandatory gates, and exports reproducible proof packets. The repository name is FCA; the Python package and architecture name are FCEA.

This release implements the **Research Local** deployment profile. It includes working code for every architectural layer L0–L24 within that profile, with an explicit [implementation map and boundaries](docs/ARCHITECTURE.md). Successful synthetic tests establish software behavior; they do not establish the truth of external sources, causal assumptions, or real-world scientific conclusions. Institutional/cloud deployment and independent domain validation remain separate work.

## Run in three commands

Install **Python 3.11 or newer** and Git. No API key, paid service, Node.js, database server, or runtime `pip install` is required.

```sh
git clone https://github.com/Vados992/FCA.git
cd FCA
python -m fcea serve
```

Open **http://127.0.0.1:8000**. On first launch, read the `analyst` token in `var/fcea/credentials.local.json` and paste it into the login field. Select an example, click **Load example**, then **Freeze & run**. Inspect the estimate, G0–G15, uncertainty, and proof packet. Tokens remain in the tab's memory; keep the credentials file private. Use `python3` if that is your Python command.

For a terminal-only run:

```sh
python -m fcea --data-dir var/demo demo --all
python -m fcea --data-dir var/demo verify
python -m unittest discover -s tests -v
```

Docker is also supplied:

```sh
docker compose up --build -d
docker compose exec fcea cat /data/credentials.local.json
```

The published port binds to localhost. The container stores state in the `fcea-data` volume; `docker compose down` preserves it. See [operations](docs/OPERATIONS.md) for backup, restore, tokens, and container verification.

## What is included

| Component | Working implementation |
|---|---|
| Evidence | SHA-256 raw store, versioned typed records, reproducible extraction, provenance and source-dependency clusters |
| Research core | Protocol freeze, scope algebra, valid/knowledge time, proof routes, mandatory gate DAG, separate scientific/execution/validity states |
| Numerical methods | RCT, two-period DiD, single-instrument IV, fixed-prediction checks, finite predicates, market backtests, maximum flow, single-fingerprint OLS, oscillator recurrence, documentary paths |
| Falsification | Frozen counterfactual ensemble, negative controls/placebos, Holm/BH adjustment, contradiction resolutions, causal edge and feedback certificates |
| Reproduction | Fresh-interpreter numerical checks, proof ZIP with frozen inputs/code hashes, full gate replay from the archive |
| Application | Authenticated HTTP API, browser dashboard, CLI, SQLite migrations/views, review and release workflows |
| Delivery | Ten synthetic scenarios, JSON schemas and OpenAPI, Docker/Compose, CI, executable tests, original architecture and traceability matrix |

Eight adapter families cover **science, policy, public health, market, climate, supply, physics, and integrity**. Each adapter advertises its actual supported methods and limitations. There are no fake cloud connectors, live trading connections, placeholder model results, or hidden remote inference dependencies.

## Use your own evidence

```sh
python -m fcea example policy-rct --output my-study.json
# Edit IDs, source data, scopes, model assumptions, tests and frozen parameters.
python -m fcea --data-dir var/study import my-study.json
python -m fcea --data-dir var/study freeze policy_rct.protocol
python -m fcea --data-dir var/study run policy_rct.protocol --output run.json
```

Use a new identifier/version for amended objects. `known_at` is the date information was actually available; it is not the download timestamp. Replace synthetic assumption certificates with defensible evidence and domain review. The prose claim must accurately describe the frozen operational test: the software does not automatically prove that arbitrary natural-language text follows from data.

To export and independently rerun the workflow, substitute the actual `run_id` from the result:

```sh
python -m fcea --data-dir var/study proof export RUN_ID packet.zip
python -m fcea proof verify packet.zip
python -m fcea proof reproduce packet.zip
```

Reproduction uses the same trusted code version. Archive-supplied Python is never executed. Restricted raw sources are omitted; such packets are explicitly blocked for self-contained reproduction. Public export blocks restricted source and derived inputs.

## Repository guide

```text
fcea/          Core, service, storage, gates, adapters, API, dashboard, proof tools
tests/         Numerical, negative-control, lifecycle, privacy and replay tests
examples/      Complete importable synthetic JSON bundles
schemas/       Generated typed JSON schemas
scripts/       Artifact generation, validation, package and container checks
docs/          Methods, API, deployment, traceability and original source PDF
```

[`docs/VALIDATION.md`](docs/VALIDATION.md) explains what was actually checked. [`docs/SCIENTIFIC_STATUS.md`](docs/SCIENTIFIC_STATUS.md) defines conclusions and prohibited inference. [`SECURITY.md`](SECURITY.md) describes the local trust boundary. Releases are locally authenticated with **HMAC-SHA256**, not publicly verifiable digital signatures. The HTTP server is intended for local research, not direct exposure as an Internet service.

## Development and licensing

```sh
python scripts/generate_artifacts.py --check
python scripts/validate.py --output validation-output
```

Optional packaging: `python -m pip install .` installs the `fcea` command; only the build backend needs packages. Runtime dependencies are empty and recorded in [`runtime-lock.json`](runtime-lock.json).

The existing [Apache License 2.0](LICENSE) is preserved. See [NOTICE](NOTICE), [contributing](CONTRIBUTING.md), and [source provenance](docs/reference/README.md). All bundled example data are synthetic.
