# WBCP 0.3.0a1 Remote Candidate Receipt

## Scope and authority

- Candidate branch: `candidate/webgpt-browser-control-plane-jev-cua-0.3.0a1-20260921`
- Integration base: `work-handoffs-v4-20260912`
- Freshly observed base commit/tree: `7f9c5701a77d341bd7ca680b06242980600000dd` / `f2da7f6e46538dbc4d7a9129ebae24cfba461162`
- Candidate source commit: `313926dd54018c7bc74d78dc3101c85636c99b84`
- Candidate enclosing commit tree: `5117cffd0781b814653f1a311ff90e1cbbe84098`
- Candidate source subtree: `e50635bca7d2f66218743dd780aac20674861a54`
- Base ancestry check: `PASS` (`7f9c5701a77d341bd7ca680b06242980600000dd` is an ancestor of the candidate)
- Rejected non-authority: `candidate/webgpt-browser-control-plane-jev-cua-20260921` at `d3aa0ba287ba244a4e03cb2f3f4f1171d72b0957`; it was never reused or overwritten.

The single source-of-truth handoff URL for the local lane is:

`https://github.com/Kyuha927/comfy/tree/candidate/webgpt-browser-control-plane-jev-cua-0.3.0a1-20260921`

## Candidate identity

- Version: `0.3.0a1`
- Candidate source files: `87`
- Packaged files: `90` (the 87 source files plus the three tracked manifests)
- `MANIFEST.sha256` SHA-256: `9214011050eacfefe441b9b0c049f5481e00166844e2b615584789d942200f38`
- `SOURCE_MANIFEST.sha256` SHA-256: `9214011050eacfefe441b9b0c049f5481e00166844e2b615584789d942200f38`
- `PACKAGE_MANIFEST.sha256` SHA-256: `9214011050eacfefe441b9b0c049f5481e00166844e2b615584789d942200f38`
- Source archive (`WBCP_0.3.0a1_SOURCE.tar.gz`): `84cea8b47e19966f924b3442a87da8f912e6b6d6c34f7d490d834febde20f5ca` (`128344` bytes)
- Source ZIP (`WBCP_0.3.0a1_SOURCE.zip`): `b06b842316d97bd2e1ac60f73d0e9fba289fc381f34619d756cc22da4b6ec087` (`179309` bytes)
- Jev source lock: `browser-use/jev-ultrafast` `0.1.0` at `1231850a0bf1a0c0341fe408ef1668dbbfdfac46`; direct local source verification: `PASS_SOURCE_VERIFIED`.
- Browser harness lock: `browser-harness==0.1.13`.
- CUA policy minimum validated stable reference: `0.28.2`, bounded mode only.

## Executed verification

| Check | Command class | Observed result |
| --- | --- | --- |
| Source manifests | `scripts/verify_source_manifest.py` | exit `0`, `87` verified files |
| Compilation | `python -m compileall -q src tests scripts` | exit `0` |
| Full suite | `PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'` | exit `0`, `125` tests |
| Jev source lock | `scripts/verify_engine_sources.py --jev-source <verified checkout>` | exit `0`, `PASS_SOURCE_VERIFIED` |
| Repeated suite | `scripts/run_exit_stability.py --runs 10` | exit `0`, `10 × 125 = 1250` tests; report bound to the current manifest hash |
| MCP stdio acceptance | `scripts/run_mcp_acceptance.py` via release gate | exit `0` |
| HTTP process smoke | `scripts/run_http_process_smoke.py` via release gate | exit `0` |
| Scoped static security scan | `scripts/security_static_checks.py` via release gate | exit `0`, no findings within scanner scope |
| Package secret/sensitive-file scan | `scripts/scan_package_secrets.py` via release gate | exit `0`, no findings within scanner scope |
| Deterministic archive rebuild | two independent `scripts/package_candidate.py` runs | exit `0`; both tar.gz and ZIP byte-identical |
| Safe fresh extraction | `scripts/safe_extract_candidate.py` for tar.gz and ZIP | exit `0`, `90` files each |
| Fresh extracted source | manifest check, compileall, full suite, repackaging | exit `0`, `87` manifest files, `125` tests, both rebuilt archive hashes exactly match |
| Release gate | `scripts/run_release_gates.py` | exit `2` by design; `CONDITIONAL_OFFLINE_AND_LOCAL_TRANSPORT_PASS_PRODUCTION_BLOCKED`, `release_ready=false` |

The current source-manifest binding in the release gate matched on both sides:
`9214011050eacfefe441b9b0c049f5481e00166844e2b615584789d942200f38`.

## Remaining blockers and boundaries

- `PRODUCTION_READY=false`: real representative journeys, production identity/key custody, external security review, 24-hour soak, independent release decision, and explicit production promotion are not present.
- `BLOCKED_CURRENT_WBCP_SOURCE_IDENTITY_UNRESOLVED` is resolved only for this isolated candidate; the active `0.2.0a1` OneClick runtime remains unchanged until separate local candidate acceptance completes.
- `BLOCKED_CUA_DRIVER_BELOW_MINIMUM_VALIDATED_REFERENCE` remains pending an official-supported current-stable upgrade assessment and its backup/recovery gate.
- `JEV_LIVE_PAID_SMOKE=BLOCKED_PAID_API_NOT_AUTHORIZED`; no paid service was called.
- No default or existing personal Chrome profile, authentication state, payment/security setting, TCC setting, production runtime, or incomplete candidate branch was changed.

## Publication intent

This receipt is created before remote publication. The next allowed operation is a non-force push of this exact branch followed by a fresh remote clone verification and a Draft PR against the recorded integration base. It authorizes neither merge nor production promotion.
