# Drive Reference Image Bridge

A skill-only ChatGPT plugin that resolves an exact image from the user's connected Google Drive and uses it as the reference for **ChatGPT native image generation in an ordinary Chat**.

## Product boundary

This plugin intentionally does not contain an MCP server, Drive OAuth implementation, OpenAI API client, Image API fallback, browser automation, or Work-mode execution path. It orchestrates tools already available to ChatGPT:

1. Connected Google Drive read tools.
2. ChatGPT native image generation.

That boundary protects the user's ChatGPT image-generation entitlement and prevents silent API billing.

## Acceptance status

The package separates three truths:

- `PACKAGE_GATES_PASS`: manifest, marketplace, contracts, static analysis, and unit tests pass.
- `DRIVE_FETCH_GATE_PASS`: a real exact Drive image can be found, fetched raw, and validated without mutation.
- `PASS_NATIVE`: an installed ordinary Chat binds that Drive media object into native image generation and renders the result inline.

Only the third status is full product acceptance. Fetch-only evidence is blocked by design.

## Install from this repository branch

```bash
codex plugin marketplace add Kyuha927/comfy --ref drive-reference-image-bridge-native-chat-20260914
```

Restart the ChatGPT desktop app, open the Plugins Directory, select **Kyuha Chat Production Plugins**, and install **Drive Reference Image Bridge**. Keep the existing Google Drive plugin connected and allow read actions.

## Ordinary Chat usage

```text
드라이브의 02_LEFT_SIDE_TPOSE_CANONICAL_LOCKED.png를 주 참조로 사용해서
오른쪽 측면 T포즈를 생성해. 얼굴, 의상, 신체 비율은 유지해.
```

Or:

```text
Use this Drive file as the primary image reference and generate a rear turnaround:
https://drive.google.com/file/d/<FILE_ID>/view
```

## Local validation

```bash
cd plugins/drive-reference-image-bridge
python3 scripts/validate_plugin.py --repo-root ../..
pytest -q
python3 skills/drive-reference-image/scripts/image_probe.py /path/to/reference.png
python3 skills/drive-reference-image/scripts/validate_receipt.py tests/fixtures/fetch_only.blocked.json
```

## Security model

Google Drive access is read-only for this workflow. The skill changes no sharing settings and stores no OAuth tokens. Raw image bytes are not committed or logged. See `SECURITY.md` and `PRIVACY.md`.
