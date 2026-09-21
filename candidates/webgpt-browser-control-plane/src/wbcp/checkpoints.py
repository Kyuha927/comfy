from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .evidence import EvidenceLedger


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def generate_keypair(private_path: str | os.PathLike[str], public_path: str | os.PathLike[str]) -> dict[str, str]:
    private_file = Path(private_path)
    public_file = Path(public_path)
    private_file.parent.mkdir(parents=True, exist_ok=True)
    public_file.parent.mkdir(parents=True, exist_ok=True)
    if private_file.exists() or public_file.exists():
        raise FileExistsError("Checkpoint key path already exists")
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    private_file.write_bytes(
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    os.chmod(private_file, 0o600)
    public_file.write_bytes(
        public_key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    os.chmod(public_file, 0o644)
    return {"private_key": str(private_file), "public_key": str(public_file)}


def sign_ledger_checkpoint(
    ledger: EvidenceLedger,
    *,
    private_key_path: str | os.PathLike[str],
    output_path: str | os.PathLike[str],
    instance_id: str,
) -> dict[str, Any]:
    verification = ledger.verify()
    if not verification.valid:
        raise ValueError(f"Cannot sign an invalid evidence ledger: {verification.error}")
    key = serialization.load_pem_private_key(Path(private_key_path).read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise TypeError("Checkpoint private key must be Ed25519")
    public_raw = key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    body = {
        "schema_version": "1.0",
        "algorithm": "Ed25519",
        "instance_id": instance_id,
        "event_count": verification.event_count,
        "root_hash": verification.root_hash,
        "created_at": time.time(),
        "public_key_raw_base64": base64.b64encode(public_raw).decode("ascii"),
    }
    signature = key.sign(_canonical(body))
    checkpoint = {**body, "signature_base64": base64.b64encode(signature).decode("ascii")}
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(output.suffix + ".tmp")
    tmp.write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, output)
    return checkpoint


def verify_checkpoint(
    checkpoint_path: str | os.PathLike[str],
    *,
    public_key_path: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    checkpoint = json.loads(Path(checkpoint_path).read_text(encoding="utf-8"))
    signature = base64.b64decode(checkpoint.pop("signature_base64"), validate=True)
    embedded_raw = base64.b64decode(checkpoint["public_key_raw_base64"], validate=True)
    if public_key_path:
        loaded = serialization.load_pem_public_key(Path(public_key_path).read_bytes())
        if not isinstance(loaded, Ed25519PublicKey):
            raise TypeError("Checkpoint public key must be Ed25519")
        external_raw = loaded.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        if external_raw != embedded_raw:
            return {"valid": False, "error": "public key mismatch"}
        public_key = loaded
    else:
        public_key = Ed25519PublicKey.from_public_bytes(embedded_raw)
    try:
        public_key.verify(signature, _canonical(checkpoint))
        return {
            "valid": True,
            "event_count": checkpoint["event_count"],
            "root_hash": checkpoint["root_hash"],
            "instance_id": checkpoint["instance_id"],
        }
    except InvalidSignature:
        return {"valid": False, "error": "signature mismatch"}
