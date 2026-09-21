from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Iterable

from .errors import ControlPlaneError, FailureCode
from .models import ActionRequest, JobState, PolicyDecision, RiskTier


LEGAL_TRANSITIONS: dict[JobState, set[JobState]] = {
    JobState.CREATED: {JobState.PREFLIGHTED, JobState.BLOCKED, JobState.CANCELLED},
    JobState.PREFLIGHTED: {JobState.AWAITING_APPROVAL, JobState.AUTHORIZED, JobState.BLOCKED, JobState.CANCELLED},
    JobState.AWAITING_APPROVAL: {JobState.AUTHORIZED, JobState.BLOCKED, JobState.CANCELLED},
    JobState.AUTHORIZED: {JobState.RUNNING, JobState.BLOCKED, JobState.CANCELLED},
    JobState.RUNNING: {JobState.VERIFYING, JobState.FAILED, JobState.CANCELLED},
    JobState.VERIFYING: {
        JobState.SUCCEEDED,
        JobState.FAILED,
        JobState.ROLLED_BACK,
        JobState.QUARANTINED,
    },
    JobState.FAILED: {JobState.ROLLED_BACK, JobState.QUARANTINED},
    JobState.SUCCEEDED: set(),
    JobState.ROLLED_BACK: set(),
    JobState.CANCELLED: set(),
    JobState.BLOCKED: set(),
    JobState.QUARANTINED: set(),
}


@dataclass(slots=True)
class JobRecord:
    job_id: str
    idempotency_key: str
    fingerprint: str
    state: JobState
    revision: int
    risk: RiskTier
    request: ActionRequest
    decision: PolicyDecision
    result: dict[str, Any] | None
    error_code: str | None
    created_at: float
    updated_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "idempotency_key": self.idempotency_key,
            "fingerprint": self.fingerprint,
            "state": self.state.value,
            "revision": self.revision,
            "risk": int(self.risk),
            "request": self.request.to_dict(),
            "decision": self.decision.to_dict(),
            "result": self.result,
            "error_code": self.error_code,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class JobStore:
    def __init__(self, db_path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._conn:
            self._conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                PRAGMA foreign_keys=ON;
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    idempotency_key TEXT UNIQUE NOT NULL,
                    fingerprint TEXT NOT NULL,
                    state TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    risk INTEGER NOT NULL,
                    request_json TEXT NOT NULL,
                    decision_json TEXT NOT NULL,
                    result_json TEXT,
                    error_code TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                """
            )

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> JobRecord:
        return JobRecord(
            job_id=str(row["job_id"]),
            idempotency_key=str(row["idempotency_key"]),
            fingerprint=str(row["fingerprint"]),
            state=JobState(row["state"]),
            revision=int(row["revision"]),
            risk=RiskTier(int(row["risk"])),
            request=ActionRequest.from_dict(json.loads(row["request_json"])),
            decision=PolicyDecision.from_dict(json.loads(row["decision_json"])),
            result=json.loads(row["result_json"]) if row["result_json"] else None,
            error_code=row["error_code"],
            created_at=float(row["created_at"]),
            updated_at=float(row["updated_at"]),
        )

    def create_or_get(self, request: ActionRequest, decision: PolicyDecision) -> tuple[JobRecord, bool]:
        fingerprint = request.fingerprint()
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                row = self._conn.execute(
                    "SELECT * FROM jobs WHERE idempotency_key=?", (request.idempotency_key,)
                ).fetchone()
                if row is not None:
                    record = self._row_to_record(row)
                    if record.fingerprint != fingerprint:
                        raise ControlPlaneError(
                            FailureCode.BLOCKED_IDEMPOTENCY_CONFLICT,
                            "The idempotency key was reused with a different action payload",
                            {"job_id": record.job_id},
                        )
                    self._conn.execute("COMMIT")
                    return record, False
                now = time.time()
                job_id = str(uuid.uuid4())
                self._conn.execute(
                    """
                    INSERT INTO jobs(
                        job_id,idempotency_key,fingerprint,state,revision,risk,
                        request_json,decision_json,result_json,error_code,created_at,updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        job_id,
                        request.idempotency_key,
                        fingerprint,
                        JobState.CREATED.value,
                        0,
                        int(decision.risk),
                        json.dumps(request.to_dict(), sort_keys=True, ensure_ascii=False),
                        json.dumps(decision.to_dict(), sort_keys=True, ensure_ascii=False),
                        None,
                        None,
                        now,
                        now,
                    ),
                )
                row = self._conn.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
                self._conn.execute("COMMIT")
                assert row is not None
                return self._row_to_record(row), True
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def get(self, job_id: str) -> JobRecord:
        row = self._conn.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(job_id)
        return self._row_to_record(row)

    def transition(
        self,
        job_id: str,
        *,
        expected_states: Iterable[JobState],
        new_state: JobState,
        expected_revision: int | None = None,
        result: dict[str, Any] | None = None,
        error_code: str | None = None,
    ) -> JobRecord:
        expected = set(expected_states)
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                row = self._conn.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
                if row is None:
                    raise KeyError(job_id)
                current = self._row_to_record(row)
                if current.state not in expected:
                    raise ControlPlaneError(
                        FailureCode.BLOCKED_ILLEGAL_STATE_TRANSITION,
                        "Current state is not accepted by this operation",
                        {
                            "current": current.state.value,
                            "expected": sorted(s.value for s in expected),
                            "requested": new_state.value,
                        },
                    )
                if new_state not in LEGAL_TRANSITIONS[current.state]:
                    raise ControlPlaneError(
                        FailureCode.BLOCKED_ILLEGAL_STATE_TRANSITION,
                        "Requested state transition is not legal",
                        {"current": current.state.value, "requested": new_state.value},
                    )
                if expected_revision is not None and current.revision != expected_revision:
                    raise ControlPlaneError(
                        FailureCode.BLOCKED_CONCURRENT_REVISION_CONFLICT,
                        "Job revision changed concurrently",
                        {"expected": expected_revision, "actual": current.revision},
                    )
                now = time.time()
                next_revision = current.revision + 1
                cursor = self._conn.execute(
                    """
                    UPDATE jobs
                    SET state=?, revision=?, result_json=COALESCE(?,result_json),
                        error_code=COALESCE(?,error_code), updated_at=?
                    WHERE job_id=? AND revision=?
                    """,
                    (
                        new_state.value,
                        next_revision,
                        json.dumps(result, sort_keys=True, ensure_ascii=False) if result is not None else None,
                        error_code,
                        now,
                        job_id,
                        current.revision,
                    ),
                )
                if cursor.rowcount != 1:
                    raise ControlPlaneError(
                        FailureCode.BLOCKED_CONCURRENT_REVISION_CONFLICT,
                        "Compare-and-swap update failed",
                    )
                updated_row = self._conn.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
                self._conn.execute("COMMIT")
                assert updated_row is not None
                return self._row_to_record(updated_row)
            except Exception:
                self._conn.execute("ROLLBACK")
                raise
