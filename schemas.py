"""Shared Pydantic schemas used across all agents and API routes."""
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Dataset metadata (output of Data Analysis Agent)
# ---------------------------------------------------------------------------

class ColumnStat(BaseModel):
    name: str
    dtype: str
    non_null_count: int
    null_count: int
    unique_count: int
    sample_values: list[Any] = Field(default_factory=list)
    # numeric only
    mean: float | None = None
    std: float | None = None
    min: float | None = None
    max: float | None = None
    median: float | None = None


class DatasetMetadata(BaseModel):
    row_count: int
    column_count: int
    columns: list[ColumnStat]
    correlations: dict[str, dict[str, float]] = Field(default_factory=dict)
    anomalies: list[str] = Field(default_factory=list)
    inferred_domain: str = "general"  # e.g. "sales", "finance", "healthcare"


# ---------------------------------------------------------------------------
# Visualization spec (output of Visualization Generation Agent)
# ---------------------------------------------------------------------------

ChartType = Literal[
    "bar", "line", "scatter", "pie", "histogram",
    "heatmap", "box", "area", "funnel", "treemap"
]


class ChartSpec(BaseModel):
    chart_id: str
    chart_type: ChartType
    title: str
    x_column: str | None = None
    y_column: str | None = None
    color_column: str | None = None
    rationale: str
    plotly_code: str = ""   # filled by Code Generation Agent
    rendered_html: str = "" # filled by Code Execution Agent


# ---------------------------------------------------------------------------
# Story (output of Story Generation / Execution Agents)
# ---------------------------------------------------------------------------

AudienceMode = Literal["executive", "analyst", "investor", "general"]


class StoryIdea(BaseModel):
    title: str
    hook: str          # one-sentence grabber
    context: str
    dispute: str       # the surprising / unexpected finding
    solution: str      # actionable recommendation
    relevant_chart_ids: list[str] = Field(default_factory=list)


class RankedStory(StoryIdea):
    score: float = 0.0
    audience_mode: AudienceMode = "general"
    narrative_text: str = ""


# ---------------------------------------------------------------------------
# Pipeline job — tracks state across agents
# ---------------------------------------------------------------------------

PipelineStatus = Literal[
    "queued", "ingesting", "analyzing", "visualizing",
    "generating", "executing", "reporting", "done", "error"
]


class PipelineJob(BaseModel):
    job_id: str
    filename: str
    status: PipelineStatus = "queued"
    progress: int = 0          # 0-100
    status_message: str = ""
    metadata: DatasetMetadata | None = None
    chart_specs: list[ChartSpec] = Field(default_factory=list)
    stories: list[RankedStory] = Field(default_factory=list)
    report_html: str = ""
    error: str | None = None


# ---------------------------------------------------------------------------
# API request / response wrappers
# ---------------------------------------------------------------------------

class UploadResponse(BaseModel):
    job_id: str
    filename: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: PipelineStatus
    progress: int
    status_message: str
    error: str | None = None


class JobResultResponse(BaseModel):
    job_id: str
    metadata: DatasetMetadata | None
    chart_specs: list[ChartSpec]
    stories: list[RankedStory]
    report_html: str
