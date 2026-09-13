# Production gates

The gates are ordered. A later gate cannot repair or waive an earlier failure.

| Gate | Name | Pass condition | Failure status |
|---|---|---|---|
| G00 | Surface | Ordinary Chat and native image generation available | `BLOCKED_SURFACE_NOT_CHAT`, `BLOCKED_NATIVE_IMAGE_GEN_UNAVAILABLE` |
| G01 | Connector | Connected Google Drive read tools are available | `BLOCKED_GOOGLE_DRIVE_PLUGIN_UNAVAILABLE` |
| G02 | Selector | ID/URL is exact, or filename is an exact unique match | `BLOCKED_DRIVE_IMAGE_NOT_FOUND`, `BLOCKED_DRIVE_IMAGE_AMBIGUOUS` |
| G03 | Raw fetch | Original stored file is returned, not a thumbnail or preview | `BLOCKED_DRIVE_RAW_FETCH_FAILED` |
| G04 | Media | Allowed MIME, magic bytes, dimensions, and size | `BLOCKED_DRIVE_IMAGE_INVALID_MIME`, `BLOCKED_IMAGE_TOO_LARGE`, `BLOCKED_IMAGE_DIMENSIONS_UNSUPPORTED`, `BLOCKED_IMAGE_DECODE_FAILED` |
| G05 | Integrity | Original bytes remain unchanged through transfer | `BLOCKED_DRIVE_BYTES_MUTATED` |
| G06 | Reference bind | The native generator consumes the Drive media object as an image reference | `BLOCKED_DRIVE_IMAGE_REFERENCE_BIND_FAILED`, `BLOCKED_NATIVE_REFERENCE_BIND_UNVERIFIED` |
| G07 | Native dispatch | ChatGPT native image generation is invoked | `BLOCKED_NATIVE_IMAGE_GEN_UNAVAILABLE`, `BLOCKED_EXTERNAL_API_PROHIBITED` |
| G08 | Inline result | Generated image appears in the same Chat | `BLOCKED_NATIVE_IMAGE_RESULT_NOT_INLINE` |
| G09 | Audit | No secret leakage, no Drive write, no external image API call | `BLOCKED_AUDIT_EVIDENCE_INCOMPLETE` |

## Hard acceptance rule

The only success status is `PASS_NATIVE`.

Drive discovery, Drive download, image analysis, or a generated text prompt can never satisfy G06 through G08. A fetch-only execution must end as blocked.

## Byte-preservation rule

When raw bytes are available, compute SHA-256 immediately after retrieval and immediately before binding. The values and byte lengths must match. When the host supplies only an opaque media handle, mark byte verification as unavailable and require host-level bind evidence. Do not invent a digest.

## API prohibition

The release must not contain or request:

- `OPENAI_API_KEY`
- calls to `api.openai.com`
- Images API or Responses API image generation
- third-party image-generation endpoints
- a paid fallback hidden behind native-bind failure

A user may separately request an API product in another workflow, but that is outside this plugin.

## Release levels

- `PACKAGE_GATES_PASS`: manifest, policy, static checks, and unit tests pass.
- `DRIVE_FETCH_GATE_PASS`: an exact real Drive image was found, fetched, and validated.
- `PASS_NATIVE`: an installed ordinary Chat completed G00 through G09.
- `BLOCKED_NATIVE_REFERENCE_BIND_UNVERIFIED`: package and Drive gates pass, but the host bind was not proven.

Do not rename a lower release level to `PASS_NATIVE`.
