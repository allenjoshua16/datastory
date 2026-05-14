"""Preprocessing Agent — mimics what a data analyst does with raw data."""
from __future__ import annotations
import logging
import os
import re
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PreprocessingReport:
    row_count_before: int = 0
    row_count_after: int = 0
    column_count_before: int = 0
    column_count_after: int = 0
    transformations: list[str] = field(default_factory=list)
    column_stats_after: list[dict] = field(default_factory=list)
    inferred_types: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "row_count_before": self.row_count_before,
            "row_count_after": self.row_count_after,
            "column_count_before": self.column_count_before,
            "column_count_after": self.column_count_after,
            "rows_removed": self.row_count_before - self.row_count_after,
            "columns_removed": self.column_count_before - self.column_count_after,
            "transformations": self.transformations,
            "column_stats_after": self.column_stats_after,
            "inferred_types": self.inferred_types,
        }


def _load_df(filepath: str) -> pd.DataFrame:
    fp = filepath.lower()
    if fp.endswith((".xlsx", ".xls", ".xlsm")):
        return pd.read_excel(filepath)
    elif fp.endswith(".json"):
        try:
            return pd.read_json(filepath)
        except Exception:
            import json
            with open(filepath) as f:
                data = json.load(f)
            return pd.DataFrame(data if isinstance(data, list) else [data])
    elif fp.endswith(".tsv"):
        return pd.read_csv(filepath, sep="\t", encoding_errors="replace")
    elif fp.endswith(".parquet"):
        return pd.read_parquet(filepath)
    else:
        for enc in ["utf-8", "latin-1", "cp1252"]:
            try:
                return pd.read_csv(filepath, encoding=enc, encoding_errors="replace")
            except Exception:
                continue
    return pd.read_csv(filepath, encoding_errors="replace")


def _clean_column_names(df: pd.DataFrame, report: PreprocessingReport) -> pd.DataFrame:
    """Trim whitespace, replace spaces/special chars with underscores, ensure unique."""
    original = df.columns.tolist()
    new_cols = []
    seen = {}
    for col in original:
        c = str(col).strip()
        c = re.sub(r"[^\w]", "_", c)
        c = re.sub(r"_+", "_", c).strip("_")
        if not c:
            c = "column"
        if c in seen:
            seen[c] += 1
            c = f"{c}_{seen[c]}"
        else:
            seen[c] = 0
        new_cols.append(c)
    df.columns = new_cols
    changed = [(o, n) for o, n in zip(original, new_cols) if str(o).strip() != n]
    if changed:
        report.transformations.append(
            f"Cleaned {len(changed)} column name(s): {changed[:5]}"
        )
    return df


def _infer_and_convert_types(df: pd.DataFrame, report: PreprocessingReport) -> pd.DataFrame:
    """Detect and convert columns to appropriate types."""
    for col in df.columns:
        series = df[col]
        original_dtype = str(series.dtype)

        # Skip already numeric
        if pd.api.types.is_numeric_dtype(series):
            report.inferred_types[col] = original_dtype
            continue

        # Try datetime
        if any(x in col.lower() for x in ["date", "time", "created", "updated", "timestamp"]):
            try:
                converted = pd.to_datetime(series, errors="coerce")
                if converted.notna().sum() > len(series) * 0.5:
                    df[col] = converted
                    report.inferred_types[col] = "datetime"
                    report.transformations.append(f"Converted '{col}' to datetime")
                    continue
            except Exception:
                pass

        # Try numeric
        try:
            numeric = pd.to_numeric(series.str.replace(r"[,$%]", "", regex=True), errors="coerce")
            if numeric.notna().sum() > len(series) * 0.7:
                df[col] = numeric
                report.inferred_types[col] = "numeric"
                report.transformations.append(f"Converted '{col}' to numeric")
                continue
        except Exception:
            pass

        report.inferred_types[col] = "categorical" if series.nunique() < 50 else "text"

    return df


def _remove_duplicates(df: pd.DataFrame, report: PreprocessingReport) -> pd.DataFrame:
    before = len(df)
    df = df.drop_duplicates()
    removed = before - len(df)
    if removed > 0:
        report.transformations.append(f"Removed {removed} duplicate row(s)")
    return df


def _drop_empty_columns(df: pd.DataFrame, report: PreprocessingReport, threshold: float = 0.9) -> pd.DataFrame:
    """Drop columns where more than threshold fraction is missing."""
    missing_frac = df.isna().mean()
    to_drop = missing_frac[missing_frac > threshold].index.tolist()
    if to_drop:
        df = df.drop(columns=to_drop)
        report.transformations.append(
            f"Dropped {len(to_drop)} column(s) with >{threshold*100:.0f}% missing: {to_drop[:5]}"
        )
    return df


def _handle_missing_values(df: pd.DataFrame, report: PreprocessingReport) -> pd.DataFrame:
    """Impute missing values: median for numeric, mode for categorical."""
    for col in df.columns:
        null_count = df[col].isna().sum()
        if null_count == 0:
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            median = df[col].median()
            df[col] = df[col].fillna(median)
            report.transformations.append(
                f"Imputed {null_count} missing value(s) in '{col}' with median ({median:.2f})"
            )
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            pass  # Leave datetime NaT as-is
        else:
            mode_vals = df[col].mode()
            if not mode_vals.empty:
                df[col] = df[col].fillna(mode_vals[0])
                report.transformations.append(
                    f"Imputed {null_count} missing value(s) in '{col}' with mode ('{mode_vals[0]}')"
                )
    return df


def _handle_outliers(df: pd.DataFrame, report: PreprocessingReport) -> pd.DataFrame:
    """Cap outliers at IQR boundaries (Winsorization)."""
    for col in df.select_dtypes(include="number").columns:
        series = df[col].dropna()
        if len(series) < 10:
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower, upper = q1 - 3 * iqr, q3 + 3 * iqr
        outliers = ((df[col] < lower) | (df[col] > upper)).sum()
        if outliers > 0:
            df[col] = df[col].clip(lower=lower, upper=upper)
            report.transformations.append(
                f"Capped {outliers} outlier(s) in '{col}' to [{lower:.2f}, {upper:.2f}]"
            )
    return df


def _extract_date_features(df: pd.DataFrame, report: PreprocessingReport) -> pd.DataFrame:
    """Extract year, month, day from datetime columns."""
    for col in df.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]).columns:
        try:
            df[f"{col}_year"]  = df[col].dt.year
            df[f"{col}_month"] = df[col].dt.month
            df[f"{col}_day"]   = df[col].dt.day
            report.transformations.append(
                f"Extracted year/month/day from datetime column '{col}'"
            )
        except Exception as e:
            logger.warning(f"Date feature extraction failed for '{col}': {e}")
    return df


def _compute_column_stats(df: pd.DataFrame) -> list[dict]:
    stats = []
    for col in df.columns:
        s = df[col]
        stat: dict = {
            "name": col,
            "dtype": str(s.dtype),
            "non_null": int(s.notna().sum()),
            "null_count": int(s.isna().sum()),
            "unique": int(s.nunique()),
        }
        if pd.api.types.is_numeric_dtype(s) and s.notna().sum() > 0:
            stat.update({
                "mean":   round(float(s.mean()), 4),
                "median": round(float(s.median()), 4),
                "std":    round(float(s.std()), 4),
                "min":    round(float(s.min()), 4),
                "max":    round(float(s.max()), 4),
            })
        stats.append(stat)
    return stats


async def run(filepath: str, output_dir: str = "./uploads") -> tuple[str, PreprocessingReport]:
    """
    Run the full preprocessing pipeline.
    Returns (clean_filepath, PreprocessingReport).
    """
    report = PreprocessingReport()
    os.makedirs(output_dir, exist_ok=True)

    df = _load_df(filepath)
    report.row_count_before    = len(df)
    report.column_count_before = len(df.columns)

    # Pipeline
    df = _clean_column_names(df, report)
    df = _infer_and_convert_types(df, report)
    df = _remove_duplicates(df, report)
    df = _drop_empty_columns(df, report)
    df = _handle_missing_values(df, report)
    df = _handle_outliers(df, report)
    df = _extract_date_features(df, report)

    report.row_count_after    = len(df)
    report.column_count_after = len(df.columns)
    report.column_stats_after = _compute_column_stats(df)

    if not report.transformations:
        report.transformations.append("Dataset was already clean — no transformations required.")

    # Save cleaned file
    base = os.path.splitext(os.path.basename(filepath))[0]
    clean_path = os.path.join(output_dir, f"{base}_cleaned.csv")
    df.to_csv(clean_path, index=False)
    logger.info(f"Preprocessing complete: {report.row_count_before}→{report.row_count_after} rows, "
                f"{report.column_count_before}→{report.column_count_after} cols, "
                f"{len(report.transformations)} transformations")
    return clean_path, report
