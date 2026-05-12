"""Data Analysis Agent — supports CSV, Excel, JSON, TSV, Parquet, DOCX."""
from __future__ import annotations
import json
import logging
import pandas as pd
from core.schemas import ColumnStat, DatasetMetadata
from core.llm import chat

logger = logging.getLogger(__name__)


def _load_dataframe(filepath: str) -> pd.DataFrame:
    fp = filepath.lower()
    if fp.endswith((".xlsx", ".xls", ".xlsm", ".xlsb")):
        return pd.read_excel(filepath)
    elif fp.endswith(".json"):
        return pd.read_json(filepath)
    elif fp.endswith(".tsv"):
        return pd.read_csv(filepath, sep="\t", encoding_errors="replace")
    elif fp.endswith(".parquet"):
        return pd.read_parquet(filepath)
    elif fp.endswith(".docx"):
        return _read_docx(filepath)
    else:
        # CSV, TXT, and anything else
        return pd.read_csv(filepath, encoding_errors="replace")


def _read_docx(filepath: str) -> pd.DataFrame:
    """Extract text from a Word doc as a single-column DataFrame."""
    try:
        from docx import Document
        doc = Document(filepath)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        # Try to extract tables if present
        tables = []
        for table in doc.tables:
            headers = [cell.text.strip() for cell in table.rows[0].cells]
            rows = []
            for row in table.rows[1:]:
                rows.append([cell.text.strip() for cell in row.cells])
            if rows:
                tables.append(pd.DataFrame(rows, columns=headers))
        if tables:
            return pd.concat(tables, ignore_index=True)
        return pd.DataFrame({"text": paragraphs})
    except ImportError:
        raise RuntimeError("python-docx not installed. Cannot read .docx files.")


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
    df.columns = df.columns.str.strip()  # clean column name whitespace
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
    logger.info(f"Detected domain: {domain}, columns: {col_names}")

    return DatasetMetadata(
        row_count=len(df), column_count=len(df.columns),
        columns=columns, correlations=correlations,
        anomalies=anomalies, inferred_domain=domain,
    )
