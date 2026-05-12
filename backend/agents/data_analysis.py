"""Data Analysis Agent."""
from __future__ import annotations
import pandas as pd
from core.schemas import ColumnStat, DatasetMetadata
from core.llm import chat


def _load_dataframe(filepath: str) -> pd.DataFrame:
    if filepath.endswith((".xlsx", ".xls")):
        return pd.read_excel(filepath)
    return pd.read_csv(filepath, encoding_errors="replace")


def _compute_column_stats(df: pd.DataFrame) -> list[ColumnStat]:
    stats = []
    for col in df.columns:
        series = df[col]
        stat = ColumnStat(
            name=col, dtype=str(series.dtype),
            non_null_count=int(series.notna().sum()),
            null_count=int(series.isna().sum()),
            unique_count=int(series.nunique()),
            sample_values=series.dropna().head(5).tolist(),
        )
        if pd.api.types.is_numeric_dtype(series):
            stat.mean   = round(float(series.mean()), 4)
            stat.std    = round(float(series.std()),  4)
            stat.min    = round(float(series.min()),  4)
            stat.max    = round(float(series.max()),  4)
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
            anomalies.append(f"Column '{col}' has {len(outliers)} extreme outlier(s) (e.g. {outliers.iloc[0]:.2f}).")
    missing_pct = (df.isna().sum() / len(df) * 100).round(1)
    for col, pct in missing_pct.items():
        if pct > 20:
            anomalies.append(f"Column '{col}' is {pct}% missing.")
    return anomalies[:10]


async def run(filepath: str) -> DatasetMetadata:
    df = _load_dataframe(filepath)
    df_sample = df.head(5000)
    columns      = _compute_column_stats(df_sample)
    correlations = _compute_correlations(df_sample)
    anomalies    = _detect_anomalies(df_sample)

    col_names = [c.name for c in columns][:20]
    prompt = (
        f"Given these dataset column names: {col_names}, "
        "in one word, what business domain does this data likely come from? "
        "Examples: sales, finance, healthcare, marketing, logistics, hr, ecommerce. "
        "Reply with only the domain word, nothing else."
    )
    domain = chat(prompt).strip().lower().split()[0]

    return DatasetMetadata(
        row_count=len(df), column_count=len(df.columns),
        columns=columns, correlations=correlations,
        anomalies=anomalies, inferred_domain=domain,
    )
