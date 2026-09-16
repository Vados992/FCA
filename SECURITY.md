# Security model

FCEA 1.0 is a **Research Local** system with one trusted filesystem owner and authenticated workspace-level API users. It is not a multi-tenant hosted service. The [architecture boundary](docs/ARCHITECTURE.md) and [operations guide](docs/OPERATIONS.md) are part of the deployment contract.

## Implemented controls

- Sources are content-addressed and verified on use. Objects/references/audit records are append-only through the application and SQLite triggers. Run inputs and code hashes are frozen.
- API tokens contain cryptographically random entropy, are stored as SHA-256 digests, and are compared with `hmac.compare_digest`. Roles separate analysts, reviewers and release owners. The CLI trusts the OS user.
- Localhost is the default; credentials are required for all private endpoints. Host/Origin checks, no CORS, CSP, no inline/third-party scripts, no-store and anti-framing headers constrain the browser boundary. The UI keeps tokens only in tab memory.
- Source acquisition accepts explicit bytes rather than fetching supplied URLs. Parsers and adapters are allowlisted. No evaluation of Python/SQL expressions, arbitrary plugins or archive-supplied code occurs.
- Upload, row, iteration, request and archive limits bound local workload. Archive verification rejects traversal, symlinks, duplicates and hash inconsistencies before replay. Reproduction imports installed trusted code only.
- Public proof export rejects restricted sources and derived inputs. Internal packets can contain authorized derived values; an omitted restricted raw source makes replay explicitly non-self-contained.
- Releases require independent review and preserve machine verdicts. HMAC authenticates the local release record; proof ZIP hashes alone establish consistency, not publisher authenticity.
- Backups and restore verify manifests, database, raw content and audit. New data/backup/restore directories use POSIX mode 0700; auth/key files use 0600. Existing directories/ACLs and encrypted media require deployment configuration.

## Trust limits

A privileged local administrator can alter code, remove SQL triggers, replace an entire coherent history, access raw data, impersonate CLI actors, or obtain HMAC keys. A chain of unanchored hashes cannot detect complete malicious replacement. Institutions need externally anchored digests/WORM storage, independently controlled signing keys, least-privilege OS identities and reviewed backups.

Source truth, undisclosed common ownership/dependence, consent, causal assumptions and reviewer independence cannot be inferred from cryptographic hashes. The service checks declared contracts and certificates; domain review is still required. Integrity and authorization tests do not constitute a penetration test, regulatory certification or independent scientific validation.

No OIDC/SSO/MFA, automatic TLS provisioning, secret rotation service, storage encryption/KMS, tenant-specific ACLs, distributed admission control or public-key PKI is bundled. Do not publish real sensitive input or expose the standard-library HTTP server as an Internet endpoint. In a multi-user environment, readers can inspect all records in their workspace: separate workspaces are needed for separate disclosure boundaries.

## Reporting

Do not place secrets or sensitive evidence in public GitHub issues. If private vulnerability reporting is enabled for the repository, use that channel; otherwise contact the repository owner privately before disclosing exploitable details. Supply a minimal synthetic reproducer, affected version, expected/actual behavior and scope. No unverified security contact address is invented here.
