"""Data Analysis Agent.

Reads a CSV/Excel file, computes column statistics, correlation matrix,
detects anomalies, and returns a DatasetMetadata object.
"""
from __future__ import annotations
import json
import numpy as np
import pandas as pd
from openai import AsyncOpenAI
from core.schemas import ColumnStat, DatasetMetadata
from core.config import get_settings


def _load_dataframe(filepath: str) -> pd.DataFrame:
    if filepath.endswith((".xlsx", ".xls")):
        return pd.read_excel(filepath)
    return pd.read_csv(filepath, encoding_errors="replace")


def _compute_column_stats(df: pd.DataFrame) -> list[ColumnStat]:
    stats = []
    for col in df.columns:
        series = df[col]
        stat = ColumnStat(
            name=col,
            dtype=str(series.dtype),
            non_null_count=int(series.notna().sum()),
            null_count=int(series.isna().sum()),
            unique_count=int(series.nunique()),
            sample_values=series.dropna().head(5).tolist(),
        )
        if pd.api.types.is_numeric_dtype(series):
            stat.mean = round(float(series.mean()), 4)
            stat.std = round(float(series.std()), 4)
            stat.min = round(float(series.min()), 4)
            stat.max = round(float(series.max()), 4)
            stat.median = round(float(series.median()), 4)
        stats.append(stat)
    return stats


def _compute_correlations(df: pd.DataFrame) -> dict[str, dict[str, float]]:
    num_df = df.select_dtypes(include="number")
    if num_df.shape[1] < 2:
        return {}
    corr = num_df.corr().round(3)
    return {col: corr[col].to_dict() for col in corr.columns}


def _detect_anomalies(df: pd.DataFrame) -> list[str]:
    anomalies = []
    for col in df.select_dtypes(include="number").columns:
        series = df[col].dropna()
        if len(series) < 4:
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        outliers = series[(series < q1 - 3 * iqr) | (series > q3 + 3 * iqr)]
        if not outliers.empty:
            anomalies.append(
                f"Column '{col}' has {len(outliers)} extreme outlier(s) "
                f"(e.g. {outliers.iloc[0]:.2f})."
            )
    missing_pct = (df.isna().sum() / len(df) * 100).round(1)
    for col, pct in missing_pct.items():
        if pct > 20:
            anomalies.append(f"Column '{col}' is {pct}% missing.")
    return anomalies[:10]  # cap to keep prompt manageable


async def _infer_domain(columns: list[str], client: AsyncOpenAI, model: str) -> str:
    """Ask the LLM to guess the business domain from column names."""
    prompt = (
        f"Given these dataset column names: {columns[:20]}, "
        "in one word, what business domain does this data likely come from? "
        "Examples: sales, finance, healthcare, marketing, logistics, hr, ecommerce. "
        "Reply with only the domain word."
    )
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=10,
        temperature=0,
    )
    return response.choices[0].message.content.strip().lower()


async def run(filepath: str) -> DatasetMetadata:
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    df = _load_dataframe(filepath)
    # Limit rows for analysis to keep it fast
    df_sample = df.head(5000)

    columns = _compute_column_stats(df_sample)
    correlations = _compute_correlations(df_sample)
    anomalies = _detect_anomalies(df_sample)
    domain = await _infer_domain([c.name for c in columns], client, settings.openai_model)

    return DatasetMetadata(
        row_count=len(df),
        column_count=len(df.columns),
        columns=columns,
        correlations=correlations,
        anomalies=anomalies,
        inferred_domain=domain,
    )
