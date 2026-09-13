# Source Artifact Publication Status

## Reviewed artifact identity

- Candidate: `WebGPT Browser Control Plane 0.1.0a2`
- Archive: `WBCP_0.1.0a2_SOURCE.tar.gz`
- SHA-256: `30d29628edbdba943841fd7e7958972d393924fb57f59ec96a580e500a351d51`
- Size: `62,975 bytes`
- Source file count after safe extraction: `51`
- Local reconstruction result: `PASS`
- Candidate verdict: `CONDITIONAL_OFFLINE_PASS_PRODUCTION_BLOCKED`

## Why the binary archive is not committed in this change

The available GitHub connector accepts textual blob content but does not provide an authenticated local-file upload primitive. During split Base64 publication, multiple large transfers produced blob SHA mismatches. Every mismatched or missing blob was rejected before tree attachment. No incomplete package is referenced by this branch.

The exact reviewed archive is delivered separately in the originating ChatGPT conversation. Consumers must verify the SHA-256 above before extraction or execution. A reconstruction success does not authorize use against a real account, paid provider, production browser profile, or externally visible surface.

## Required next publication gate

Publish the exact archive through an authenticated binary-safe GitHub release asset or ordinary Git push, then independently verify:

1. asset SHA-256 equals the value above;
2. archive size is `62,975 bytes`;
3. safe extraction produces exactly `51` files;
4. `MANIFEST.sha256` verifies;
5. no source, test, policy, or report file differs from the reviewed candidate.

Until that gate passes, the GitHub documents are review evidence and handoff material, not a complete source distribution.
