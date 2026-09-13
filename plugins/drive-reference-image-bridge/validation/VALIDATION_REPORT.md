# Validation report

Date: 2026-09-14 KST

## Current verdict

```text
PACKAGE_GATES=PASS
DRIVE_EXACT_RESOLUTION=PASS
DRIVE_RAW_FETCH=PASS
SOURCE_INTEGRITY=PASS
NATIVE_REFERENCE_BIND=UNVERIFIED
EXTERNAL_IMAGE_API_CALLS=0
OVERALL=BLOCKED_NATIVE_REFERENCE_BIND_UNVERIFIED
```

This is intentionally not labeled `PASS_NATIVE`. The real Google Drive source was resolved and fetched, but full acceptance requires an installed ordinary Chat to prove that the native image-generation tool consumed the returned Drive media object and rendered an image inline.

## Canonical source evidence

- File ID: `1mPsJ38k7xfxStY3tNLnR3_OZW7U3XOIb`
- Exact name: `02_LEFT_SIDE_TPOSE_CANONICAL_LOCKED.png`
- MIME: `image/png`
- Size: `1,469,732` bytes
- Dimensions: `1024 x 1536`
- SHA-256: `99c36237f3b84d98d674ded2f95a8c137096f0b6fea1875da189e7254e7276ee`
- Re-encode, resize, crop: none

The image itself is not committed.

## Full acceptance smoke

Run in a new ordinary Chat with the plugin and Google Drive enabled:

```text
드라이브 파일 ID 1mPsJ38k7xfxStY3tNLnR3_OZW7U3XOIb의 원본 이미지를
주 참조로 사용해서 오른쪽 측면 T포즈를 생성해.
얼굴, 의상, 신체 비율을 유지하고 일반 챗의 native 이미지 생성만 사용해.
진단 영수증을 남겨.
```

Accept only when the inline image is present and the receipt validates as `PASS_NATIVE` with zero external API calls.
