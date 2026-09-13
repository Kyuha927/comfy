# ONE-SHOT: Security Red-Team the WebGPT Browser Control Plane

Act as an independent hostile security reviewer. Do not implement product features, approve release, run real consequential actions, bypass browser policy, or use personal credentials. Review the candidate as an attacker controlling page content, redirects, downloads, browser prompts, tool outputs, network timing, and some worker processes.

## Inputs

Read `00_READ_FIRST_WEBGPT_BROWSER_CONTROL_PLANE.md`, the threat model, policy, schemas, MCP contract, evidence design, source, tests, and current status. Verify the source archive SHA-256 before use. Treat every undocumented assumption as untrusted.

## Attack program

Test at minimum:

- Prompt injection and confused-deputy paths where page content attempts to grant authority, change host, expand scope, approve itself, or alter evidence requirements.
- Permit forgery, nonce reuse, replay, partial-consumption races, cost/currency confusion, host canonicalization, wildcard confusion, clock skew, and key rotation failure.
- Approval replay, digest substitution, stale UI, hidden payload mutation, same-person dual approval, and approve-after-execute races.
- SSRF through redirects, DNS rebinding, IPv4/IPv6 variants, encoded hosts, alternate schemes, credentials in URLs, localhost, private, link-local, metadata, and internal names.
- Browser-profile theft, auth-state leakage, cookies/tokens in traces, screenshots, console, downloads, evidence bundles, errors, and logs.
- Selector substitution, clickjacking, modal overlays, visual deception, service-worker interference, download bombs, archive traversal, upload exfiltration, and malicious filenames.
- Job-state races, duplicate execution, rollback bypass, evidence-chain truncation/reordering, HMAC misuse, database tampering, and quarantine escape.
- Developer/CDP elevation and existing-profile access as separate high-risk modes.

## Standards and gates

Map findings to OWASP ASVS 5.0.0 where applicable, NIST SSDF 1.1 practices, and the candidate's own R0-R5 policy. Run dependency, secret, static, and dynamic checks with exact versions and retain evidence. A passing regex scan is not a comprehensive secret audit.

## Output

Create a severity-ranked report with reproducible steps, affected invariant, evidence, exploit preconditions, blast radius, smallest safe fix, regression test, and release impact. Any unresolved Critical or High issue, ambiguous authority boundary, or missing evidence must produce `SECURITY_RELEASE_BLOCKED`. Do not self-certify fixes and do not change the release verdict.
