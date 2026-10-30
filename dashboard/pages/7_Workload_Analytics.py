"""
WorkforceIQ – Workload & Project Analytics (Page 7).

Provides:
  - Workforce allocation metrics (Active projects, assigned employee headcount).
  - Average weekly logged hours by department.
  - Over-allocation risk analysis (>45 hours/week burnout warning threshold).
  - Billable vs. non-billable project allocation distributions.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.api_client import api_client
from dashboard.theme import (
    COLORS,
    apply_custom_css,
    create_plotly_figure,
    render_disclaimer_banner,
    render_metric_card,
)

st.set_page_config(page_title="Workload Analytics – WorkforceIQ", page_icon="⏱️", layout="wide")
apply_custom_css()

st.title("⏱️ Workload & Capacity Analytics")
st.markdown("Workforce allocation, weekly logged hours, billable project intensity, and over-allocation burnout risks.")
render_disclaimer_banner()

# Fetch workload data
departments = api_client.get_departments()
workload_data = api_client.get_workload_analytics()

total_projects = workload_data.get("total_active_projects", 45)
avg_hours = workload_data.get("average_weekly_hours", 41.8)
over_allocated_pct = workload_data.get("over_allocation_pct", 14.6)
billable_pct = 78.4

# KPI Header
c1, c2, c3, c4 = st.columns(4)
with c1:
    render_metric_card("Active Projects", total_projects, subtitle="Enterprise initiatives", delta="+4 this quarter")
with c2:
    render_metric_card("Avg Weekly Logged Hours", f"{avg_hours:.1f} hrs", subtitle="Standard benchmark: 40 hrs", delta="+1.8h baseline")
with c3:
    render_metric_card("Over-Allocated Staff", f"{over_allocated_pct:.1f}%", subtitle="Logging >45 hours/week", delta="High Burnout Risk")
with c4:
    render_metric_card("Billable Allocation", f"{billable_pct:.1f}%", subtitle="Client & revenue projects", delta="Healthy Target")

st.markdown("<hr style='margin: 15px 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Department Workload & Overtime Analysis
# ---------------------------------------------------------------------------
col_w1, col_w2 = st.columns(2)

with col_w1:
    st.subheader("📊 Average Weekly Hours by Department")
    dept_hours = [
        {"Department": "AI Research", "Hours": 44.5, "Overtime Pct": 24.2},
        {"Department": "Engineering", "Hours": 43.8, "Overtime Pct": 21.5},
        {"Department": "Sales & Accounts", "Hours": 42.6, "Overtime Pct": 16.4},
        {"Department": "Product Management", "Hours": 41.9, "Overtime Pct": 13.8},
        {"Department": "Customer Success", "Hours": 41.2, "Overtime Pct": 11.0},
        {"Department": "Marketing & Growth", "Hours": 39.8, "Overtime Pct": 6.5},
        {"Department": "Finance & Legal", "Hours": 39.2, "Overtime Pct": 5.8},
        {"Department": "People & HR", "Hours": 38.5, "Overtime Pct": 4.2},
    ]
    df_wh = pd.DataFrame(dept_hours)

    fig_wh = create_plotly_figure()
    fig_wh.add_trace(go.Bar(
        x=df_wh["Department"],
        y=df_wh["Hours"],
        marker_color=[COLORS["risk_critical"] if h >= 43.5 else COLORS["primary"] for h in df_wh["Hours"]],
        text=df_wh["Hours"],
        textposition="auto",
    ))
    fig_wh.add_hline(y=40, line_dash="solid", line_color="#64748b", annotation_text="Standard 40h Baseline")
    fig_wh.add_hline(y=45, line_dash="dash", line_color=COLORS["risk_critical"], annotation_text="Burnout Threshold (45h)")
    fig_wh.update_layout(height=320, xaxis_tickangle=-30, yaxis_title="Hours / Week")
    st.plotly_chart(fig_wh, use_container_width=True)

with col_w2:
    st.subheader("🔥 Over-Allocation Vulnerability Rate (>45 hrs/week)")
    st.caption("Percentage of departmental workforce exceeding 45 weekly hours in trailing 90 days.")

    fig_ov = create_plotly_figure()
    fig_ov.add_trace(go.Bar(
        x=df_wh["Department"],
        y=df_wh["Overtime Pct"],
        marker_color=[COLORS["risk_high"] if p >= 15 else COLORS["secondary"] for p in df_wh["Overtime Pct"]],
        text=[f"{p}%" for p in df_wh["Overtime Pct"]],
        textposition="auto",
    ))
    fig_ov.update_layout(height=320, xaxis_tickangle=-30, yaxis_title="% Over-Allocated (>45h)")
    st.plotly_chart(fig_ov, use_container_width=True)

# ---------------------------------------------------------------------------
# Project Allocations & Billability Split
# ---------------------------------------------------------------------------
st.markdown("<div class='wiq-section-header'>Project Allocation & Billability Distribution</div>", unsafe_allow_html=True)

col_p1, col_p2 = st.columns([1, 2])

with col_p1:
    st.markdown("#### Billable vs. Internal Ratio")
    bill_data = {"Billable Client Projects": 78.4, "Internal R&D / Platform": 21.6}
    fig_b = create_plotly_figure()
    fig_b.add_trace(go.Pie(
        labels=list(bill_data.keys()),
        values=list(bill_data.values()),
        hole=0.45,
        marker=dict(colors=[COLORS["primary"], COLORS["accent"]]),
    ))
    fig_b.update_layout(height=280, margin=dict(t=10, b=10, l=10, r=10))
    st.plotly_chart(fig_b, use_container_width=True)

with col_p2:
    st.markdown("#### Workload Hours Distribution Histogram")
    st.caption("Employee distribution across weekly hours logged.")
    hour_buckets = ["< 35 hrs", "35 - 40 hrs", "40 - 45 hrs", "45 - 50 hrs (Elevated)", "> 50 hrs (Critical)"]
    hour_counts = [620, 4850, 2240, 980, 340]
    fig_hb = create_plotly_figure()
    fig_hb.add_trace(go.Bar(
        x=hour_buckets,
        y=hour_counts,
        marker_color=[
            "#94a3b8",
            COLORS["status_approved"],
            COLORS["secondary"],
            COLORS["risk_high"],
            COLORS["risk_critical"],
        ],
        text=hour_counts,
        textposition="auto",
    ))
    fig_hb.update_layout(height=280, yaxis_title="Employee Count", margin=dict(t=10, b=10, l=10, r=10))
    st.plotly_chart(fig_hb, use_container_width=True)
