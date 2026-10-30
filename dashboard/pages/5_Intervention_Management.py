r"""
WorkforceIQ – Retention Intervention Management (Page 5).

Human-in-the-Loop Lifecycle:
  CREATED -> PENDING_REVIEW -> APPROVED -> IN_PROGRESS -> COMPLETED
                                                        \-> CANCELLED

Provides:
  - Retention interventions list with filtering (status, type, priority).
  - Human review queue: explicit Approve / Reject / Start / Complete / Cancel workflows.
  - Intervention creation form.
  - Immutable audit event history tracking all state transitions and reviewer justifications.
"""

from datetime import datetime
import pandas as pd
import streamlit as st

from dashboard.api_client import api_client
from dashboard.theme import (
    COLORS,
    apply_custom_css,
    create_plotly_figure,
    render_disclaimer_banner,
    render_metric_card,
)

st.set_page_config(page_title="Intervention Management – WorkforceIQ", page_icon="🛡️", layout="wide")
apply_custom_css()

st.title("🛡️ Retention Intervention Management")
st.markdown("Human-in-the-loop retention action governance, review workflows, and immutable audit logs.")
render_disclaimer_banner()

# ---------------------------------------------------------------------------
# Filter Controls & KPI Summary
# ---------------------------------------------------------------------------
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    status_filter = st.selectbox(
        "Lifecycle Status Filter",
        ["ALL", "PENDING_REVIEW", "APPROVED", "IN_PROGRESS", "CREATED", "COMPLETED", "CANCELLED", "REJECTED"],
        index=0,
    )
with col_f2:
    type_filter = st.selectbox(
        "Intervention Type",
        ["ALL", "STAY_INTERVIEW", "COMPENSATION_REVIEW", "WORKLOAD_REBALANCING", "CAREER_PATHING", "MANAGER_COACHING"],
        index=0,
    )
with col_f3:
    emp_search = st.text_input("Filter by Employee ID", placeholder="e.g. EMP-000001")

# Fetch interventions
interventions_res = api_client.get_interventions(
    page=1,
    page_size=200,
    status=None if status_filter == "ALL" else status_filter,
    intervention_type=None if type_filter == "ALL" else type_filter,
    employee_id=emp_search.strip() if emp_search else None,
)

items = interventions_res.get("items", [])
total_records = interventions_res.get("total", len(items))

# Status counts
counts = {"PENDING_REVIEW": 0, "APPROVED": 0, "IN_PROGRESS": 0, "COMPLETED": 0}
for it in items:
    s = it.get("status", "CREATED")
    if s in counts:
        counts[s] += 1

c1, c2, c3, c4 = st.columns(4)
with c1:
    render_metric_card("Pending Review", counts["PENDING_REVIEW"], subtitle="Awaiting HR leadership action", delta="Action Required")
with c2:
    render_metric_card("Approved", counts["APPROVED"], subtitle="Ready for implementation", delta="Approved")
with c3:
    render_metric_card("In Progress", counts["IN_PROGRESS"], subtitle="Active retention engagements", delta="Ongoing")
with c4:
    render_metric_card("Completed", counts["COMPLETED"], subtitle="Successfully evaluated", delta="Historical")

st.markdown("<hr style='margin: 15px 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Pending Reviews & Human Decision Queue
# ---------------------------------------------------------------------------
st.subheader("⚖️ Human-in-the-Loop Decision Queue")
st.caption("Interventions requiring qualified human review before any organizational action is taken.")

pending_items = [it for it in items if it.get("status") in ["PENDING_REVIEW", "CREATED"]]

if not pending_items:
    st.success("✅ No interventions currently pending human review.")
else:
    for item in pending_items[:5]:  # Display top 5 pending
        iid = item.get("intervention_id")
        eid = item.get("employee_id")
        itype = item.get("intervention_type")
        cost = item.get("cost_usd", 0.0)
        prio = item.get("priority", "MEDIUM")
        just = item.get("justification", "No justification provided.")
        cur_status = item.get("status", "PENDING_REVIEW")

        with st.expander(f"Review Required: {iid} | Employee: {eid} | Type: {itype} | Priority: {prio}", expanded=True):
            col_d1, col_d2 = st.columns([3, 2])
            with col_d1:
                st.markdown(f"**Target Employee:** `{eid}`")
                st.markdown(f"**Intervention Type:** `{itype}` | **Estimated Budget:** `${cost:,.2f}`")
                st.markdown(f"**Manager Justification:** *\"{just}\"*")
                st.markdown(f"**Current Status:** `{cur_status}`")

            with col_d2:
                st.markdown("**Reviewer Decision:**")
                rev_notes = st.text_input(f"Decision Rationale for {iid}", key=f"notes_{iid}", placeholder="Enter review justification...")
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("✅ Approve", key=f"app_{iid}", type="primary"):
                        res = api_client.transition_intervention(
                            intervention_id=iid,
                            target_status="APPROVED",
                            reason=rev_notes if rev_notes else "Approved by HR Director in dashboard review",
                        )
                        if res:
                            st.success(f"Intervention {iid} APPROVED.")
                            st.rerun()
                with col_b2:
                    if st.button("❌ Reject", key=f"rej_{iid}"):
                        res = api_client.transition_intervention(
                            intervention_id=iid,
                            target_status="REJECTED",
                            reason=rev_notes if rev_notes else "Rejected by HR Director in dashboard review",
                        )
                        if res:
                            st.warning(f"Intervention {iid} REJECTED.")
                            st.rerun()

st.markdown("<div class='wiq-section-header'>All Interventions & Lifecycle Tracking</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Interventions Data Table & State Transition Controls
# ---------------------------------------------------------------------------
if items:
    df_interventions = pd.DataFrame([
        {
            "Intervention ID": it.get("intervention_id"),
            "Employee ID": it.get("employee_id"),
            "Type": it.get("intervention_type"),
            "Status": it.get("status"),
            "Priority": it.get("priority"),
            "Budget (USD)": f"${float(it.get('cost_usd', 0)):,.2f}",
            "Proposed By": it.get("proposed_by", "USR-MGR"),
            "Created Date": str(it.get("created_at", ""))[:10],
        }
        for it in items
    ])
    st.dataframe(df_interventions, use_container_width=True, hide_index=True)

    # State transition tool
    st.markdown("#### Transition Intervention State (Manual Governance)")
    col_t1, col_t2, col_t3, col_t4 = st.columns([2, 2, 3, 1])
    with col_t1:
        selected_iid = st.selectbox("Select Intervention ID", [it.get("intervention_id") for it in items])
    with col_t2:
        new_state = st.selectbox("New Lifecycle State", ["IN_PROGRESS", "COMPLETED", "CANCELLED"])
    with col_t3:
        reason_txt = st.text_input("Operational Reason / Notes", placeholder="e.g. Stay interview completed; workload reduced by 10 hrs")
    with col_t4:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if st.button("Update State"):
            res = api_client.transition_intervention(
                intervention_id=selected_iid,
                target_status=new_state,
                reason=reason_txt if reason_txt else f"State changed to {new_state} via dashboard",
            )
            if res:
                st.success(f"{selected_iid} updated to {new_state}!")
                st.rerun()
            else:
                st.error("Invalid state transition for current lifecycle stage.")

else:
    st.info("No intervention records found.")

# ---------------------------------------------------------------------------
# Create New Intervention Form
# ---------------------------------------------------------------------------
st.markdown("<div class='wiq-section-header'>Propose New Intervention</div>", unsafe_allow_html=True)

with st.expander("➕ Open New Intervention Entry Form"):
    with st.form("new_intervention_form"):
        col_n1, col_n2 = st.columns(2)
        with col_n1:
            n_eid = st.text_input("Target Employee ID", placeholder="e.g. EMP-000001")
            n_type = st.selectbox(
                "Intervention Type",
                [
                    "STAY_INTERVIEW",
                    "COMPENSATION_REVIEW",
                    "WORKLOAD_REBALANCING",
                    "CAREER_PATHING",
                    "MANAGER_COACHING",
                    "RETENTION_BONUS",
                ],
            )
            n_prio = st.selectbox("Priority", ["HIGH", "CRITICAL", "MEDIUM", "LOW"])
        with col_n2:
            n_cost = st.number_input("Proposed Budget (USD)", min_value=0.0, value=750.0, step=100.0)
            n_just = st.text_area("Justification & Plan", placeholder="Describe the proposed retention action and intended outcome...")

        submit_n = st.form_submit_button("Submit Intervention for Approval", type="primary")
        if submit_n:
            if not n_eid:
                st.error("Employee ID is required.")
            else:
                payload = {
                    "employee_id": n_eid.strip(),
                    "intervention_type": n_type,
                    "priority": n_prio,
                    "cost_usd": float(n_cost),
                    "justification": n_just,
                    "proposed_by": "USR-HR-LEAD",
                }
                res = api_client.propose_intervention(payload)
                if res:
                    st.success(f"Intervention `{res.get('intervention_id')}` submitted for human review!")
                    st.rerun()
                else:
                    st.error("Failed to submit intervention.")
