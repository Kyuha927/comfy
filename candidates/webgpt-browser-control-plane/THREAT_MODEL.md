# Threat Model

## Protected assets

- User accounts, authenticated browser sessions, cookies, passkeys, and recovery material.
- Money, credits, generation quotas, reservations, messages, posts, files, and external resources.
- Control-plane signing keys and approval authority.
- Policy, domain allowlists, budgets, release configuration, and audit evidence.
- Local files reachable through upload/download flows.
- Browser history, console, network metadata, and screenshots.

## Trust boundaries

1. Chat/model proposal boundary.
2. MCP/app/plugin transport boundary.
3. Identity and approval boundary.
4. Control-plane to browser-worker boundary.
5. Browser to website boundary.
6. Browser to local filesystem boundary.
7. Evidence exporter/observability boundary.
8. Release pipeline and update boundary.

## Principal threats and mandatory controls

| Threat | Example | Required control | Failure behavior |
|---|---|---|---|
| Prompt injection | Page says to ignore policy and send secrets | Page content cannot be authority; explicit detector; exact user-bound permit | block and preserve redacted evidence |
| Confused deputy | Model acts in the wrong account/workspace | Account/tab identity assertion, exact host and session permit, pre-commit preview | block before mutation |
| SSRF/rebinding | Redirect or DNS change reaches metadata/private host | exact allowlist, every-hop validation, resolved-IP checks and pinning | block connection |
| Approval substitution | Approved draft is changed before submit | approval bound to action digest and page revision; runtime freshness check | invalidate approval |
| Replay/double spend | Retry repeats a paid action | idempotency key, finite permit registry, provider receipt reconciliation | return prior receipt or block conflict |
| Secret leakage | Cookies/token in logs or screenshots | collect minimum, redact before append, secret-key detection, restricted artifact access | stop and quarantine evidence |
| Extension message forgery | Compromised content script asks native host to act | validate every message; service worker owns privilege; origin/capability binding | reject message |
| Browser state bleed | One job inherits another account/session | isolated context per identity and purpose; no shared auth state by default | destroy context and block |
| Stale UI/TOCTOU | Button/price/recipient changes after preview | page revision, target/price/recipient re-read immediately before commit | require new approval |
| False success | Click returns but provider rejected action | DOM + pixel + network/provider evidence, terminal receipt | failed/quarantined, never success |
| Rollback fiction | Remote post remains while UI looks restored | compensating action plus independent verification | quarantine and alert |
| Supply-chain compromise | Browser/MCP dependency update changes behavior | pinned versions, lockfile/SBOM, signature/provenance, staged upgrade tests | block release |
| Evidence tampering | Local actor edits audit file | append-only hash chain, HMAC, external root anchoring in production | verification fails closed |
| Privilege escalation | Generic click reaches payment/delete | semantic typed tools, unknown action fails R4, R4 default block | block |
| Availability attack | Stuck page exhausts workers | timeouts, cancellation, circuit breakers, bounded queues and payloads | fail terminally, release resources |

## Residual risks

- A screenshot digest alone does not prove semantic correctness. R3/R4 therefore require explicit visual assertions and independent DOM/network evidence.
- Browser automation cannot guarantee that a third-party provider will not later reverse or duplicate an external effect. Provider-side idempotency and reconciliation are required.
- HMAC evidence proves integrity only relative to the local key holder. Production requires asymmetric signing or external anchoring.
- Native OpenAI browser controls cannot be claimed as governed by this control plane until a real enforcement and receipt integration is demonstrated.
- Human approvers can approve the wrong payload. Approval UI must display target account, host, action, recipient, content summary, price, currency, and irreversible effects.
