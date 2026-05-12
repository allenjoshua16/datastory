"""
Deterministic Chart Engine.
Generates Plotly charts directly from ChartSpec — no LLM involved.
Falls back to LLM code generation only if the deterministic approach fails.
"""
from __future__ import annotations
import logging
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from core.schemas import ChartSpec

logger = logging.getLogger(__name__)


def _load_df(filepath: str) -> pd.DataFrame:
    fp = filepath.lower()
    if fp.endswith((".xlsx", ".xls", ".xlsm")):
        df = pd.read_excel(filepath)
    elif fp.endswith(".json"):
        df = pd.read_json(filepath)
    elif fp.endswith(".tsv"):
        df = pd.read_csv(filepath, sep="\t", encoding_errors="replace")
    elif fp.endswith(".parquet"):
        df = pd.read_parquet(filepath)
    else:
        df = pd.read_csv(filepath, encoding_errors="replace")
    df.columns = df.columns.str.strip()
    return df


def _safe_col(df: pd.DataFrame, col: str | None) -> str | None:
    """Return col if it exists in df, else None."""
    if col and col in df.columns:
        return col
    return None


def render_chart(spec: ChartSpec, filepath: str, output_path: str) -> bool:
    """
    Render a chart deterministically. Returns True on success.
    """
    try:
        df = _load_df(filepath)
        x = _safe_col(df, spec.x_column)
        y = _safe_col(df, spec.y_column)
        color = _safe_col(df, spec.color_column)
        ctype = spec.chart_type
        title = spec.title

        fig = None

        # --- BAR ---
        if ctype == "bar":
            if x and y:
                plot_df = df[[x, y] + ([color] if color else [])].dropna()
                if not pd.api.types.is_numeric_dtype(plot_df[y]):
                    plot_df[y] = plot_df[y].astype(str)
                fig = px.bar(plot_df, x=x, y=y, color=color, title=title)
            elif x:
                counts = df[x].value_counts().reset_index()
                counts.columns = [x, "Count"]
                fig = px.bar(counts, x=x, y="Count", title=title)
            elif y:
                counts = df[y].value_counts().reset_index()
                counts.columns = [y, "Count"]
                fig = px.bar(counts, x=y, y="Count", title=title)

        # --- LINE ---
        elif ctype == "line":
            if x:
                # Try parsing as date
                try:
                    df["_date"] = pd.to_datetime(df[x], errors="coerce")
                    if df["_date"].notna().sum() > len(df) * 0.5:
                        df["_month"] = df["_date"].dt.to_period("M").astype(str)
                        if y and pd.api.types.is_numeric_dtype(df[y]):
                            monthly = df.groupby("_month")[y].sum().reset_index()
                            monthly.columns = [x, y]
                        else:
                            monthly = df.groupby("_month").size().reset_index(name="Count")
                            monthly.columns = [x, "Count"]
                            y = "Count"
                        fig = px.line(monthly, x=x, y=y, title=title)
                except Exception:
                    pass
                if fig is None and y:
                    plot_df = df[[x, y]].dropna()
                    fig = px.line(plot_df, x=x, y=y, title=title)

        # --- PIE ---
        elif ctype == "pie":
            col = x or y
            if col:
                counts = df[col].value_counts().reset_index()
                counts.columns = [col, "Count"]
                fig = px.pie(counts, names=col, values="Count", title=title)

        # --- HISTOGRAM ---
        elif ctype == "histogram":
            col = y or x
            if col and pd.api.types.is_numeric_dtype(df[col]):
                fig = px.histogram(df.dropna(subset=[col]), x=col, color=color, title=title)

        # --- BOX ---
        elif ctype == "box":
            if y and pd.api.types.is_numeric_dtype(df[y]):
                fig = px.box(df.dropna(subset=[y]), x=x, y=y, color=color, title=title)
            elif x and pd.api.types.is_numeric_dtype(df[x]):
                fig = px.box(df.dropna(subset=[x]), y=x, title=title)

        # --- SCATTER ---
        elif ctype == "scatter":
            if x and y:
                plot_df = df[[x, y] + ([color] if color else [])].dropna()
                fig = px.scatter(plot_df, x=x, y=y, color=color, title=title)

        # --- AREA ---
        elif ctype == "area":
            if x and y:
                plot_df = df[[x, y]].dropna()
                fig = px.area(plot_df, x=x, y=y, title=title)

        # --- HEATMAP ---
        elif ctype == "heatmap":
            num_df = df.select_dtypes(include="number")
            if num_df.shape[1] >= 2:
                corr = num_df.corr().round(2)
                fig = px.imshow(corr, title=title, text_auto=True)

        # Fallback: if we still have no fig, do a value_counts bar on first categorical col
        if fig is None:
            cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
            if cat_cols:
                col = cat_cols[0]
                counts = df[col].value_counts().head(20).reset_index()
                counts.columns = [col, "Count"]
                fig = px.bar(counts, x=col, y="Count",
                             title=f"{title} (fallback: {col} distribution)")
            else:
                num_cols = df.select_dtypes(include="number").columns.tolist()
                if num_cols:
                    fig = px.histogram(df, x=num_cols[0], title=f"{title} (fallback)")

        if fig is None:
            logger.error(f"Could not build any chart for spec: {spec.chart_id}")
            return False

        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            font_color="#333",
            title_font_size=16,
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.write_html(output_path, include_plotlyjs="cdn")
        logger.info(f"Chart '{spec.title}' rendered OK → {output_path}")
        return True

    except Exception as e:
        import traceback
        logger.error(f"Chart engine failed for '{spec.title}': {traceback.format_exc()}")
        return False
