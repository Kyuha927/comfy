# Operations Runbook

**Candidate:** `0.3.0a1`
**Default mode:** local read/write disabled until exact permits are issued
**Production status:** blocked

## Trustworthy startup

1. Verify the source manifest and candidate commit or bundle identity.
2. Store environment secrets in a local `0600` file outside the repository. Never paste them into chat.
3. Use three distinct random values for permit signing, approval signing, and evidence HMAC.
4. Set an exact target-host allowlist. Wildcards are rejected by live settings.
5. Keep `WBCP_R4_MODE=block` unless a separately approved dual-control deployment exists.
6. Start only on `127.0.0.1`; expose a private endpoint only through the approved Secure MCP Tunnel path.
7. Verify `browser.health`, evidence integrity, tool schema, and transport version before creating a browser session.
8. Issue the smallest finite permit from the operator CLI. Permit and approval issuance are intentionally absent from MCP tools.

## Start commands

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[http,playwright]'
python -m playwright install chromium

set -a
source /secure/path/wbcp.env
set +a

wbcp serve-http --bind 127.0.0.1 --port 8765
# or, for a local process-managed MCP client:
wbcp serve-stdio
```


HTTP transport identity and least privilege are configured with `WBCP_HTTP_PRINCIPAL_ID`, `WBCP_HTTP_ALLOWED_TOOLS`, `WBCP_HTTP_REQUESTS_PER_MINUTE`, `WBCP_HTTP_MAX_CONCURRENT_REQUESTS`, `WBCP_HTTP_MAX_REQUEST_BYTES`, and `WBCP_HTTP_MAX_BATCH_ITEMS`. An empty tool allowlist means every reviewed MCP tool, so production deployments should set an explicit list.

## Engine-specific local isolation

- Use Playwright as the deterministic primary worker for known flows. `AUTO` is not permission to select Jev or CUA.
- Install Jev only in a separate WBCP-owned Python `>=3.12` environment after `scripts/verify_engine_sources.py --jev-source PATH` validates [`ENGINE_SOURCES.lock.json`](ENGINE_SOURCES.lock.json). Do not attach it to an everyday Chrome profile.
- Keep Jev authenticated pages, sensitive pages, personal profiles, unsupported features, and external-model egress default-denied. A Jev `DONE` result needs an independent WBCP verifier before it can succeed.
- Bind every CUA operation to the exact session, PID, window, target, tab, authorized URL, and isolated profile. CUA must meet the `0.28.2` minimum validated reference and remain within the typed-operation allowlist.
- Do not install this candidate, modify TCC, upgrade CUA, or attach an existing profile until the candidate's remote/fresh-clone and isolated local gates pass. Those operations require their own backup and observed rollback evidence.

## Finite authorization

Create the session permit before the model calls `browser.session.create`:

```bash
wbcp issue-permit \
  --session-id SESSION_ID \
  --actions session_create inspect navigate query job_get evidence_get session_close \
  --hosts example.com \
  --risk-ceiling 1 \
  --max-calls 20 \
  --ttl-seconds 300
```

For R3 work, preflight first, review the exact job ID and action digest, then issue one approval:

```bash
wbcp issue-approval \
  --job-id JOB_ID \
  --approval-kind HIGH_IMPACT \
  --approvers HUMAN_APPROVER_ID \
  --confirm-action-digest ACTION_DIGEST_FROM_PREFLIGHT \
  --confirm-page-revision PAGE_REVISION_FROM_PREFLIGHT \
  --ttl-seconds 120
```

R4 remains blocked by default. Dual control requires two distinct approver identities and a separately reviewed deployment policy.

## Per-action sequence

```text
proposal
-> normalize and classify
-> exact-host and SSRF preflight
-> durable job and action digest
-> finite permit validation
-> one-shot approval when required
-> atomic permit plus approval consumption
-> execute typed semantic action
-> DOM/accessibility verification
-> rendered-pixel verification
-> provider/network receipt verification
-> success OR verified rollback OR quarantine
-> append evidence and optionally sign checkpoint
```

## Evidence checkpoint

```bash
wbcp generate-checkpoint-key \
  --private-key /secure/wbcp-checkpoint.pem \
  --public-key /secure/wbcp-checkpoint.pub.pem

wbcp sign-checkpoint \
  --private-key /secure/wbcp-checkpoint.pem \
  --output /secure/checkpoints/wbcp-root.json \
  --instance-id macpro-wbcp-local

wbcp verify-checkpoint \
  --checkpoint /secure/checkpoints/wbcp-root.json \
  --public-key /secure/wbcp-checkpoint.pub.pem
```

A local signature is not an external anchor. Production requires managed key custody and copying the signed root to an independently controlled append-only destination.

## Failure rules

- Any authentication, Host, Origin, protocol, request-size, schema, URL, permit, approval, revision, or evidence failure blocks before execution.
- A browser or transport error before a known external effect is terminal failure.
- An error after a consequential provider request may have escaped is `QUARANTINED`; reconcile by provider idempotency key or receipt before any retry.
- Failed postcondition plus verified compensating action may become `ROLLED_BACK`.
- Failed postcondition without verified compensation never becomes success.
- Evidence verification failure globally stops writes.
- Disk-full or evidence fsync failure must stop before consequential commit.
- Schema drift blocks affected tools until admin and release review.

## Emergency stop

1. Reject new write authorizations.
2. Cancel safely cancellable jobs.
3. Quarantine uncertain external effects.
4. Close browser contexts and tunnel.
5. Preserve the redacted ledger and last valid root.
6. Revoke and rotate affected transport, permit, approval, and checkpoint keys.
7. Require a fresh deployment receipt before re-enable.

Do not delete evidence, silently retry consequential actions, edit SQLite to force a state, or broaden permissions to recover availability.

## Backup and restore

- Back up SQLite through a WAL-consistent snapshot.
- Back up evidence plus the last externally anchored checkpoint.
- Restore only into an isolated environment.
- Start restored deployments read-only until job revisions, permit usage, ledger sequence/root, and provider reconciliation pass.

## Upgrade

- Build an immutable candidate and rerun all local gates.
- Diff MCP schemas and target browser policy.
- Drain old workers; do not hot-patch active jobs.
- Migrate a copied state store, verify, then switch.
- Retain a tested rollback package and database backup.
- Revoke the old signing identity only after the rollback window.
