# WBCP 0.3.0a1 Phase B isolated local rebinding - 2026-09-22

## Status

- Result: `PASS_CANDIDATE_LOCAL_ISOLATED`.
- This is a candidate-only local proof. It did not replace the active WBCP
  `0.2.0a1` wrapper, reload `wbcp_browser`, alter Codex configuration, attach a
  personal Chrome profile, or call a paid service.
- Canonical local-lane handoff: https://github.com/Kyuha927/comfy/pull/4

## Exact remote binding

- Source evidence commit: `5eb0c372c010638210ef66ce63ed06722d0cd984`.
- Candidate subtree: `fedf884713d30daae3ac3bf119d6d1b96aa12d87`.
- Version read from the isolated editable install: `0.3.0a1`.
- `MANIFEST.sha256` and `PACKAGE_MANIFEST.sha256`:
  `2e078eaf106ab79ba7feed68eb4754260db1930b76b7b5818c71f21304445745`
  (87 verified source files each).
- Reproducible source tar / ZIP SHA-256:
  `314b8d5fc88f156c03b8622ec2739ff936393a636a868c2bc3235d086c675a00` /
  `73394a7f9633f63f59dd5db9261e84e447d34b2e9858698bf9103ce680ac70a2`.

## Isolated environment and executed checks

- Environment: dedicated Python `3.12.13` virtual environment; `pip check`
  exit `0` with `No broken requirements found`.
- From the fresh remote clone's candidate root, all following commands exited
  `0`:

  ```text
  $VENV/bin/python scripts/verify_source_manifest.py
  $VENV/bin/python -m compileall -q src tests
  PYTHONPATH=src:tests $VENV/bin/python -m unittest discover -s tests -p 'test_*.py' -v
  $VENV/bin/python scripts/run_mcp_acceptance.py
  PYTHONPATH=src $VENV/bin/python scripts/run_http_process_smoke.py
  ```

- Results: source manifest `87` files PASS; full unit/integration suite `125`
  tests PASS in `3.432s`; candidate MCP acceptance `43` tests PASS in `0.398s`;
  loopback HTTP child-process smoke PASS with HTTP `200` in `0.446s` and
  `CANDIDATE_NOT_PRODUCTION`.

## Local and CUA boundaries

- Fresh CUA readback: `cua-driver 0.28.2`; `doctor --json` returned `ok=true`;
  daemon PID `45001` was healthy; Accessibility and Screen Recording were
  granted. Direct Capture remains a historical `permissions_grant` observation,
  not a fresh capture probe.
- The daemon reports `standard (trusted_startup_configuration)`, not a verified
  bounded operating mode. The existing app-owned LaunchAgent contains
  `--grant existing-profile`. Neither value was changed.
- Candidate CUA/Jev executor registration remains absent. Consequently no live
  CUA or Jev browser/native action was claimed; paid Jev smoke remains
  `BLOCKED_PAID_API_NOT_AUTHORIZED`.

## Deployment blockers retained

- Active baseline WBCP workers remain host-owned: `19` observed
  `wbcp.cli serve-stdio` processes, sample parent PID `38901`. They were not
  interrupted.
- Active deployment, active `wbcp_browser` acceptance, actual rollback/reapply,
  and live CUA smoke remain blocked until the host-owned WBCP lifecycle is safely
  drained and the CUA bounded/profile-grant conditions are remediated through
  their appropriate approval surfaces.
