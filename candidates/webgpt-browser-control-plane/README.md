# WBCP 0.4.0a1 Safe Signup Candidate

This directory publishes the exact, reconstructed source candidate and evidence packet for safe single-account registration.

## Verified candidate state

- tests: 172/172 PASS
- real Chromium offline DOM/pixel/user-handoff path: PASS
- synthetic offline browser-response receipt: PASS
- real provider account transaction: NOT RUN
- repeated short soak: 1000/1000 PASS
- static security and focused secret scans: PASS, zero findings
- production ready: false
- production promotion: not granted

## Reconstruct exact source

```bash
bash RECONSTRUCT_SOURCE.sh /tmp/WBCP_0.4.0a1_SOURCE.tar.gz
sha256sum /tmp/WBCP_0.4.0a1_SOURCE.tar.gz
# expected: ec006c9080a87c9ef1c6a49b5559b5eb328b456ed2391d755c2b3cc7ef06282e
```

Extract only after rejecting absolute paths, `..`, symlinks, and hard links. The CI workflow performs that safe extraction and reruns manifests, 172 tests, router acceptance, offline signup acceptance, security scans, and the expected production-blocked release gate.

## Safety boundary

This branch is a reviewable candidate and source-delivery surface. It does not authorize merge, target-Mac plugin replacement, personal-profile attachment, real-account creation, paid provider use, CAPTCHA/OTP automation, payment or subscription activation, or production promotion.
