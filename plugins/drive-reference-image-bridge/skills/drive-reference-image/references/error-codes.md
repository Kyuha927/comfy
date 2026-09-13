# Error codes

Use one primary code and a short corrective message. Never downgrade a bind failure into a vague success.

| Code | Meaning |
|---|---|
| `BLOCKED_SURFACE_NOT_CHAT` | The request is not running in an ordinary Chat surface. |
| `BLOCKED_GOOGLE_DRIVE_PLUGIN_UNAVAILABLE` | Google Drive read tools are unavailable or disconnected. |
| `BLOCKED_DRIVE_IMAGE_NOT_FOUND` | No exact accessible Drive object matches the selector. |
| `BLOCKED_DRIVE_IMAGE_AMBIGUOUS` | Multiple accessible objects match and no exact ID disambiguates them. |
| `BLOCKED_DRIVE_RAW_FETCH_FAILED` | The stored original could not be fetched. |
| `BLOCKED_DRIVE_IMAGE_INVALID_MIME` | The declared or detected type is not an allowed image MIME. |
| `BLOCKED_IMAGE_TOO_LARGE` | The image exceeds 20 MiB. |
| `BLOCKED_IMAGE_DIMENSIONS_UNSUPPORTED` | Width or height is outside 32 through 8192 pixels. |
| `BLOCKED_IMAGE_DECODE_FAILED` | The raw bytes are not a valid supported image. |
| `BLOCKED_DRIVE_BYTES_MUTATED` | Source and pre-bind byte length or SHA-256 differ. |
| `BLOCKED_DRIVE_IMAGE_REFERENCE_BIND_FAILED` | The Drive media object could not be supplied to native image generation. |
| `BLOCKED_NATIVE_REFERENCE_BIND_UNVERIFIED` | The host did not expose sufficient evidence that native generation consumed the Drive image. |
| `BLOCKED_NATIVE_IMAGE_GEN_UNAVAILABLE` | ChatGPT native image generation is unavailable in this Chat. |
| `BLOCKED_NATIVE_IMAGE_RESULT_NOT_INLINE` | Native generation ran but no image appeared in the same Chat. |
| `BLOCKED_EXTERNAL_API_PROHIBITED` | A route attempted to use a separately billed API or external generator. |
| `BLOCKED_API_FALLBACK_NOT_CONFIGURED` | Compatibility alias only. This plugin intentionally has no API fallback. |
| `BLOCKED_AUDIT_EVIDENCE_INCOMPLETE` | Required acceptance evidence is missing or contradictory. |
