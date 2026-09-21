## WBCP 0.4.0a1 safe signup candidate

This Draft PR publishes the exact source archive as hash-verified text chunks plus reproducible build and validation receipts.

### Verified non-local evidence

- 172/172 unit, integration, and security tests PASS
- real Chromium offline signup DOM, pixel, direct-user handoff, and evidence-chain path PASS
- synthetic offline browser-response receipt PASS
- real provider account transaction NOT RUN
- worker-router acceptance PASS
- static security and focused secret scans PASS with zero findings
- four independent 250-operation, 8-worker short soaks: 1000/1000 PASS
- tar.gz, ZIP, and Git bundle reconstructions each rerun 172 tests PASS
- two independent builds produce identical artifact hashes

### Exact source

`WBCP_0.4.0a1_SOURCE.tar.gz` SHA-256: `ec006c9080a87c9ef1c6a49b5559b5eb328b456ed2391d755c2b3cc7ef06282e`

### Explicitly not proven

- target-Mac installed runtime identity and plugin deployment
- macOS Accessibility/Screen Recording and live CUA window/dialog path
- live Jev isolated-profile attachment
- one explicitly approved disposable free-provider account E2E
- real provider HTTP/account receipt
- local rollback restoration
- independent release review
- 24-hour mixed-route soak
- production promotion

### Safety boundary

No merge, production write, personal-profile attachment, paid provider call, payment/subscription activation, CAPTCHA/OTP automation, real-account creation, or production release is authorized by this PR.
