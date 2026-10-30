"""
WorkforceIQ – Streamlit Design System and UI Theme.

Provides:
  - Enterprise design tokens, color palettes, and Plotly templates.
  - Custom CSS styling for metric cards, status badges, and alert banners.
  - Standardized formatting utilities for percentages, currency, dates, and risk tiers.
"""

from typing import Any, Dict, Optional
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Color Palette & Tokens (Enterprise Navy & Slate)
# ---------------------------------------------------------------------------

COLORS = {
    "primary": "#1e3a8a",        # Deep Navy
    "secondary": "#3b82f6",      # Vibrant Blue
    "accent": "#0ea5e9",         # Sky Blue
    "dark": "#0f172a",           # Dark Slate
    "light": "#f8fafc",          # Light Gray/White
    "border": "#e2e8f0",         # Border Gray
    "muted": "#64748b",          # Slate Gray
    "surface": "#ffffff",        # White Surface
    # Risk Tiers
    "risk_critical": "#dc2626",  # Red-600
    "risk_high": "#f97316",      # Orange-500
    "risk_medium": "#eab308",    # Yellow-500
    "risk_low": "#10b981",       # Emerald-500
    # Statuses
    "status_approved": "#10b981",
    "status_pending": "#f59e0b",
    "status_progress": "#3b82f6",
    "status_rejected": "#ef4444",
    "status_completed": "#059669",
    "status_cancelled": "#6b7280",
}

# Chart text color — adapts well to both light and dark Streamlit themes
CHART_TEXT_COLOR = "#1e293b"

PLOTLY_TEMPLATE = "plotly_white"


def apply_custom_css():
    """Injects modern, executive enterprise CSS into the Streamlit app."""
    st.markdown(
        """
        <style>
            /* Global fonts */
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

            html, body, [class*="css"] {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            }

            /* ----------------------------------------------------------------
               Main page title — high-contrast on any Streamlit background
            ---------------------------------------------------------------- */
            h1 {
                color: #f1f5f9 !important;
                font-weight: 800 !important;
                letter-spacing: -0.02em !important;
            }
            h2, h3 {
                color: #e2e8f0 !important;
                font-weight: 700 !important;
            }
            /* Streamlit's own st.title / st.header / st.subheader */
            .stAppHeader h1,
            [data-testid="stHeader"] h1 {
                color: #f1f5f9 !important;
            }

            /* ----------------------------------------------------------------
               KPI / Metric Cards — white surface cards for clear legibility
            ---------------------------------------------------------------- */
            .wiq-card {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 10px;
                padding: 20px 22px;
                margin-bottom: 16px;
                box-shadow: 0 2px 6px 0 rgba(15, 23, 42, 0.08);
                transition: box-shadow 0.15s ease;
            }
            .wiq-card:hover {
                box-shadow: 0 4px 12px 0 rgba(15, 23, 42, 0.12);
            }
            .wiq-card-title {
                color: #475569;
                font-size: 0.78rem;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.07em;
                margin-bottom: 8px;
            }
            .wiq-card-value {
                color: #0f172a;
                font-size: 2rem;
                font-weight: 800;
                line-height: 1.15;
            }
            .wiq-card-subtitle {
                color: #64748b;
                font-size: 0.80rem;
                margin-top: 7px;
                line-height: 1.4;
            }
            .wiq-card-delta {
                display: inline-block;
                margin-top: 6px;
                font-size: 0.75rem;
                font-weight: 700;
                padding: 2px 8px;
                border-radius: 4px;
            }
            .wiq-card-delta-positive {
                background: #dcfce7;
                color: #15803d;
            }
            .wiq-card-delta-info {
                background: #dbeafe;
                color: #1d4ed8;
            }
            .wiq-card-delta-warning {
                background: #fef9c3;
                color: #854d0e;
            }
            .wiq-card-delta-neutral {
                background: #f1f5f9;
                color: #475569;
            }

            /* ----------------------------------------------------------------
               Status and Risk Badges
            ---------------------------------------------------------------- */
            .wiq-badge {
                display: inline-block;
                padding: 3px 10px;
                border-radius: 9999px;
                font-size: 0.73rem;
                font-weight: 700;
                letter-spacing: 0.05em;
                text-transform: uppercase;
            }
            .wiq-badge-critical {
                background-color: #fee2e2;
                color: #b91c1c;
                border: 1px solid #fca5a5;
            }
            .wiq-badge-high {
                background-color: #ffedd5;
                color: #c2410c;
                border: 1px solid #fdba74;
            }
            .wiq-badge-medium {
                background-color: #fef9c3;
                color: #854d0e;
                border: 1px solid #fde047;
            }
            .wiq-badge-low {
                background-color: #d1fae5;
                color: #065f46;
                border: 1px solid #6ee7b7;
            }
            .wiq-badge-info {
                background-color: #e0f2fe;
                color: #0369a1;
                border: 1px solid #7dd3fc;
            }

            /* ----------------------------------------------------------------
               Responsible AI Disclaimer Banner
            ---------------------------------------------------------------- */
            .wiq-disclaimer {
                background-color: #eff6ff;
                border-left: 4px solid #3b82f6;
                padding: 12px 16px;
                border-radius: 0 8px 8px 0;
                color: #1e40af;
                font-size: 0.82rem;
                margin: 14px 0;
                line-height: 1.5;
            }

            /* ----------------------------------------------------------------
               Section Headers — visible on dark Streamlit background
            ---------------------------------------------------------------- */
            .wiq-section-header {
                color: #e2e8f0;
                font-size: 1.2rem;
                font-weight: 700;
                margin-top: 24px;
                margin-bottom: 14px;
                border-bottom: 2px solid #334155;
                padding-bottom: 8px;
                letter-spacing: -0.01em;
            }

            /* ----------------------------------------------------------------
               Navigation Module Cards (home page grid)
            ---------------------------------------------------------------- */
            .wiq-module-card {
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 16px;
                min-height: 130px;
                box-shadow: 0 1px 4px 0 rgba(0,0,0,0.2);
                transition: border-color 0.15s, box-shadow 0.15s;
            }
            .wiq-module-card:hover {
                border-color: #3b82f6;
                box-shadow: 0 4px 14px 0 rgba(59,130,246,0.15);
            }
            .wiq-module-card-title {
                font-size: 1.05rem;
                font-weight: 700;
                color: #93c5fd;
                margin-bottom: 8px;
            }
            .wiq-module-card-desc {
                color: #94a3b8;
                font-size: 0.84rem;
                line-height: 1.5;
            }

            /* ----------------------------------------------------------------
               Model info banner
            ---------------------------------------------------------------- */
            .wiq-model-banner {
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 11px 18px;
                margin-bottom: 18px;
                color: #cbd5e1;
                font-size: 0.85rem;
                line-height: 1.6;
            }
            .wiq-model-banner strong {
                color: #e2e8f0;
            }
            .wiq-model-banner code {
                background: #334155;
                color: #7dd3fc;
                padding: 1px 5px;
                border-radius: 3px;
                font-size: 0.82rem;
            }

            /* ----------------------------------------------------------------
               Sidebar styling
            ---------------------------------------------------------------- */
            [data-testid="stSidebar"] {
                background-color: #0f172a !important;
            }
            [data-testid="stSidebarNav"] a span {
                color: #cbd5e1 !important;
                font-size: 0.9rem;
            }
            [data-testid="stSidebarNav"] a:hover span {
                color: #93c5fd !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(
    title: str,
    value: Any,
    subtitle: str = "",
    delta: Optional[str] = None,
    delta_style: str = "neutral",
):
    """Renders a polished HTML metric card.

    Args:
        title: Short uppercase label.
        value: Primary large display value.
        subtitle: Smaller descriptive text below the value.
        delta: Optional tag/pill text shown below value.
        delta_style: One of 'positive', 'info', 'warning', 'neutral'.
    """
    delta_html = ""
    if delta:
        # Auto-detect style from content if not explicitly set
        if delta_style == "neutral":
            if any(k in delta.lower() for k in ("+", "pass", "verified", "active")):
                delta_style = "positive"
            elif any(k in delta.lower() for k in ("model", "calibrated", "forecast", "90d")):
                delta_style = "info"
            elif any(k in delta.lower() for k in ("warn", "risk", "alert", "review")):
                delta_style = "warning"
        delta_html = f"<div class='wiq-card-delta wiq-card-delta-{delta_style}'>{delta}</div>"

    html = f"""
    <div class="wiq-card">
        <div class="wiq-card-title">{title}</div>
        <div class="wiq-card-value">{value}</div>
        <div class="wiq-card-subtitle">{subtitle}</div>
        {delta_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def get_risk_badge_html(tier: str) -> str:
    """Returns HTML for an inline risk tier badge."""
    t = tier.upper()
    css_class = {
        "CRITICAL": "wiq-badge-critical",
        "HIGH": "wiq-badge-high",
        "MEDIUM": "wiq-badge-medium",
        "LOW": "wiq-badge-low",
    }.get(t, "wiq-badge-info")
    return f'<span class="wiq-badge {css_class}">{t}</span>'


def render_disclaimer_banner():
    """Renders the standard Responsible AI governance disclaimer banner."""
    st.markdown(
        """
        <div class="wiq-disclaimer">
            <strong>⚖️ Responsible AI Notice:</strong> All risk scores, rankings, and SHAP contributions are
            <strong>statistical associations</strong> derived from longitudinal history. They do <em>not</em> imply
            direct causation and must never be used to make automated employment decisions. All retention
            actions require human-led evaluation and managerial discretion.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_model_banner(
    algorithm: str = "RandomForest",
    model_version: str = "v2.0.0-prospective",
    threshold: float = 0.050,
    snapshot_date: str = "2026-06-15",
    horizon_days: int = 90,
):
    """Renders the standard model metadata banner for prediction pages."""
    st.markdown(
        f"""
        <div class="wiq-model-banner">
            <strong>Active Model:</strong> {algorithm} (<code>{model_version}</code>)
            &nbsp;|&nbsp;
            <strong>Calibration:</strong> Platt Sigmoid
            &nbsp;|&nbsp;
            <strong>Operational Threshold:</strong> <code>{threshold:.3f}</code>
            &nbsp;|&nbsp;
            <strong>Prediction Horizon:</strong> {horizon_days} days (snapshot: {snapshot_date})
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(text: str):
    """Renders a high-contrast section divider with heading text."""
    st.markdown(
        f"<div class='wiq-section-header'>{text}</div>",
        unsafe_allow_html=True,
    )


def create_plotly_figure(**kwargs) -> go.Figure:
    """Creates a Plotly figure pre-configured with the enterprise design template.

    Uses neutral white background with dark text to ensure readability in both
    Streamlit's light and dark themes (charts are rendered as images).
    """
    fig = go.Figure(**kwargs)
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        font=dict(family="Inter, sans-serif", size=12, color="#1e293b"),
        title_font=dict(size=14, color="#0f172a", family="Inter, sans-serif"),
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11, color="#334155"),
        ),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#f8fafc",
    )
    return fig
