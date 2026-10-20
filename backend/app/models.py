"""Pydantic v2 request/response schemas."""

from typing import Literal

from pydantic import BaseModel, Field

Stage = Literal[1, 2, 3, 4]
Trap = Literal["most_rows", "newest_dates"]
Tone = Literal["red", "amber", "green"]
SourceKind = Literal["prompt", "table", "report"]
CaptureStatus = Literal["captured", "stale", "missing"]


class StageInfo(BaseModel):
    stage: Stage
    title: str
    subtitle: str


class QuestionResponse(BaseModel):
    question: str
    english: str
    stages: list[StageInfo]


class RunRequest(BaseModel):
    stage: Stage
    trap: Trap | None = Field(default=None, description="Stage 4 only: which naive heuristic picks the wrong table")


class Badge(BaseModel):
    label: str
    tone: Tone


class EvidenceItem(BaseModel):
    label: str
    value: str


class ContextSource(BaseModel):
    name: str
    kind: SourceKind
    detail: str
    est_tokens: int
    used: bool


class ContextInfo(BaseModel):
    sources: list[ContextSource]
    total_est_tokens: int


class RunResponse(BaseModel):
    stage: Stage
    title: str
    prompt: str
    answer_text: str
    answer_source: Literal["captured", "engine"]
    capture_status: CaptureStatus
    captured_with: str | None
    badge: Badge
    takeaway: str
    evidence: list[EvidenceItem]
    context: ContextInfo
    steps: list[str]
    wrong_table: str | None
    headline_change_pct: float | None = Field(
        default=None, description="Computed % change the answer is based on (negative = drop). None when no data."
    )


class TableInfo(BaseModel):
    name: str
    rows: int
    role: Literal["source", "decoy", "other"]


class TablesResponse(BaseModel):
    tables: list[TableInfo]


class DailyPoint(BaseModel):
    date: str
    units: int


class Promo(BaseModel):
    promo_name: str
    start_date: str
    end_date: str
    discount_pct: float


class DatasetResponse(BaseModel):
    category: str
    series: list[DailyPoint]
    promos: list[Promo]
    pivot_date: str
    window_days: int
