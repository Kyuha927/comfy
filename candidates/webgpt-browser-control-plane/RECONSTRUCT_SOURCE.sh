#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARTS="${WBCP_PARTS_DIR:-$ROOT/releases/WBCP_0.4.0a1_SOURCE.tar.gz.b64.parts}"
MANIFEST="${WBCP_PARTS_MANIFEST:-$ROOT/SOURCE_PARTS_MANIFEST.json}"
OUTPUT="${1:-$ROOT/releases/WBCP_0.4.0a1_SOURCE.tar.gz}"
python3 - "$MANIFEST" "$PARTS" "$OUTPUT" <<'PY2'
from pathlib import Path
import base64,hashlib,json,sys
manifest=Path(sys.argv[1]); parts_dir=Path(sys.argv[2]); output=Path(sys.argv[3])
spec=json.loads(manifest.read_text(encoding='utf-8'))
encoded=[]
for part in spec['parts']:
    path=parts_dir/Path(part['path']).name
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=part['sha256_utf8']:
        raise SystemExit(f'part hash mismatch: {path}')
    text=raw.decode('ascii').strip()
    if len(text)!=part['chars']:
        raise SystemExit(f'part length mismatch: {path}')
    encoded.append(text)
data=base64.b64decode(''.join(encoded),validate=True)
if len(data)!=spec['decoded_size_bytes']:
    raise SystemExit('decoded size mismatch')
actual=hashlib.sha256(data).hexdigest()
if actual!=spec['decoded_sha256']:
    raise SystemExit(f'decoded sha256 mismatch: {actual}')
output.parent.mkdir(parents=True,exist_ok=True)
output.write_bytes(data)
print(f'WBCP_SOURCE_RECONSTRUCTION_PASS={output}')
print(f'SHA256={actual}')
PY2
