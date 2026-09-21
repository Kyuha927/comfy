# Official Route Reconciliation

**Research checkpoint:** 2026-09-14
**Result:** `OFFICIAL_ROUTE_RECONCILED_FOR_DESIGN`
**Live capability proof:** `NOT YET RUN`

The candidate was designed after checking first-party OpenAI, Playwright, Chrome, OWASP, NIST, and OpenTelemetry material. This document separates official recommended routes from candidate additions.

## 1. ChatGPT browser route

### Officially documented route

- ChatGPT desktop provides a built-in browser in Work or Codex. It keeps its own browser state.
- The Codex Chrome extension is the preferred official route when a task needs the user's existing Chrome profile, signed-in session, open tabs, or installed extensions.
- Credentials should be entered in the browser, not in chat. Website content must be treated as untrusted.
- Developer mode can grant controlled full CDP access for deeper debugging. OpenAI documents that this can expose sensitive browser internals, requires explicit approval, and can be disabled by workspace policy.

Sources:

- https://help.openai.com/en/articles/20001277-using-the-built-in-browser-in-the-chatgpt-desktop-app
- https://help.openai.com/en/articles/11369540

### Candidate decision

- **Adopt, do not replace**, the built-in browser/Chrome route when it satisfies the task.
- The candidate control plane is justified only where durable jobs, exact finite permits, independent evidence, rollback/quarantine, or cross-worker governance are required.
- Native browser actions cannot be claimed as governed by this candidate until an actual enforcement/receipt integration is demonstrated.

## 2. ChatGPT web custom MCP route

### Officially documented route

- ChatGPT custom apps are MCP-based.
- Full custom MCP write/modify support is documented for Business and Enterprise/Edu web workspaces.
- Pro can build Apps SDK apps, but custom MCP access is documented as read/fetch only.
- ChatGPT connects to remote MCP endpoints. A local/private MCP server is not connected directly; the official Secure MCP Tunnel is the documented route.
- Important writes may require confirmation, and especially risky actions may be blocked.
- Workspace administrators review and publish custom apps; tool snapshots and later schema changes require review/update.

Sources:

- https://help.openai.com/ko-kr/articles/12584461-developer-mode-apps-and-full-mcp-connectors-in-chatgpt-beta
- https://help.openai.com/en/articles/12515353-build-with-the-apps-sdk
- https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
- https://developers.openai.com/plugins

### Candidate decision

- A write-capable generic ChatGPT web route on a Pro-only account must stop with `BLOCKED_PLAN_OR_CHATGPT_TIER_NOT_WRITE_CAPABLE`.
- Do not bypass this by disguising writes as reads or by exposing an unauthenticated local endpoint.
- The immediate write-capable route is the supported Work/Codex browser surface, or an eligible Business/Enterprise/Edu custom app after admin review.

## 3. Browser automation engine

### Officially documented route

- Playwright browser contexts provide isolated, incognito-like profiles.
- Authentication state files may contain sensitive cookies and headers and must not be committed.
- User-facing locators and auto-waiting assertions are the preferred resilient interaction method.
- Playwright tracing records DOM snapshots, screenshots, action logs, console, and network evidence.
- Playwright documents that `connect_over_cdp` is Chromium-only and lower fidelity than the Playwright protocol.
- Playwright publishes an MCP server intended for agent browser control through structured accessibility snapshots.

Sources:

- https://playwright.dev/docs/browser-contexts
- https://playwright.dev/docs/auth
- https://playwright.dev/docs/locators
- https://playwright.dev/docs/trace-viewer
- https://playwright.dev/docs/api/class-browsertype
- https://github.com/microsoft/playwright

### Candidate decision

- Primary worker: current official Playwright MCP or Playwright-owned isolated context, after version pinning and target-Mac acceptance.
- Python adapter in this repository: reference/fallback candidate, not production primary until live parity tests pass.
- CDP attach: compatibility lane only, with an explicit approval and reduced-assurance label.
- Daily-driver Chrome control is never silently selected merely because a logged-in session exists.

## 4. Chrome extension/native host route

### Officially documented route

- Chrome extensions should request the narrowest permissions and use optional host permissions when possible.
- Content-script messages are untrusted and must be validated before privileged work.
- Native messaging has explicit framing/size rules and an allowlist of permitted extension origins.

Sources:

- https://developer.chrome.com/docs/extensions/develop/concepts/declare-permissions
- https://developer.chrome.com/docs/extensions/develop/concepts/messaging
- https://developer.chrome.com/docs/apps/nativeMessaging

### Candidate decision

An extension/native-host lane is deferred until the official Chrome route cannot satisfy a required workflow. If implemented, service-worker/native-host code owns privileges; content scripts can only submit validated data. Host permissions are per-site and time-bounded.

## 5. Security and observability baselines

- Verification baseline: OWASP ASVS 5.0.0, with requirement IDs mapped to evidence.
- Secure development baseline: NIST SSDF 1.1 final. A later draft may be gap-reviewed but must not be labeled as achieved final compliance.
- Telemetry model: OpenTelemetry traces, metrics, and logs, with secrets removed before export.

Sources:

- https://owasp.org/www-project-application-security-verification-standard/
- https://csrc.nist.gov/projects/ssdf
- https://opentelemetry.io/docs/concepts/signals/

## 6. Resulting product route

```text
Preferred now:
ChatGPT desktop Work/Codex -> official built-in browser or Codex Chrome route

Strict custom governance:
Eligible ChatGPT custom app -> Secure MCP Tunnel -> policy/evidence control plane
  -> Playwright MCP / isolated browser worker

Pro generic web chat:
read/fetch candidate only; all mutations hard-blocked until the platform capability changes
```

Official sources must be re-checked at each release because availability, plan support, permissions, and APIs can change.
