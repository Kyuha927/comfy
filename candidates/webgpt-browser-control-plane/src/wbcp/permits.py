from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from .errors import ControlPlaneError, FailureCode
from .models import ActionRequest, ApprovalKind, RiskTier


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    """Decode only the unique unpadded Base64url representation.

    Python's permissive decoder accepts several final characters that differ only
    in unused padding bits. Accepting those aliases makes a byte-identical HMAC
    appear under multiple token strings and can defeat string-level tamper tests.
    """
    if not data or "=" in data:
        raise ValueError("Base64url segment must be non-empty and unpadded")
    try:
        encoded = data.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("Base64url segment must be ASCII") from exc
    if any(
        not (
            ord("A") <= byte <= ord("Z")
            or ord("a") <= byte <= ord("z")
            or ord("0") <= byte <= ord("9")
            or byte in {ord("-"), ord("_")}
        )
        for byte in encoded
    ):
        raise ValueError("Base64url segment contains an invalid character")
    if len(encoded) % 4 == 1:
        raise ValueError("Base64url segment has an impossible length")
    padded = encoded + b"=" * (-len(encoded) % 4)
    decoded = base64.b64decode(padded, altchars=b"-_", validate=True)
    if _b64url_encode(decoded) != data:
        raise ValueError("Base64url segment is not canonical")
    return decoded


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class SignedTokenCodec:
    def __init__(self, secret: bytes, issuer: str = "wbcp") -> None:
        if len(secret) < 32:
            raise ValueError("Signing secret must be at least 32 bytes")
        self._secret = secret
        self.issuer = issuer

    def encode(self, kind: str, claims: dict[str, Any]) -> str:
        header = {"alg": "HS256", "typ": "WBCP", "kind": kind}
        payload = {"iss": self.issuer, **claims}
        h = _b64url_encode(_canonical(header))
        p = _b64url_encode(_canonical(payload))
        sig = hmac.new(self._secret, f"{h}.{p}".encode("ascii"), hashlib.sha256).digest()
        return f"{h}.{p}.{_b64url_encode(sig)}"

    def decode(self, token: str, *, expected_kind: str) -> dict[str, Any]:
        try:
            h, p, s = token.split(".")
            header = json.loads(_b64url_decode(h))
            payload = json.loads(_b64url_decode(p))
            supplied = _b64url_decode(s)
            if not isinstance(header, dict) or not isinstance(payload, dict):
                raise ValueError("Signed-token header and payload must be objects")
        except Exception as exc:  # noqa: BLE001 - convert all malformed token errors
            raise ControlPlaneError(FailureCode.BLOCKED_PERMIT_INVALID, "Malformed signed token") from exc
        expected = hmac.new(self._secret, f"{h}.{p}".encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(supplied, expected):
            raise ControlPlaneError(FailureCode.BLOCKED_PERMIT_INVALID, "Token signature mismatch")
        if header.get("alg") != "HS256" or header.get("kind") != expected_kind:
            raise ControlPlaneError(FailureCode.BLOCKED_PERMIT_INVALID, "Token type mismatch")
        if payload.get("iss") != self.issuer:
            raise ControlPlaneError(FailureCode.BLOCKED_PERMIT_INVALID, "Token issuer mismatch")
        return payload


class PermitRegistry:
    def __init__(self, db_path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._conn:
            self._conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS permit_usage (
                    permit_id TEXT PRIMARY KEY,
                    calls INTEGER NOT NULL DEFAULT 0,
                    spent REAL NOT NULL DEFAULT 0,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS permit_consumption (
                    permit_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    amount REAL NOT NULL,
                    created_at REAL NOT NULL,
                    PRIMARY KEY (permit_id, idempotency_key)
                );
                CREATE TABLE IF NOT EXISTS approval_consumption (
                    approval_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    consumed_at REAL NOT NULL
                );
                """
            )

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def consume_authorization(
        self,
        *,
        permit_id: str,
        idempotency_key: str,
        amount: float,
        max_calls: int,
        max_cost: float,
        approval_id: str | None = None,
        approval_job_id: str | None = None,
    ) -> dict[str, float | int | bool]:
        """Atomically consume the finite permit and optional one-shot approval.

        The approval and permit are one authorization decision. Consuming either one
        without the other can burn a user's permit after a failed approval check.
        This transaction therefore makes the pair all-or-nothing and permits only
        an exact idempotent replay for the same permit key and approval/job binding.
        """
        if (approval_id is None) != (approval_job_id is None):
            raise ValueError("approval_id and approval_job_id must be supplied together")
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                prior = self._conn.execute(
                    "SELECT amount FROM permit_consumption WHERE permit_id=? AND idempotency_key=?",
                    (permit_id, idempotency_key),
                ).fetchone()
                usage = self._conn.execute(
                    "SELECT calls, spent FROM permit_usage WHERE permit_id=?", (permit_id,)
                ).fetchone()
                calls = int(usage["calls"]) if usage else 0
                spent = float(usage["spent"]) if usage else 0.0

                approval_prior = None
                if approval_id is not None:
                    approval_prior = self._conn.execute(
                        "SELECT job_id FROM approval_consumption WHERE approval_id=?",
                        (approval_id,),
                    ).fetchone()

                if prior is not None:
                    if abs(float(prior["amount"]) - amount) > 1e-9:
                        raise ControlPlaneError(
                            FailureCode.BLOCKED_IDEMPOTENCY_CONFLICT,
                            "Replayed permit consumption changed cost",
                        )
                    if approval_id is not None:
                        if approval_prior is None or approval_prior["job_id"] != approval_job_id:
                            raise ControlPlaneError(
                                FailureCode.BLOCKED_APPROVAL_REPLAY,
                                "Idempotent permit replay does not match approval consumption",
                            )
                    self._conn.execute("COMMIT")
                    return {"calls": calls, "spent": spent, "replayed": True}

                if approval_prior is not None:
                    raise ControlPlaneError(
                        FailureCode.BLOCKED_APPROVAL_REPLAY,
                        "Approval token is one-shot and has already been consumed",
                        {"prior_job_id": approval_prior["job_id"]},
                    )
                if calls + 1 > max_calls or spent + amount > max_cost + 1e-9:
                    raise ControlPlaneError(
                        FailureCode.BLOCKED_PERMIT_EXHAUSTED,
                        "Finite permit call or cost limit exhausted",
                        {
                            "calls": calls,
                            "max_calls": max_calls,
                            "spent": spent,
                            "max_cost": max_cost,
                            "requested_amount": amount,
                        },
                    )

                now = time.time()
                self._conn.execute(
                    "INSERT OR REPLACE INTO permit_usage(permit_id,calls,spent,updated_at) VALUES(?,?,?,?)",
                    (permit_id, calls + 1, spent + amount, now),
                )
                self._conn.execute(
                    "INSERT INTO permit_consumption(permit_id,idempotency_key,amount,created_at) VALUES(?,?,?,?)",
                    (permit_id, idempotency_key, amount, now),
                )
                if approval_id is not None:
                    self._conn.execute(
                        "INSERT INTO approval_consumption(approval_id,job_id,consumed_at) VALUES(?,?,?)",
                        (approval_id, approval_job_id, now),
                    )
                self._conn.execute("COMMIT")
                return {"calls": calls + 1, "spent": spent + amount, "replayed": False}
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

    def consume_permit(
        self,
        *,
        permit_id: str,
        idempotency_key: str,
        amount: float,
        max_calls: int,
        max_cost: float,
    ) -> dict[str, float | int | bool]:
        return self.consume_authorization(
            permit_id=permit_id,
            idempotency_key=idempotency_key,
            amount=amount,
            max_calls=max_calls,
            max_cost=max_cost,
        )

    def consume_approval(self, approval_id: str, job_id: str) -> None:
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                prior = self._conn.execute(
                    "SELECT job_id FROM approval_consumption WHERE approval_id=?", (approval_id,)
                ).fetchone()
                if prior is not None:
                    raise ControlPlaneError(
                        FailureCode.BLOCKED_APPROVAL_REPLAY,
                        "Approval token is one-shot and has already been consumed",
                        {"prior_job_id": prior["job_id"]},
                    )
                self._conn.execute(
                    "INSERT INTO approval_consumption(approval_id,job_id,consumed_at) VALUES(?,?,?)",
                    (approval_id, job_id, time.time()),
                )
                self._conn.execute("COMMIT")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise


@dataclass(slots=True)
class PermitValidation:
    permit_id: str
    subject: str
    claims: dict[str, Any]
    usage: dict[str, float | int | bool]


class PermitAuthority:
    def __init__(self, secret: bytes, registry: PermitRegistry, *, issuer: str = "wbcp") -> None:
        self.codec = SignedTokenCodec(secret, issuer)
        self.registry = registry

    @staticmethod
    def random_secret() -> bytes:
        return secrets.token_bytes(32)

    def issue(
        self,
        *,
        subject: str,
        session_id: str,
        allowed_actions: list[str],
        exact_hosts: list[str],
        risk_ceiling: RiskTier,
        max_calls: int,
        max_cost: float = 0.0,
        currency: str = "USD",
        ttl_seconds: int = 300,
        not_before: float | None = None,
    ) -> str:
        if max_calls < 1 or max_calls > 10_000:
            raise ValueError("max_calls outside safe range")
        if max_cost < 0:
            raise ValueError("max_cost must be non-negative")
        now = time.time()
        claims = {
            "jti": str(uuid.uuid4()),
            "sub": subject,
            "session_id": session_id,
            "allowed_actions": sorted({a.strip().lower() for a in allowed_actions}),
            "exact_hosts": sorted({h.strip().lower().rstrip(".") for h in exact_hosts}),
            "risk_ceiling": int(risk_ceiling),
            "max_calls": int(max_calls),
            "max_cost": float(max_cost),
            "currency": currency.upper(),
            "nbf": float(not_before if not_before is not None else now - 1),
            "exp": float(now + ttl_seconds),
            "nonce": secrets.token_urlsafe(18),
        }
        return self.codec.encode("permit", claims)

    def validate(
        self,
        token: str,
        *,
        request: ActionRequest,
        risk: RiskTier,
        expected_subject: str,
        now: float | None = None,
    ) -> PermitValidation:
        claims = self.codec.decode(token, expected_kind="permit")
        current = time.time() if now is None else now
        if current < float(claims.get("nbf", 0)):
            raise ControlPlaneError(FailureCode.BLOCKED_PERMIT_INVALID, "Permit is not active yet")
        if current >= float(claims.get("exp", 0)):
            raise ControlPlaneError(FailureCode.BLOCKED_PERMIT_EXPIRED, "Permit has expired")
        if claims.get("sub") != expected_subject or claims.get("session_id") != request.session_id:
            raise ControlPlaneError(
                FailureCode.BLOCKED_PERMIT_SCOPE_MISMATCH,
                "Permit subject or session does not match",
            )
        allowed_actions = {str(a).lower() for a in claims.get("allowed_actions", [])}
        if request.action_type not in allowed_actions:
            raise ControlPlaneError(
                FailureCode.BLOCKED_PERMIT_SCOPE_MISMATCH,
                "Action is outside permit scope",
                {"action_type": request.action_type},
            )
        host = (urlsplit(request.target_url).hostname or "").lower().rstrip(".")
        if host not in {str(h).lower().rstrip(".") for h in claims.get("exact_hosts", [])}:
            raise ControlPlaneError(
                FailureCode.BLOCKED_PERMIT_SCOPE_MISMATCH,
                "Host is outside permit scope",
                {"host": host},
            )
        if int(risk) > int(claims.get("risk_ceiling", -1)):
            raise ControlPlaneError(
                FailureCode.BLOCKED_PERMIT_SCOPE_MISMATCH,
                "Risk exceeds permit ceiling",
            )
        amount = float(request.estimated_cost or 0.0)
        permit_currency = str(claims.get("currency", "USD")).upper()
        if amount > 0 and (request.currency or "").upper() != permit_currency:
            raise ControlPlaneError(
                FailureCode.BLOCKED_PERMIT_SCOPE_MISMATCH,
                "Currency does not match permit",
            )
        return PermitValidation(str(claims["jti"]), str(claims["sub"]), claims, {})

    def validate_and_consume(
        self,
        token: str,
        *,
        request: ActionRequest,
        risk: RiskTier,
        expected_subject: str,
        now: float | None = None,
    ) -> PermitValidation:
        validation = self.validate(
            token,
            request=request,
            risk=risk,
            expected_subject=expected_subject,
            now=now,
        )
        amount = float(request.estimated_cost or 0.0)
        validation.usage = self.registry.consume_permit(
            permit_id=validation.permit_id,
            idempotency_key=request.idempotency_key,
            amount=amount,
            max_calls=int(validation.claims["max_calls"]),
            max_cost=float(validation.claims["max_cost"]),
        )
        return validation


class ApprovalAuthority:
    def __init__(self, secret: bytes, registry: PermitRegistry, *, issuer: str = "wbcp") -> None:
        self.codec = SignedTokenCodec(secret, issuer)
        self.registry = registry

    def issue(
        self,
        *,
        job_id: str,
        action_digest: str,
        approval_kind: ApprovalKind,
        approvers: list[str],
        ttl_seconds: int = 120,
    ) -> str:
        unique = sorted({a.strip() for a in approvers if a.strip()})
        if approval_kind == ApprovalKind.DUAL_CONTROL and len(unique) < 2:
            raise ValueError("Dual-control approval requires two distinct approvers")
        if approval_kind == ApprovalKind.HIGH_IMPACT and len(unique) < 1:
            raise ValueError("High-impact approval requires an approver")
        now = time.time()
        claims = {
            "jti": str(uuid.uuid4()),
            "job_id": job_id,
            "action_digest": action_digest,
            "approval_kind": approval_kind.value,
            "approvers": unique,
            "nbf": now - 1,
            "exp": now + ttl_seconds,
            "nonce": secrets.token_urlsafe(18),
        }
        return self.codec.encode("approval", claims)

    def validate(
        self,
        token: str,
        *,
        job_id: str,
        action_digest: str,
        required_kind: ApprovalKind,
        now: float | None = None,
    ) -> dict[str, Any]:
        try:
            claims = self.codec.decode(token, expected_kind="approval")
        except ControlPlaneError as exc:
            raise ControlPlaneError(FailureCode.BLOCKED_APPROVAL_INVALID, exc.message) from exc
        current = time.time() if now is None else now
        if current < float(claims.get("nbf", 0)):
            raise ControlPlaneError(FailureCode.BLOCKED_APPROVAL_INVALID, "Approval is not active yet")
        if current >= float(claims.get("exp", 0)):
            raise ControlPlaneError(FailureCode.BLOCKED_APPROVAL_EXPIRED, "Approval has expired")
        if claims.get("job_id") != job_id or claims.get("action_digest") != action_digest:
            raise ControlPlaneError(
                FailureCode.BLOCKED_APPROVAL_INVALID,
                "Approval is bound to a different job or action payload",
            )
        if claims.get("approval_kind") != required_kind.value:
            raise ControlPlaneError(
                FailureCode.BLOCKED_APPROVAL_INVALID,
                "Approval kind does not satisfy the action gate",
            )
        approvers = {str(a) for a in claims.get("approvers", [])}
        if required_kind == ApprovalKind.DUAL_CONTROL and len(approvers) < 2:
            raise ControlPlaneError(
                FailureCode.BLOCKED_APPROVAL_INVALID,
                "Dual-control approval has fewer than two distinct approvers",
            )
        return claims

    def validate_and_consume(
        self,
        token: str,
        *,
        job_id: str,
        action_digest: str,
        required_kind: ApprovalKind,
        now: float | None = None,
    ) -> dict[str, Any]:
        claims = self.validate(
            token,
            job_id=job_id,
            action_digest=action_digest,
            required_kind=required_kind,
            now=now,
        )
        self.registry.consume_approval(str(claims["jti"]), job_id)
        return claims
