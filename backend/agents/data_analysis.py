"""Data Analysis Agent — supports CSV and Excel only."""
from __future__ import annotations
import logging
import pandas as pd
from core.schemas import ColumnStat, DatasetMetadata
from core.llm import chat

logger = logging.getLogger(__name__)


def _load_dataframe(filepath: str) -> pd.DataFrame:
    """Load CSV or Excel file with robust encoding and delimiter detection."""
    fp = filepath.lower()

    if fp.endswith((".xlsx", ".xls", ".xlsm", ".xlsb")):
        try:
            df = pd.read_excel(filepath)
            logger.info(f"Loaded Excel: {df.shape}")
            return df
        except Exception as e:
            raise RuntimeError(f"Could not read Excel file: {e}")

    # CSV — try multiple encodings and delimiters
    encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252", "iso-8859-1"]
    delimiters = [",", ";", "\t", "|"]

    for enc in encodings:
        for delim in delimiters:
            try:
                df = pd.read_csv(
                    filepath,
                    encoding=enc,
                    sep=delim,
                    encoding_errors="replace",
                    low_memory=False,
                    on_bad_lines="skip",
                )
                # Validate — must have at least 2 columns or 1 row
                if df.shape[1] >= 1 and df.shape[0] >= 1:
                    logger.info(f"Loaded CSV (enc={enc}, sep='{delim}'): {df.shape}")
                    return df
            except Exception:
                continue

    # Last resort — read as raw text
    raise RuntimeError(
        "Could not parse CSV file. Please ensure it is a valid comma-separated or Excel file."
    )


def _compute_column_stats(df: pd.DataFrame) -> list[ColumnStat]:
    stats = []
    for col in df.columns:
        series = df[col]
        try:
            sample = series.dropna().head(5).tolist()
            sample = [str(v) if not isinstance(v, (int, float, str, bool)) else v for v in sample]
            stat = ColumnStat(
                name=str(col),
                dtype=str(series.dtype),
                non_null_count=int(series.notna().sum()),
                null_count=int(series.isna().sum()),
                unique_count=int(series.nunique()),
                sample_values=sample,
            )
            if pd.api.types.is_numeric_dtype(series) and series.notna().sum() > 0:
                stat.mean   = round(float(series.mean()), 4)
                stat.std    = round(float(series.std()),  4)
                stat.min    = round(float(series.min()),  4)
                stat.max    = round(float(series.max()),  4)
                stat.median = round(float(series.median()), 4)
            stats.append(stat)
        except Exception as e:
            logger.warning(f"Stats failed for '{col}': {e}")
    return stats


def _compute_correlations(df: pd.DataFrame) -> dict[str, dict[str, float]]:
    try:
        num_df = df.select_dtypes(include="number")
        if num_df.shape[1] < 2:
            return {}
        corr = num_df.corr().round(3)
        return {
            str(col): {str(k): float(v) for k, v in corr[col].items()}
            for col in corr.columns
        }
    except Exception as e:
        logger.warning(f"Correlation failed: {e}")
        return {}


def _detect_anomalies(df: pd.DataFrame) -> list[str]:
    anomalies = []
    try:
        for col in df.select_dtypes(include="number").columns:
            series = df[col].dropna()
            if len(series) < 4:
                continue
            q1, q3 = series.quantile(0.25), series.quantile(0.75)
            iqr = q3 - q1
            if iqr == 0:
                continue
            outliers = ((df[col] < q1 - 3 * iqr) | (df[col] > q3 + 3 * iqr)).sum()
            if outliers > 0:
                anomalies.append(f"Column '{col}' has {outliers} extreme outlier(s).")
        for col in df.columns:
            pct = df[col].isna().mean() * 100
            if pct > 20:
                anomalies.append(f"Column '{col}' is {pct:.0f}% missing.")
    except Exception as e:
        logger.warning(f"Anomaly detection failed: {e}")
    return anomalies[:10]


async def run(filepath: str) -> DatasetMetadata:
    df = _load_dataframe(filepath)

    # Clean column names
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(axis=1, how="all")  # drop fully empty columns
    df = df.loc[:, ~df.columns.duplicated()]  # drop duplicate column names

    df_sample = df.head(5000)

    columns      = _compute_column_stats(df_sample)
    correlations = _compute_correlations(df_sample)
    anomalies    = _detect_anomalies(df_sample)

    domain = "general"
    try:
        col_names = [c.name for c in columns][:20]
        prompt = (
            f"Given these dataset column names: {col_names}, "
            "in one word, what business domain is this? "
            "Examples: sales, finance, healthcare, marketing, logistics, hr, ecommerce. "
            "Reply with only the single domain word, nothing else."
        )
        result = chat(prompt).strip().lower().split()[0]
        known = {
            "sales","finance","healthcare","marketing","logistics",
            "hr","ecommerce","retail","education","operations","general"
        }
        domain = result if result in known else "general"
    except Exception as e:
        logger.warning(f"Domain inference failed: {e}")

    logger.info(f"Analysis done: {len(df)} rows, {len(df.columns)} cols, domain={domain}")
    return DatasetMetadata(
        row_count=len(df),
        column_count=len(df.columns),
        columns=columns,
        correlations=correlations,
        anomalies=anomalies,
        inferred_domain=domain,
    )
