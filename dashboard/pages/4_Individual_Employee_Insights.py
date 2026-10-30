"""
WorkforceIQ – Individual Employee Insights & 360 Explainability (Page 4).

Provides:
  - Employee 360 Profile (title, department, manager, tenure, compa-ratio, career velocity).
  - Real-time model inference and Platt-calibrated flight-risk score.
  - Interactive SHAP waterfall / bidirectional driver breakdown:
    - Positive Risk Contributors (features increasing risk).
    - Negative Protective Factors (features decreasing risk).
  - Longitudinal engagement survey history (Job Satisfaction, Trust, Burnout Risk).
  - Workload intensity history (Weekly hours, project allocations).
  - Career timeline (promotions, compensation revisions, performance reviews).
  - Direct Action Form: Propose a targeted retention intervention.
"""

from datetime import date
import pandas as pd
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
)

st.set_page_config(page_title="Employee 360 Insights – WorkforceIQ", page_icon="🔍", layout="wide")
apply_custom_css()

st.title("🔍 Individual Employee Insights & SHAP Explainability")
st.markdown("Granular employee profile, prospective retention risk, and bidirectional SHAP feature attribution.")
render_disclaimer_banner()

# ---------------------------------------------------------------------------
# Employee Selection & Lookup
# ---------------------------------------------------------------------------
col_s1, col_s2 = st.columns([3, 1])
with col_s1:
    selected_id = st.text_input("Enter Employee ID", value="EMP-000001", placeholder="e.g. EMP-000001")
with col_s2:
    st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
    fetch_btn = st.button("Load Profile", type="primary")

emp_detail = api_client.get_employee_detail(selected_id.strip())

if not emp_detail:
    st.error(f"Employee '{selected_id}' not found in database. Please verify the ID format (e.g. EMP-000001).")
    st.stop()

# ---------------------------------------------------------------------------
# Employee Profile Summary Banner
# ---------------------------------------------------------------------------
emp_prof = emp_detail.get("profile") or emp_detail
dept_info = emp_detail.get("department") or {}
role_info = emp_detail.get("role") or {}
mgr_info = emp_detail.get("manager") or {}
comp_history = emp_detail.get("compensation_history") or []
latest_comp = comp_history[-1] if comp_history else emp_detail.get("compensation", {})

full_name = f"{emp_prof.get('first_name', '')} {emp_prof.get('last_name', '')}".strip()
title = role_info.get("title", emp_prof.get("role_title", "Role Title"))
dept_name = dept_info.get("name", emp_prof.get("department_name", "Department"))
hire_date = str(emp_prof.get("hire_date", "2024-01-01"))
tenure_months = float(emp_prof.get("tenure_months", 24.0)) if "tenure_months" in emp_prof else 24.0
work_location = emp_prof.get("work_location", "HYBRID")
base_sal = float(latest_comp.get("base_salary", 110000.0))
mid_sal = float(role_info.get("mid_salary", 110000.0)) if "mid_salary" in role_info else 110000.0
compa_ratio = round(base_sal / mid_sal, 3) if mid_sal > 0 else 1.0

# Fetch real-time prospective prediction & SHAP explanation
pred_result = api_client.get_employee_prediction(selected_id.strip(), top_n_drivers=6)
if not pred_result:
    pred_prob = 0.015
    risk_tier = "LOW"
    risk_drivers = []
    protective_factors = []
    is_alert = False
else:
    pred_prob = pred_result.get("flight_risk_probability", 0.015)
    risk_tier = pred_result.get("risk_tier", "LOW")
    risk_drivers = pred_result.get("top_risk_drivers", [])
    protective_factors = pred_result.get("top_protective_factors", [])
    is_alert = pred_result.get("is_retention_alert", False)

st.markdown(
    f"""
    <div style="background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 20px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
                <h2 style="color: #0f172a; margin: 0 0 4px 0; font-size: 1.6rem; font-weight: 700;">{full_name}</h2>
                <div style="color: #475569; font-size: 1rem; font-weight: 500;">
                    {title} • <span style="color: #1e3a8a; font-weight: 600;">{dept_name}</span> • ID: <code>{selected_id}</code>
                </div>
                <div style="color: #64748b; font-size: 0.85rem; margin-top: 6px;">
                    Hired: {hire_date} ({tenure_months:.1f} mos tenure) | Location: <strong>{work_location}</strong> | Manager: <strong>{mgr_info.get('name', 'None')}</strong>
                </div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 0.8rem; font-weight: 600; color: #64748b; text-transform: uppercase;">Prospective Flight Risk</div>
                <div style="font-size: 2.1rem; font-weight: 800; color: {'#dc2626' if pred_prob >= 0.05 else '#0f172a'}; margin: 2px 0;">
                    {pred_prob * 100:.2f}%
                </div>
                <div>{get_risk_badge_html(risk_tier)}</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# SHAP Explainability Breakdown
# ---------------------------------------------------------------------------
st.markdown("<div class='wiq-section-header'>SHAP Explainability & Key Drivers</div>", unsafe_allow_html=True)
st.caption(
    "Bidirectional feature attribution from TreeExplainer. Explanations describe statistical associations, NOT causal conclusions."
)

col_shap1, col_shap2 = st.columns(2)

with col_shap1:
    st.markdown("#### 🚨 Top Risk Drivers (Increases Departure Probability)")
    if risk_drivers:
        for d in risk_drivers:
            label = d.get("human_label", d.get("feature", ""))
            val = d.get("shap_value", 0.0)
            interp = d.get("interpretation", "")
            st.markdown(
                f"""
                <div style="background: #fff1f2; border-left: 4px solid #f43f5e; padding: 10px 14px; border-radius: 4px; margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between; font-weight: 600; color: #9f1239;">
                        <span>{label}</span>
                        <span>+{val:.4f} SHAP</span>
                    </div>
                    <div style="font-size: 0.8rem; color: #881337; margin-top: 3px;">{interp}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("No significant risk-amplifying drivers detected for this employee.")

with col_shap2:
    st.markdown("#### 🛡️ Top Protective Factors (Decreases Departure Probability)")
    if protective_factors:
        for p in protective_factors:
            label = p.get("human_label", p.get("feature", ""))
            val = p.get("shap_value", 0.0)
            interp = p.get("interpretation", "")
            st.markdown(
                f"""
                <div style="background: #ecfdf5; border-left: 4px solid #10b981; padding: 10px 14px; border-radius: 4px; margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between; font-weight: 600; color: #065f46;">
                        <span>{label}</span>
                        <span>{val:.4f} SHAP</span>
                    </div>
                    <div style="font-size: 0.8rem; color: #047857; margin-top: 3px;">{interp}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("No strong protective factors registered.")

# ---------------------------------------------------------------------------
# Longitudinal Engagement & Workload Trends
# ---------------------------------------------------------------------------
st.markdown("<div class='wiq-section-header'>Longitudinal Engagement & Workload Trajectory</div>", unsafe_allow_html=True)

surveys = emp_detail.get("engagement_surveys", [])
projects = emp_detail.get("project_assignments", [])

col_e1, col_e2 = st.columns(2)

with col_e1:
    st.markdown("#### Engagement Survey Scores Over Time")
    if surveys:
        s_df = pd.DataFrame(surveys)
        s_df["survey_date"] = pd.to_datetime(s_df["survey_date"])
        s_df = s_df.sort_values("survey_date")
        
        fig_s = create_plotly_figure()
        fig_s.add_trace(go.Scatter(
            x=s_df["survey_date"],
            y=s_df["job_satisfaction"],
            name="Job Satisfaction",
            line=dict(color=COLORS["secondary"], width=2),
            mode="lines+markers",
        ))
        fig_s.add_trace(go.Scatter(
            x=s_df["survey_date"],
            y=s_df["work_life_balance"],
            name="Work-Life Balance",
            line=dict(color=COLORS["status_approved"], width=2),
            mode="lines+markers",
        ))
        fig_s.add_trace(go.Scatter(
            x=s_df["survey_date"],
            y=s_df["burnout_risk_index"] * 5,  # Scale to 5
            name="Burnout Index (Scaled 1-5)",
            line=dict(color=COLORS["risk_critical"], width=2, dash="dash"),
            mode="lines",
        ))
        fig_s.update_layout(height=280, yaxis_range=[0, 5.5], margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig_s, use_container_width=True)
    else:
        st.info("No engagement survey records available for this employee.")

with col_e2:
    st.markdown("#### Weekly Logged Hours & Project Assignments")
    if projects:
        p_df = pd.DataFrame(projects)
        fig_p = create_plotly_figure()
        fig_p.add_trace(go.Bar(
            x=p_df["project_name"],
            y=p_df["logged_hours_weekly"],
            marker_color=COLORS["primary"],
            name="Logged Weekly Hours",
        ))
        fig_p.add_hline(
            y=45,
            line_dash="dash",
            line_color=COLORS["risk_critical"],
            annotation_text="Overtime Alert (45h)",
        )
        fig_p.update_layout(height=280, yaxis_title="Hours/Week", margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig_p, use_container_width=True)
    else:
        st.info("No active project assignments recorded.")

# ---------------------------------------------------------------------------
# Human-in-the-Loop Action: Propose Retention Intervention
# ---------------------------------------------------------------------------
st.markdown("<div class='wiq-section-header'>Take Retention Action (Human-in-the-Loop)</div>", unsafe_allow_html=True)

with st.expander("➕ Propose Retention Intervention for this Employee", expanded=is_alert):
    with st.form("propose_intervention_form"):
        st.markdown(f"**Target Employee:** {full_name} (`{selected_id}`) | Risk: **{pred_prob*100:.2f}%**")
        
        col_i1, col_i2 = st.columns(2)
        with col_i1:
            i_type = st.selectbox(
                "Intervention Type",
                [
                    "STAY_INTERVIEW",
                    "COMPENSATION_REVIEW",
                    "WORKLOAD_REBALANCING",
                    "CAREER_PATHING",
                    "MANAGER_COACHING",
                    "RETENTION_BONUS",
                    "TRAINING_BUDGET",
                ],
            )
            i_priority = st.selectbox("Priority Level", ["HIGH", "CRITICAL", "MEDIUM", "LOW"], index=0 if is_alert else 2)
        
        with col_i2:
            i_cost = st.number_input("Budget / Estimated Cost (USD)", min_value=0.0, value=500.0, step=100.0)
            i_justification = st.text_area(
                "Intervention Justification",
                placeholder="Document human managerial context, stay interview notes, or rationale...",
                value=f"Proactive retention review initiated based on elevated flight risk ({pred_prob*100:.2f}%) and SHAP workload drivers.",
            )

        submit_btn = st.form_submit_button("Submit Intervention for Review", type="primary")

        if submit_btn:
            payload = {
                "employee_id": selected_id,
                "intervention_type": i_type,
                "priority": i_priority,
                "cost_usd": float(i_cost),
                "justification": i_justification,
                "proposed_by": "USR-DASHBOARD-MGR",
            }
            res = api_client.propose_intervention(payload)
            if res:
                st.success(f"Intervention successfully proposed! Assigned ID: `{res.get('intervention_id', 'INT-NEW')}`. Awaiting HR review.")
            else:
                st.error("Failed to propose intervention. Please check backend service logs.")
