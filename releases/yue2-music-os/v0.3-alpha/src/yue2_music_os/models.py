from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


_PROVIDER_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")


class JobKind(StrEnum):
    GENERATE = "generate"
    TRANSCRIBE = "transcribe"
    COMPARE = "compare"
    STRIP_CHORDS = "strip-chords"
    RANK_CANDIDATES = "rank-candidates"
    PRODUCTION_RENDER = "production-render"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("project name is empty")
        return normalized


class GenerateRequest(BaseModel):
    project_id: str
    style: str = Field(min_length=1, max_length=6000)
    lyrics: str = Field(min_length=1, max_length=50000)
    cot: Literal["full", "melody", "off"] = "full"
    seed: int = Field(default=42, ge=0, le=2**31 - 1)
    abc_artifact_id: str | None = None
    candidate_count: int = Field(default=1, ge=1, le=8)

    @model_validator(mode="after")
    def score_requires_planning(self) -> "GenerateRequest":
        if self.abc_artifact_id and self.cot == "off":
            raise ValueError("abc_artifact_id requires cot=full or cot=melody")
        return self


class TranscribeRequest(BaseModel):
    project_id: str
    source_artifact_id: str
    melody_only: bool = True


class CompareRequest(BaseModel):
    project_id: str
    before_artifact_id: str
    after_artifact_id: str
    voices: Literal["both", "Vocal", "Ins"] = "both"
    allow_tempo_change: bool = False


class StripChordsRequest(BaseModel):
    project_id: str
    source_artifact_id: str
    keep_voice: Literal["both", "Vocal", "Ins"] = "both"


class RankCandidatesRequest(BaseModel):
    project_id: str
    generation_job_id: str


class ProductionRenderRequest(BaseModel):
    project_id: str
    generation_job_id: str
    candidate: int | Literal["best-technical"] = "best-technical"
    provider_ids: list[str] = Field(min_length=1, max_length=8)
    title: str = Field(default="Untitled production render", min_length=1, max_length=160)
    notes: str = Field(default="", max_length=4000)
    commercial_intent: bool = True
    license_review_acknowledged: bool = False

    @field_validator("candidate")
    @classmethod
    def validate_candidate(cls, value: int | str) -> int | str:
        if isinstance(value, int) and not 1 <= value <= 8:
            raise ValueError("candidate must be between 1 and 8")
        return value

    @field_validator("provider_ids")
    @classmethod
    def validate_providers(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for provider_id in value:
            provider_id = provider_id.strip().lower()
            if not _PROVIDER_ID.fullmatch(provider_id):
                raise ValueError(f"invalid provider id: {provider_id!r}")
            if provider_id not in normalized:
                normalized.append(provider_id)
        if not normalized:
            raise ValueError("at least one render provider is required")
        return normalized

    @model_validator(mode="after")
    def commercial_use_requires_review(self) -> "ProductionRenderRequest":
        if self.commercial_intent and not self.license_review_acknowledged:
            raise ValueError(
                "commercial_intent requires license_review_acknowledged=true"
            )
        return self


class ProjectRecord(BaseModel):
    id: str
    name: str
    created_at: datetime


class ArtifactRecord(BaseModel):
    id: str
    project_id: str
    job_id: str | None = None
    kind: str
    name: str
    media_type: str
    size_bytes: int
    sha256: str
    created_at: datetime
    download_url: str | None = None


class JobRecord(BaseModel):
    id: str
    project_id: str
    kind: JobKind
    status: JobStatus
    request: dict[str, Any]
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
