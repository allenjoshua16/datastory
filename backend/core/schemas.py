"""Shared Pydantic schemas."""
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field


class ColumnStat(BaseModel):
    name: str
    dtype: str
    non_null_count: int
    null_count: int
    unique_count: int
    sample_values: list[Any] = Field(default_factory=list)
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
    inferred_domain: str = "general"


ChartType = Literal["bar","line","scatter","pie","histogram","heatmap","box","area","funnel","treemap"]


class ChartSpec(BaseModel):
    chart_id: str
    chart_type: ChartType
    title: str
    x_column: str | None = None
    y_column: str | None = None
    color_column: str | None = None
    rationale: str
    available_columns: list[str] = Field(default_factory=list)
    plotly_code: str = ""
    rendered_html: str = ""


AudienceMode = Literal["executive", "analyst", "investor", "general"]


class StoryIdea(BaseModel):
    title: str
    hook: str
    context: str
    dispute: str
    solution: str
    relevant_chart_ids: list[str] = Field(default_factory=list)


class RankedStory(StoryIdea):
    score: float = 0.0
    audience_mode: AudienceMode = "general"
    narrative_text: str = ""


class PreprocessingReport(BaseModel):
    row_count_before: int = 0
    row_count_after: int = 0
    column_count_before: int = 0
    column_count_after: int = 0
    rows_removed: int = 0
    columns_removed: int = 0
    transformations: list[str] = Field(default_factory=list)
    column_stats_after: list[dict] = Field(default_factory=list)
    inferred_types: dict[str, str] = Field(default_factory=dict)


PipelineStatus = Literal[
    "queued","preprocessing","ingesting","analyzing","visualizing",
    "executing","generating","reporting","done","error"
]


class PipelineJob(BaseModel):
    job_id: str
    filename: str
    status: PipelineStatus = "queued"
    progress: int = 0
    status_message: str = ""
    preprocess: bool = False
    clean_filepath: str | None = None
    preprocessing_report: PreprocessingReport | None = None
    metadata: DatasetMetadata | None = None
    chart_specs: list[ChartSpec] = Field(default_factory=list)
    stories: list[RankedStory] = Field(default_factory=list)
    report_html: str = ""
    error: str | None = None


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
    preprocessing_report: PreprocessingReport | None = None
