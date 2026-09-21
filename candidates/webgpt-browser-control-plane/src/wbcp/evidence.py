from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .redaction import Redactor


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(slots=True)
class LedgerVerification:
    valid: bool
    event_count: int
    root_hash: str
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "event_count": self.event_count,
            "root_hash": self.root_hash,
            "error": self.error,
        }


class EvidenceLedger:
    """Append-only, redacted, hash-chained evidence log.

    The HMAC key is deployment-local. The ledger proves internal tamper evidence,
    not third-party non-repudiation. A production release should additionally sign
    the root digest with a managed asymmetric key and anchor it outside the host.
    """

    def __init__(
        self,
        path: str | os.PathLike[str],
        *,
        hmac_key: bytes,
        redactor: Redactor | None = None,
    ) -> None:
        if len(hmac_key) < 32:
            raise ValueError("Evidence HMAC key must be at least 32 bytes")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.hmac_key = hmac_key
        self.redactor = redactor or Redactor()
        self._lock = threading.RLock()
        if not self.path.exists():
            self.path.touch(mode=0o600)

    def _last(self) -> tuple[int, str]:
        last_seq = 0
        last_hash = "0" * 64
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                event = json.loads(line)
                last_seq = int(event["seq"])
                last_hash = str(event["event_hash"])
        return last_seq, last_hash

    def append(self, event_type: str, job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            seq, prev_hash = self._last()
            body = {
                "seq": seq + 1,
                "timestamp": time.time(),
                "event_type": event_type,
                "job_id": job_id,
                "prev_hash": prev_hash,
                "payload": self.redactor.redact(payload),
            }
            event_hash = hashlib.sha256(_canonical(body)).hexdigest()
            signature = hmac.new(self.hmac_key, event_hash.encode("ascii"), hashlib.sha256).hexdigest()
            event = {**body, "event_hash": event_hash, "signature": signature}
            encoded = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            fd = os.open(self.path, os.O_WRONLY | os.O_APPEND)
            try:
                os.write(fd, (encoded + "\n").encode("utf-8"))
                os.fsync(fd)
            finally:
                os.close(fd)
            return event

    def verify(self) -> LedgerVerification:
        expected_seq = 1
        prev_hash = "0" * 64
        root_hash = prev_hash
        try:
            with self.path.open("r", encoding="utf-8") as fh:
                for line_number, line in enumerate(fh, 1):
                    if not line.strip():
                        continue
                    event = json.loads(line)
                    if int(event["seq"]) != expected_seq:
                        return LedgerVerification(False, expected_seq - 1, root_hash, f"sequence mismatch at line {line_number}")
                    if event["prev_hash"] != prev_hash:
                        return LedgerVerification(False, expected_seq - 1, root_hash, f"previous hash mismatch at line {line_number}")
                    body = {
                        "seq": event["seq"],
                        "timestamp": event["timestamp"],
                        "event_type": event["event_type"],
                        "job_id": event["job_id"],
                        "prev_hash": event["prev_hash"],
                        "payload": event["payload"],
                    }
                    calculated = hashlib.sha256(_canonical(body)).hexdigest()
                    if calculated != event["event_hash"]:
                        return LedgerVerification(False, expected_seq - 1, root_hash, f"event hash mismatch at line {line_number}")
                    expected_sig = hmac.new(
                        self.hmac_key, calculated.encode("ascii"), hashlib.sha256
                    ).hexdigest()
                    if not hmac.compare_digest(expected_sig, str(event["signature"])):
                        return LedgerVerification(False, expected_seq - 1, root_hash, f"signature mismatch at line {line_number}")
                    prev_hash = calculated
                    root_hash = calculated
                    expected_seq += 1
            return LedgerVerification(True, expected_seq - 1, root_hash)
        except Exception as exc:  # noqa: BLE001 - verifier must report, not crash
            return LedgerVerification(False, expected_seq - 1, root_hash, f"{type(exc).__name__}: {exc}")

    def read_events(self, *, job_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if limit < 1 or limit > 500:
            raise ValueError("limit must be between 1 and 500")
        events: list[dict[str, Any]] = []
        with self._lock:
            with self.path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    event = json.loads(line)
                    if job_id is not None and str(event.get("job_id")) != job_id:
                        continue
                    events.append(event)
                    if len(events) > limit:
                        del events[0]
        return events

    def root_hash(self) -> str:
        result = self.verify()
        if not result.valid:
            raise RuntimeError(f"Evidence ledger verification failed: {result.error}")
        return result.root_hash
