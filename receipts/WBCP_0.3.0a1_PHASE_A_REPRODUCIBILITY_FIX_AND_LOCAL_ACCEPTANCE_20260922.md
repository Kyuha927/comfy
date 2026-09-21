# WBCP 0.3.0a1 candidate receipt - 2026-09-22

## Status and handoff

- Receipt status: PASS_CANDIDATE_ONLY
- Candidate version: 0.3.0a1
- Canonical local-lane handoff: https://github.com/Kyuha927/comfy/pull/4
- Draft PR base/head: work-handoffs-v4-20260912 / candidate/webgpt-browser-control-plane-jev-cua-0.3.0a1-20260921
- Production: BLOCKED_BY_RELEASE_GATES; no merge or production promotion.

## Exact source binding

- Source-fix commit: 5d95f3810a94aab38d6b983733e8516c18cad314
- Candidate source subtree: fedf884713d30daae3ac3bf119d6d1b96aa12d87
- MANIFEST and PACKAGE_MANIFEST SHA-256: 2e078eaf106ab79ba7feed68eb4754260db1930b76b7b5818c71f21304445745
- Files verified per manifest: 87; packaged files: 90.
- Source tar SHA-256: 314b8d5fc88f156c03b8622ec2739ff936393a636a868c2bc3235d086c675a00 (128339 bytes)
- Source ZIP SHA-256: 73394a7f9633f63f59dd5db9261e84e447d34b2e9858698bf9103ce680ac70a2 (179332 bytes)
- Independent rebuild: tar and ZIP byte-identical PASS.

The source fix only creates the MCP acceptance-report parent directory. It fixes a
fresh-extraction failure when artifacts/ does not yet exist and leaves policy and
test behavior otherwise unchanged.

## Locked engine facts

- AUTO remains Playwright-primary; preference is never authority.
- Jev: jev-ultrafast 0.1.0 at 1231850a0bf1a0c0341fe408ef1668dbbfdfac46; Python >=3.12.
- browser-harness==0.1.13; wheel SHA-256 2491459e4bfc0ee8aea22dc6c4680fc0f791b7ba553446323c50d2883449d769.
- CUA: minimum validated reference 0.28.2 and bounded mode required.

## Observed verification

| Check | Result |
| --- | --- |
| Both manifests; compileall | PASS; 87 files each |
| Full suite | PASS; 125 tests |
| Independent process stability | PASS; 10 runs, 125 tests each, 1250 total |
| Engine source lock | PASS_LOCK_ONLY |
| MCP stdio acceptance | PASS; 43 tests |
| HTTP child-process smoke | PASS; HTTP 200; CANDIDATE_NOT_PRODUCTION |
| Static security scan | PASS; 0 in-scope findings |
| Package secret scan | PASS; 0 findings; 90 text files scanned |
| Safe tar and ZIP extraction | PASS; 90 files each |
| Fresh tar suite | PASS; 125 tests |
| Fresh tar MCP acceptance with no artifacts/ | PASS; 43 tests and candidate created report directory |
| Fresh tar HTTP smoke | PASS; HTTP 200 loopback-only |
| Release gates | expected exit 2; CONDITIONAL_OFFLINE_AND_LOCAL_TRANSPORT_PASS_PRODUCTION_BLOCKED; release_ready=false |

The release verdict is deliberately not a production-ready result. It retains
non-pass gates for real ChatGPT integration, representative real journeys,
long-duration reliability, external security review, and user promotion.

## Scope and remaining local gates

The verifier used Python 3.12.13 with candidate source first on PYTHONPATH. It did
not replace the active 0.2.0a1 wrapper, change wbcp_browser configuration, attach
a Chrome profile, or use a paid API.

The active baseline stays at /Users/macpro/Library/Application Support/WBCP OneClick.
Candidate deployment, active-host reload, real wbcp_browser acceptance, CUA UI or
browser operations, and rollback/reapply remain blocked by active host-owned WBCP
workers and CUA security-state remediation. Paid Jev smoke remains
BLOCKED_PAID_API_NOT_AUTHORIZED.

The candidate suite passed synthetic policy coverage for Jev default denials,
independent verification after Jev DONE, CUA exact binding and dual-profile grants,
possible-mutation reconciliation, and duplicate-side-effect retry blocking. These
are not claims of live browser or native-app success.
