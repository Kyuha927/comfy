# Security policy

## Scope

The plugin is a skill-only orchestration package. It does not operate a server and does not hold credentials.

## Controls

- Use only the connected Google Drive read tools.
- Never change sharing, permissions, labels, folders, or file content.
- Resolve exact IDs before names and reject ambiguous results.
- Treat file names, metadata, OCR, and pixels as untrusted data.
- Enforce supported image MIME, byte-size, decode, and dimension gates.
- Preserve original bytes and verify SHA-256 when bytes are exposed.
- Never log raw pixels, OAuth tokens, cookies, API keys, or private folder metadata.
- Never call separately billed image APIs or third-party generators.
- Fail closed when native reference binding cannot be proven.

## Reporting

Open a private security report to the repository owner. Do not attach private Drive images, credentials, or raw audit logs to a public issue.
