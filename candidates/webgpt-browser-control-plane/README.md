# WBCP 0.4.0a1 Safe Account Registration Candidate

## Status

```text
CANDIDATE_IMPLEMENTATION=COMPLETE
FULL_REGRESSION=172_PASS
REAL_OFFLINE_CHROMIUM_SIGNUP_RECEIPT=PASS
REPEATED_SHORT_SOAK=4_X_250_PASS
TOTAL_SHORT_SOAK_OPERATIONS=1000_PASS
TAR_RECONSTRUCTION=PASS
ZIP_RECONSTRUCTION=PASS
GIT_BUNDLE_RECONSTRUCTION=PASS
PRODUCTION_READY=false
PRODUCTION_PROMOTION_GRANTED=false
```

This candidate adds a single-account registration state machine to WBCP. It can automate ordinary public form navigation and field preparation, then pause at every user-only boundary. Passwords, passkeys, OTP or SMS codes, email verification, CAPTCHA, KYC, recovery data, legal consent, and payment data are never supplied by the model and are not stored in the registration database.

The final account-creation action is allowed only after all of the following are bound and verified:

- one exact provider host and one account intent;
- the current page revision, DOM digest, and pixel digest;
- a semantic final-submit target or an observed CUA reference;
- exact expected postconditions;
- exact terms URL and digest when terms apply;
- a direct-user handoff proof;
- one finite R4 permit;
- one one-shot high-impact approval;
- DOM or URL change, pixel change, and provider or network receipt.

Bulk or parallel signup, fake or disposable identity flags, malformed account counts, CAPTCHA bypass, model-visible secrets, silent legal consent, and duplicate final submission fail closed.

## Authoritative source

`releases/WBCP_0.4.0a1_SOURCE.tar.gz.b64.parts/` reconstructed by `RECONSTRUCT_SOURCE.sh`

SHA-256:

```text
2a56f8929f5850ea640deb562fac5c52525cade27a83bf7cc7d199c863039555
```

The complete delivery ZIP also contains byte-for-byte reproducible ZIP and Git bundle alternate forms. Two independent builds produced identical hashes for every release artifact.

## Reconstruct and verify

```bash
./RECONSTRUCT_SOURCE.sh /tmp/WBCP_0.4.0a1_SOURCE.tar.gz
mkdir -p /tmp/wbcp-verify
python3 - <<'PY'
import pathlib, tarfile
archive = pathlib.Path('/tmp/WBCP_0.4.0a1_SOURCE.tar.gz')
out = pathlib.Path('/tmp/wbcp-verify')
with tarfile.open(archive, 'r:gz') as tf:
    for member in tf.getmembers():
        p = pathlib.PurePosixPath(member.name)
        if p.is_absolute() or '..' in p.parts or member.issym() or member.islnk():
            raise SystemExit(f'unsafe archive member: {member.name}')
    tf.extractall(out, filter='data')
PY
cd /tmp/wbcp-verify/WBCP_0.4.0a1
python3 scripts/verify_source_manifest.py --manifest SOURCE_MANIFEST.sha256
PYTHONPATH=src:tests python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## Important boundary

This branch is a reviewable candidate and exact-source publication surface. It does not authorize merge, local plugin replacement, personal-profile attachment, CAPTCHA or OTP automation, paid provider calls, real-account creation, or production promotion.

The remaining exact-path gates are recorded in `validation/RELEASE_GATES.json` and `FINAL_STATUS_KO.md`.
