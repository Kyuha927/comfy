# Security and privacy notes

## Default posture

- Bind to `127.0.0.1`.
- Use an SSH tunnel for Mac-to-GPU access.
- Require a token for deliberate non-loopback access.
- Keep model caches, source music, lyrics, credentials, and outputs outside Git.
- Treat creative assets and provider receipts as sensitive.

## Controls present

| Risk | Control |
|---|---|
| Path traversal | normalized names, random IDs, `resolve()` containment checks |
| Oversized upload | streaming byte limit and empty-file rejection |
| Command injection | argv arrays only, no shell, command provider requires absolute executable |
| Template injection | only `{request_json}`, `{output_dir}`, `{provider_id}` placeholders are accepted |
| Malicious provider receipt | required JSON schema subset, relative outputs only, containment and non-empty checks |
| Credential leakage | provider argv is not returned through API; secrets remain in operator environment/keychain bridge |
| Hung process | timeout plus process-group TERM/KILL and retained logs |
| GPU contention | exactly one worker plus single-instance data lock |
| False success | receipt/status/file agreement and terminal status only after indexing |
| Cross-project reference | project ownership and source-job kind/status validation |
| DNS rebinding | explicit trusted-host allow-list; wildcard requires token |
| Browser embedding | CSP `frame-ancestors 'none'` and `X-Frame-Options: DENY` |
| MIME sniffing | `X-Content-Type-Options: nosniff` |
| Commercial ambiguity | explicit intent/acknowledgement, provider commercial state, terms reference, retained warnings |
| Noncommercial source audio leakage | selected YuE2 audio is stored under audit only and never copied to provider packages |

## Command provider boundary

A command adapter is trusted operator software. The controller does not accept arbitrary argv through HTTP. Provider definitions are loaded only from process configuration, validated at startup, and never exposed to browser clients. For commercial live execution, the provider must be marked `operator-verified` and should record a terms or contract reference.

## Deliberate exclusions

The alpha does not provide accounts, public multi-tenancy, cloud secrets, payment, rights clearance, automatic publication, or arbitrary plugin installation. Do not expose it directly to the public internet.

## Copyright and consent

The controller cannot determine whether lyrics, melody, recordings, voices, style references, generated scores, or final outputs may be used commercially. Operators must obtain applicable rights and avoid unauthorized artist or voice impersonation.
