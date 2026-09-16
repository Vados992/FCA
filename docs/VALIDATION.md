# Verification record

Validation distinguishes software conformance from external scientific validation. All bundled data are synthetic. Source hashes, passing gates and repeated calculations do not independently verify an experimental assumption or a real-world conclusion.

## Local acceptance — 16 September 2026

| Check | Observed result |
|---|---|
| Complete Python test suite | **107 tests passed**, zero failures/errors/skips |
| Ten built-in scenarios across eight families | **10/10 SUPPORTED**, VALID and COMPLETE in the synthetic test scope |
| Mandatory gate coverage | **16/16 PASS in each scenario** |
| Public proof integrity | **10/10 VERIFIED** |
| Rebuild and rerun from each proof packet | **10/10 REPRODUCED**, including gates, states, numerical output, counterfactuals and falsification |
| Clean virtual environment without pip | All ten examples run from checkout using only the standard library |
| Built wheel in a separate fresh environment | Installs offline with `--no-index --no-deps`; all ten examples and storage integrity pass; SQL/dashboard resources present |
| Generated schemas/examples/API/catalogues | 30 artifacts checked for exact consistency |
| Actual HTTP API lifecycle and role controls | Included in executable tests using a live local server |
| Interactive Chromium workflow | **PASS on GitHub Actions**: login, run, proof download/replay, graphs/adapters, mobile overflow, reviewer and role checks. Local Chromium download was unavailable. |
| Container build and lifecycle | **PASS on GitHub Actions**: non-root readonly container, authenticated API, 16 gates and proof replay. Docker was unavailable locally. |
| External scientific validation, penetration/load testing | Not performed; not implied by this release |

Machine-readable [local report](validation/local/report.json), [individual test log](validation/local/tests.log), [package check](validation/package-check.log), and [clean-environment check](validation/clean-environment.json) preserve the observations. `software.code_digest` and per-file digests identify the exact executed application. The report's `git_commit` is the checkout HEAD at local test time, before initial publication, so it alone does not identify previously uncommitted implementation files; the complete code digests do. Runtime directories and keys are not committed.

## Confirmed GitHub acceptance

[Workflow run 35111310416](https://github.com/Vados992/FCA/actions/runs/35111310416), source commit `e9a8922ed605380e9a2ad240a58464bfcdb37c14`, completed successfully on 16 September 2026. **All five jobs passed**: Python 3.11, 3.12 and 3.13 (full tests, ten proof replays, isolated package install), Docker lifecycle, and Chromium browser acceptance. [Recorded job results](validation/ci-acceptance.json) link directly to each job. The application code digest is `486d243a37fbb2e7800d7d13411841a0666ec2935beb11157885c25fdc0ca442`. Subsequent documentation-only changes do not alter that code digest.

## Reproduce verification

```sh
python scripts/generate_artifacts.py --check
python -m unittest discover -s tests -v
python scripts/validate.py --output validation-output
```

Optional installed-package verification (build dependencies only):

```sh
python -m pip install -r requirements-build.txt
python scripts/check_package.py
```

Optional browser verification requires Node.js, Playwright 1.62.1 and its Chromium installation. It starts/stops its own temporary local server, signs in, imports/freezes/runs a scenario, downloads and replays its proof, checks graphs/adapters, checks a 390-pixel mobile viewport, records a reviewer disposition and checks role controls. It saves screenshots and a report under `validation-output/browser`.

```sh
npm install --no-save --no-package-lock playwright@1.62.1
npx playwright install chromium
node scripts/check_browser.cjs
```

Use `python scripts/check_container.py` where Docker is installed. Neither optional tool is a runtime requirement for the application.

[GitHub Actions](https://github.com/Vados992/FCA/actions) runs Python 3.11/3.12/3.13 conformance and package checks plus separate container/browser acceptance jobs. Consult the actual commit's job result before treating these checks as passed; merely including a workflow is not evidence that it ran. Action source revisions are pinned. Full CI logs and synthetic validation reports are retained as artifacts.

## Adverse cases and traceability

The tests deliberately reject malformed contracts, fabricated extraction, hash corruption, source echo, post-cutoff data, invalid market timing, widened scope, missing/cyclic causal graphs, IV exclusion violations, failed DiD diagnostics, counterfactual threshold manipulation, contradictory evidence, negative controls, missing proof prerequisites, incomplete finite universes, swapped/reversed causal closure edges, archive traversal/tampering, role forgery, premature releases, restricted public exports and corrupt backups.

See [TEST_CATALOGUE.md](TEST_CATALOGUE.md), [TRACEABILITY.md](TRACEABILITY.md), and [FMEA.md](FMEA.md). Requirements are mapped to implemented controls without treating repeated PDF appendix templates as additional independent experiments. Tests are not asserted to establish exhaustive formal verification of the entire architecture.
