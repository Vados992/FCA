# Research Local operations

## Data and credentials

Default data directory: `var/fcea`, overridable by `--data-dir` or `FCEA_DATA_DIR`. The directory contains `fcea.sqlite3`, WAL/SHM while open, `raw/`, and optionally API credential files. Newly created data/backup/restore directories request owner-only permissions on POSIX. Existing-directory permissions and Windows ACLs remain the operator's responsibility. Keep state on an encrypted disk if required by the dataset's policy.

`python -m fcea serve` creates a hashed `auth.json` configuration and a local `credentials.local.json` with the initial tokens. Both credential files have owner-only file permissions on POSIX. Distribute each token only to its intended role, then move the initial credential list to your secret manager or remove that list after securely recording the tokens. The API does not echo tokens or log sensitive request bodies. Restart after replacing the auth configuration; credentials are loaded at startup.

To provision a separate auth configuration, `python -m fcea auth init /private/path/auth.json` prints new tokens once. The target file must not already exist. The CLI intentionally trusts the OS user; `--actor` labels audit entries but is not authentication. Use role-separated API access for collaborative work. Never share the filesystem owner account as a substitute for RBAC.

## Review and local release

Use the actual run ID from your research. The following demonstrates local roles; organizational independence must exist in reality.

```sh
python -m fcea --data-dir var/study --actor reviewer-one review RUN_ID APPROVE --reason 'Reviewed source lineage, design, scope and limitations.'
python -m fcea --data-dir var/study --actor reviewer-two review RUN_ID APPROVE --reason 'Independently reproduced the frozen result.'
python -m fcea keygen var/keys/release.key
python -m fcea --data-dir var/study --actor release-owner release RUN_ID --key-file var/keys/release.key --output release.json
python -m fcea release-verify release.json --key-file var/keys/release.key
```

For API release, start the server with `--release-key-file var/keys/release.key` and use the separate release token. At least one independent approver is required; a high-impact claim requires at least two. Reviewers with conflicts, self-review or the release owner's own review do not count. A current DOWNGRADE, REJECT or RERUN_REQUIRED review blocks release. Integrity/code/gate prerequisites still apply.

The release record uses HMAC-SHA256 with a shared secret. A party holding the key can verify **and forge** such authentication, so this is not a public digital signature. Keep keys outside Git and separate from evidence backups. Public-key signatures and external key custody require a future reviewed integration. A release creates records and a proof packet locally; it does not push data to GitHub or elsewhere.

## Backup and restore

```sh
python -m fcea --data-dir var/study verify
python -m fcea --data-dir var/study backup var/backups/study-001
python -m fcea restore var/backups/study-001 var/restored-study
python -m fcea --data-dir var/restored-study verify
```

Backup and restore targets must not already exist. Backup copies the consistent database and raw store, with a file-hash manifest. Restore checks file hashes, paths, SQLite structure, raw inputs and the audit chain before reporting success. It never overwrites a live directory. The automated suite performs a restore test and rejects deliberately corrupted backups. Schedule the same restore exercise for your actual environment; no scheduler is bundled.

Authentication files and release keys are **not included** in an evidence backup. Back them up separately through a protected credential workflow; restored evidence can use newly provisioned API identities. Backup files themselves are not encrypted by the application. Store an external trusted copy of the manifest/hash if protection against a malicious filesystem owner is required.

## Docker

The image runs as UID/GID 10001. Compose publishes `127.0.0.1:8000`, drops capabilities, sets a readonly root filesystem, provides a bounded temporary directory and a persistent data volume, and limits process count/memory. The image health check queries `/healthz`; detailed integrity remains an authenticated action.

```sh
docker compose up --build -d
docker compose logs --tail 20
docker compose exec fcea python -m fcea --data-dir /data verify
python scripts/check_container.py
docker compose down
```

`check_container.py` builds a test image, creates a temporary non-root container, runs the authenticated API and replays a downloaded proof, then removes only that test container and its anonymous volume. Docker is required for this check. Compose's named research volume is unaffected. The base tag tracks Python 3.12 on Debian bookworm; for immutable deployment set `FCEA_PYTHON_IMAGE` to a reviewed digest with `docker build --build-arg FCEA_PYTHON_IMAGE=...`. Container-image scanning/signing is not supplied by this local profile.

## Network, scale and recovery

Localhost is the default. Non-loopback binding needs `--allow-remote`; TLS can be configured with `--tls-cert` and `--tls-key`. Host validation permits the configured bind host and localhost names. A custom proxy hostname needs a reviewed allowlist configuration/code change, and TLS termination/forwarded-header semantics must be reviewed. Do not expose this standard-library HTTP server directly to the Internet. Python documents its production limitations in the [http.server documentation](https://docs.python.org/3/library/http.server.html).

Resource limits: 16 MiB input/raw objects, 20,000 rows per adapter, 100–2,000 bootstrap draws with a four-million-draw-elements budget, 45-second isolated numerical reproduction timeout, two concurrent API runs, 16 concurrent HTTP requests, proof archives up to 32 MiB compressed / 100 MiB declared expanded size and 2,048 entries. The main-process numerical call is bounded by method-specific size/iteration limits, not a global cancellation deadline. For larger studies, create a reviewed adapter/runtime profile; do not simply remove limits.

Stop the service before upgrades. Back up evidence and credentials separately, preserve the old trusted checkout/interpreter needed by existing proof packets, and validate migration/reproduction in a new directory. Code hashes include Python, SQL and dashboard files; changing any of these intentionally makes old-run proof replay/export require the original version. A new code version cannot silently masquerade as the old one.

CLI exit codes: 0 means the command completed (a completed run can still be scientifically inconclusive); 2 means invalid input, missing data or another expected operational error; 3 means a blocked/error run, incomplete demo conformance or failed/blocked reproduction. Always inspect the JSON verdict. Unexpected test/validator failures return nonzero.
