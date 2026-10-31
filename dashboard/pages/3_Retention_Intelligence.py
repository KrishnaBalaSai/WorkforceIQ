"""
WorkforceIQ – Retention Intelligence (Page 3).

Provides:
  - Real-time prospective retention risk monitoring.
  - Platt-calibrated probability distributions.
  - Employee risk prioritization table with sorting, search, and department/tier filters.
  - Model operational threshold alerts (threshold = 0.050).
  - Direct deep-link navigation to Individual Employee Insights.
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
    get_risk_badge_html,
    render_disclaimer_banner,
    render_metric_card,
    render_section_header,
)

st.set_page_config(page_title="Retention Intelligence – WorkforceIQ", page_icon="🎯", layout="wide")
apply_custom_css()

st.title("🎯 Retention Intelligence")
st.markdown("Prospective flight-risk prioritization, calibrated probabilities, and retention alerts.")
render_disclaimer_banner()

# Model Metadata Banner
try:
    meta = api_client.get_model_metrics()
    model_version = meta.get("model_version", "v2.0.0-prospective")
    algorithm = meta.get("algorithm", "RandomForest")
    threshold = meta.get("threshold_optimization", {}).get(
        "selected_operational_threshold", 0.050
    )
    test_period = meta.get("test_period", "Not available")

except Exception:
    model_version = "v2.0.0-prospective"
    algorithm = "RandomForest"
    threshold = 0.050
    test_period = "Not available"

st.markdown(
    f"""
<div style="background-color:#1e293b; border:1px solid #475569;
border-radius:8px; padding:14px 18px; margin-bottom:20px;
color:#f8fafc; line-height:2;">
<strong>Active Model:</strong> {algorithm}
<code style="color:#86efac;">{model_version}</code>
&nbsp; | &nbsp;
<strong>Calibration:</strong> Platt Sigmoid
&nbsp; | &nbsp;
<strong>Operational Threshold:</strong>
<code style="color:#86efac;">{threshold:.3f}</code>
&nbsp; | &nbsp;
<strong>Model Test Period:</strong> {test_period}
</div>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Filter Controls
# ---------------------------------------------------------------------------
departments = api_client.get_departments()
dept_map = {d.get("name", d.get("department_id")): d.get("department_id") for d in departments}
dept_names = ["ALL"] + list(dept_map.keys())

col_f1, col_f2, col_f3, col_f4 = st.columns([2, 1.5, 2, 2])

with col_f1:
    selected_dept_name = st.selectbox("Department", dept_names, index=0)
    dept_filter_id = dept_map.get(selected_dept_name) if selected_dept_name != "ALL" else None

with col_f2:
    selected_tier = st.selectbox("Risk Tier", ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"], index=0)
    tier_filter = None if selected_tier == "ALL" else selected_tier

with col_f3:
    prob_min, prob_max = st.slider(
        "Operational Risk Probability Range",
        min_value=0.0,
        max_value=1.0,
        value=(0.0, 1.0),
        step=0.01,
        format="%.2f",
    )

with col_f4:
    search_query = st.text_input("Search Employee ID or Name", placeholder="e.g. EMP-000001 or Jane")

# Fetch shared workforce risk summary from the API
attrition_summary = api_client.get_attrition_summary()

# Fetch Phase 6 model calibration report
try:
    calibration_report = api_client.get_model_calibration() or {}
    test_calibration = calibration_report.get("test_calibration", {})
    calibration_ece = test_calibration.get("ece")
    reliability_bins = test_calibration.get("reliability_bins", [])
except Exception:
    calibration_ece = None
    reliability_bins = []

total_active = attrition_summary.get("total_active_workforce", 0)
high_count = attrition_summary.get("high_risk_count", 0)
critical_count = attrition_summary.get("critical_risk_count", 0)

alerts_total = high_count + critical_count

alert_pct = (
    alerts_total / total_active * 100
    if total_active > 0
    else 0.0
)

# ---------------------------------------------------------------------------
# Fetch Employee Flight-Risk Population
# ---------------------------------------------------------------------------
page_size = 100
employees_res = api_client.get_employees(
    page=1,
    page_size=page_size,
    department_id=dept_filter_id,
    risk_tier=tier_filter,
    min_risk_probability=prob_min,
    max_risk_probability=prob_max,
    search=search_query if search_query else None,
)

emp_items = employees_res.get("items", [])
total_matched = employees_res.get("total", len(emp_items))


# ---------------------------------------------------------------------------
# Build Employee Risk Table
# ---------------------------------------------------------------------------
table_rows = []

for employee in emp_items:
    first_name = employee.get("first_name") or ""
    last_name = employee.get("last_name") or ""

    risk_probability = employee.get("latest_flight_risk")

    table_rows.append({
        "Employee ID": employee.get("employee_id", "N/A"),
        "Employee Name": f"{first_name} {last_name}".strip(),
        "Department": employee.get("department_name") or "N/A",
        "Job Role": employee.get("role_title") or "N/A",
        "Latest Risk Probability": (
            f"{float(risk_probability):.1%}"
            if risk_probability is not None
            else "N/A"
        ),
        "Risk Tier": employee.get("latest_risk_tier") or "N/A",
        "Employment Status": employee.get("status") or "N/A",
        "Active": "Yes" if employee.get("is_active") else "No",
    })

df_table = pd.DataFrame(table_rows)

# ---------------------------------------------------------------------------
# Metrics Summary Bar
# ---------------------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)

with c1:
    render_metric_card(
        "Filtered Population",
        f"{total_matched:,}",
        subtitle=f"Page 1 of {max(1, (total_matched + page_size - 1) // page_size)}"
    )

with c2:
    render_metric_card(
        "Phase 6 ML Threshold",
        f"{threshold:.3f}",
        subtitle="Calibrated model probability",
        delta="90-day prediction"
    )

with c3:
    render_metric_card(
        "Synthetic Workforce Alerts",
        f"{alerts_total:,}",
        subtitle=f"{critical_count} Critical | {high_count} High",
        delta=f"{alert_pct:.2f}% of active workforce"
    )

with c4:
    render_metric_card(
        "Calibration ECE",
        f"{calibration_ece:.4f}" if calibration_ece is not None else "N/A",
        subtitle="Holdout test expected calibration error",
        delta="Phase 6 calibrated model"
    )

# ---------------------------------------------------------------------------
# Employee Risk Table
# ---------------------------------------------------------------------------
st.markdown("### Employee Risk Prioritization")
st.caption(
    "Latest synthetic operational risk scores from the employee database. "
    "These scores are separate from Phase 6 calibrated ML predictions."
)

if not df_table.empty:
    st.dataframe(
        df_table,
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No employees found for the selected filters.")


# ---------------------------------------------------------------------------
# Department Flight Risk Breakdown Chart
# ---------------------------------------------------------------------------
col_c1, col_c2 = st.columns(2)

with col_c1:
    st.subheader("📊 High & Critical Risk Count by Department")
    dept_risk = attrition_summary.get("department_risk_breakdown", [])
    if dept_risk:
        d_df = pd.DataFrame(dept_risk)
        fig_r = create_plotly_figure()
        fig_r.add_trace(go.Bar(
            x=d_df["department_name"],
            y=d_df["high_critical_risk_count"],
            marker_color=COLORS["risk_high"],
            text=d_df["high_critical_risk_count"],
            textposition="auto",
        ))
        fig_r.update_layout(height=300, xaxis_tickangle=-30, yaxis_title="Alert Count")
        st.plotly_chart(fig_r, use_container_width=True)


with col_c2:
    st.subheader("Model Calibration Reliability")

    st.caption(
        "Compares predicted probabilities with observed event rates "
        "on the Phase 6 holdout test cohort."
    )

    if reliability_bins:
        calibration_df = pd.DataFrame(reliability_bins)

        required_columns = [
            "mean_predicted_prob",
            "observed_event_rate",
            "bin_range",
            "sample_count",
        ]

        if all(column in calibration_df.columns for column in required_columns):

            # Create a Plotly figure using the existing theme helper.
            fig = create_plotly_figure()

            fig.add_trace(
                go.Scatter(
                    x=calibration_df["mean_predicted_prob"],
                    y=calibration_df["observed_event_rate"],
                    mode="lines+markers",
                    name="Observed calibration",
                    customdata=calibration_df[
                        ["bin_range", "sample_count"]
                    ],
                    hovertemplate=(
                        "Predicted: %{x:.2%}<br>"
                        "Observed: %{y:.2%}<br>"
                        "Bin: %{customdata[0]}<br>"
                        "Samples: %{customdata[1]:,}"
                        "<extra></extra>"
                    ),
                )
            )

            max_value = max(
                calibration_df["mean_predicted_prob"].max(),
                calibration_df["observed_event_rate"].max(),
            ) * 1.15

            fig.add_trace(
                go.Scatter(
                    x=[0, max_value],
                    y=[0, max_value],
                    mode="lines",
                    name="Perfect calibration",
                    line=dict(dash="dash"),
                )
            )

            fig.update_layout(
                title="Holdout Test Calibration",
                xaxis_title="Mean Predicted Probability",
                yaxis_title="Observed Event Rate",
                xaxis=dict(
                    tickformat=".0%",
                    range=[0, max_value],
                ),
                yaxis=dict(
                    tickformat=".0%",
                    range=[0, max_value],
                ),
                height=420,
                hovermode="closest",
                legend=dict(
                    orientation="h",
                    y=-0.2,
                ),
            )

            # IMPORTANT: Do not pass fig to create_plotly_figure().
            st.plotly_chart(
                fig,
                use_container_width=True,
            )

        else:
            st.warning(
                "Calibration report is missing required reliability fields."
            )

    else:
        st.info(
            "Calibration reliability data is unavailable."
        )


# ---------------------------------------------------------------------------
# Download Retention Risk Forecast (Phase 8 Export)
# ---------------------------------------------------------------------------
render_section_header("Data Export")
risk_csv = api_client.get_export_csv("retention-risk")
st.download_button(
    label="📥 Download Retention Risk Predictions (CSV)",
    data=risk_csv,
    file_name="workforceiq_retention_risk.csv",
    mime="text/csv",
    help="Download calibrated retention risk probabilities and top SHAP drivers for active employees.",
)
