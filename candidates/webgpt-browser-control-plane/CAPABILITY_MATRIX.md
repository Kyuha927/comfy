# Capability Matrix

| Capability | Implementation | Automated evidence | Real browser / transport evidence | Production status |
|---|---:|---:|---:|---|
| Exact-host HTTPS and unsafe URL rejection | yes | pass | Playwright route callback pass | candidate |
| Redirect scope escape | yes | pass | callback contract pass | target-network proof blocked |
| Private/link-local/internal target rejection | yes | pass | target DNS/rebinding not run | blocked |
| Prompt-injection authority boundary | yes | pass | real hostile site not run | candidate |
| R0-R5 classification, unknown-to-R4 | yes | pass | n/a | candidate |
| Finite session/write permits | yes | pass + race | MCP session creation pass | candidate |
| Canonical signed-token encoding | yes | tamper + unused-bit alias + 50 repeat pass | n/a | candidate |
| Atomic permit + one-shot approval | yes | pass + race | MCP R3 gate pass | candidate |
| Dual control | yes | pass | live operator UI not run | disabled by default |
| Cost and currency ceiling | yes | pass | real provider not run | blocked |
| Durable job state and CAS | yes | pass + race | process close/reopen pass | candidate |
| Idempotent terminal replay | yes | pass | provider reconciliation not run | blocked |
| Typed MCP tool catalog | yes | pass | no generic click/eval tool | candidate |
| MCP legacy initialize | yes | pass | local stdio/HTTP pass | candidate |
| MCP 2026 server/discover | yes | pass | local stdio/HTTP pass | candidate |
| MCP stdio transport | yes | child-process pass | local only | candidate |
| Authenticated Streamable HTTP | yes | bearer/Host/Origin/version tests pass | actual loopback uvicorn process pass | tunnel not run |
| Principal-level MCP tool allowlist | yes | filtered discovery + blocked call pass | local HTTP pass | production RBAC blocked |
| Request rate and capacity limits | yes | rate regression pass | local process only | distributed controls blocked |
| Request and batch bounds | yes | streaming byte cap + batch cap pass | local HTTP pass | edge proxy proof blocked |
| Strict JSON parser boundary | yes | duplicate-key rejection on HTTP/stdio | local transport pass | fuzz campaign blocked |
| Allowlisted CORS response | yes | exact-origin response test pass | local HTTP pass | production origin proof blocked |
| Secure MCP Tunnel | no deployed instance | no | no | blocked |
| ChatGPT app/desktop roundtrip | no live receipt | no | no | blocked |
| Playwright isolated context | yes | pass | Chromium offline pass | target Mac not run |
| Existing Chrome profile lane | no | no | no | blocked |
| DOM/accessibility evidence | yes | pass | Chromium offline pass | candidate |
| Pixel evidence | yes | pass | Chromium offline pass | candidate |
| Provider/network evidence | interface + assertions | mock pass | live network blocked | blocked |
| R3/R4 all-three evidence and receipt gate | yes | positive + missing-receipt negative pass | negative Chromium proof pass | candidate |
| Rollback and quarantine | yes | pass | real provider compensation not run | blocked |
| Secret redaction | yes | pass | public code/hash preservation pass | candidate |
| HMAC evidence chain | yes | pass + race + tamper | 3,136-event burn-in chain pass | candidate |
| Ed25519 root checkpoint | yes | sign/verify/tamper pass | local key only | external anchor blocked |
| Session leak closure | yes | 448-iteration burn-in, 0 active sessions | mock adapter | target browser blocked |
| Restart recovery | yes | pass | local process boundary pass | reboot/provider reconciliation blocked |
| Static source security checks | yes | 0 findings | limited scope | independent review blocked |
| CycloneDX SBOM and candidate inventory | yes | generated | candidate only | vuln/license/provenance blocked |
| GitHub Actions candidate workflow | yes | syntax review only | remote run not available | blocked |
| 24-hour soak and fault campaign | scripts partial | 30-second burn-in pass | 24-hour run not done | blocked |
| GPT-6 Pro/Astra independent gates | handoffs ready | not run | not run | blocked |

A `candidate` row is not a production approval. Only `RELEASE_GATES.md` can govern promotion.
