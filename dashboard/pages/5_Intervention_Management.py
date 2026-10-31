
"""
WorkforceIQ – Retention Intervention Management (Page 5).

Human-in-the-Loop Lifecycle:
    CREATED -> PENDING_REVIEW -> APPROVED -> IN_PROGRESS -> COMPLETED
        |              |             |             |
        +--------------+-------------+-------------+-> CANCELLED

Legacy statuses are displayed as historical records and are not
automatically rewritten or treated as current lifecycle transitions.
"""

import pandas as pd
import streamlit as st

from dashboard.api_client import api_client
from dashboard.theme import (
    apply_custom_css,
    render_disclaimer_banner,
    render_metric_card,
)

# Values defined in backend/models/orm.py
INTERVENTION_TYPES = [
    "COMPENSATION_INCREASE",
    "RETENTION_BONUS",
    "ROLE_PROMOTION",
    "PROJECT_REASSIGNMENT",
    "FLEXIBLE_WORK_SCHEDULE",
    "EXECUTIVE_MENTORSHIP",
    "CAREER_DEVELOPMENT",
]

STATUS_OPTIONS = [
    "CREATED",
    "PENDING_REVIEW",
    "APPROVED",
    "IN_PROGRESS",
    "COMPLETED",
    "CANCELLED",
    "RECOMMENDED",
    "REJECTED",
    "OFFERED",
    "ACCEPTED",
    "DECLINED",
    "FAILED",
]

# Only these transitions are permitted by intervention_service.py.
ALLOWED_TRANSITIONS = {
    "CREATED": ["PENDING_REVIEW", "CANCELLED"],
    "PENDING_REVIEW": ["APPROVED", "CANCELLED"],
    "APPROVED": ["IN_PROGRESS", "CANCELLED"],
    "IN_PROGRESS": ["COMPLETED", "CANCELLED"],
    "RECOMMENDED": ["PENDING_REVIEW", "APPROVED", "CANCELLED"],
    "COMPLETED": [],
    "CANCELLED": [],
}

st.set_page_config(
    page_title="Intervention Management – WorkforceIQ",
    page_icon="🛡️",
    layout="wide",
)
apply_custom_css()

st.title("Retention Intervention Management")
st.markdown(
    "Human-in-the-loop retention action governance, "
    "review workflows, and immutable audit logs."
)
render_disclaimer_banner()


# ---------------------------------------------------------------------
# Fetch all intervention records for accurate KPIs and filtering
# ---------------------------------------------------------------------

@st.cache_data(ttl=15, show_spinner=False)
def load_all_interventions():
    records = []
    page = 1
    page_size = 200

    while True:
        response = api_client.get_interventions(
            page=page,
            page_size=page_size,
        )

        if not response:
            break

        page_items = response.get("items", [])
        records.extend(page_items)

        total = int(response.get("total", len(records)))
        if not page_items or len(records) >= total:
            break

        page += 1

    return records


try:
    all_items = load_all_interventions()
except (RuntimeError, PermissionError) as exc:
    st.error(f"Unable to load intervention records: {exc}")
    st.stop()


# ---------------------------------------------------------------------
# Filter controls
# ---------------------------------------------------------------------

st.subheader("Intervention Filters")

existing_statuses = {
    str(item.get("status", "")).upper()
    for item in all_items
    if item.get("status")
}

existing_types = {
    str(item.get("intervention_type", "")).upper()
    for item in all_items
    if item.get("intervention_type")
}

col_f1, col_f2, col_f3 = st.columns(3)

with col_f1:
    status_filter = st.selectbox(
        "Lifecycle Status",
        ["ALL"] + [
            status for status in STATUS_OPTIONS
            if status in existing_statuses
        ],
    )

with col_f2:
    type_filter = st.selectbox(
        "Intervention Type",
        ["ALL"] + [
            intervention_type
            for intervention_type in INTERVENTION_TYPES
            if intervention_type in existing_types
        ],
    )

with col_f3:
    employee_search = st.text_input(
        "Search Employee ID",
        placeholder="e.g. EMP-000001",
    )


# Apply filters locally so KPI values remain independent of filters.
items = all_items

if status_filter != "ALL":
    items = [
        item for item in items
        if str(item.get("status", "")).upper() == status_filter
    ]

if type_filter != "ALL":
    items = [
        item for item in items
        if str(item.get("intervention_type", "")).upper() == type_filter
    ]

if employee_search.strip():
    search_value = employee_search.strip().lower()
    items = [
        item for item in items
        if search_value in str(item.get("employee_id", "")).lower()
    ]


# ---------------------------------------------------------------------
# Global KPI summary - independent of selected filters
# ---------------------------------------------------------------------

global_counts = {
    status: 0 for status in STATUS_OPTIONS
}

for item in all_items:
    status = str(item.get("status", "")).upper()
    if status in global_counts:
        global_counts[status] += 1

st.subheader("Intervention Lifecycle Summary")

c1, c2, c3, c4 = st.columns(4)

with c1:
    render_metric_card(
        "Pending Review",
        global_counts["PENDING_REVIEW"],
        subtitle="Awaiting human review",
    )

with c2:
    render_metric_card(
        "Approved",
        global_counts["APPROVED"],
        subtitle="Approved for implementation",
    )

with c3:
    render_metric_card(
        "In Progress",
        global_counts["IN_PROGRESS"],
        subtitle="Active interventions",
    )

with c4:
    render_metric_card(
        "Completed",
        global_counts["COMPLETED"],
        subtitle="Completed interventions",
    )

legacy_count = sum(
    global_counts[status]
    for status in [
        "RECOMMENDED",
        "REJECTED",
        "OFFERED",
        "ACCEPTED",
        "DECLINED",
        "FAILED",
    ]
)

if legacy_count:
    st.caption(
        f"Historical/legacy records: {legacy_count}. "
        "These are preserved and are not counted as current lifecycle approvals."
    )

st.divider()


# ---------------------------------------------------------------------
# Human-in-the-loop review queue
# ---------------------------------------------------------------------

st.subheader("Human-in-the-Loop Decision Queue")

st.caption(
    "Only interventions in actionable lifecycle states are shown here. "
    "Every decision requires a human reviewer and an audit event."
)

pending_items = [
    item for item in items
    if item.get("status") in [
        "CREATED",
        "PENDING_REVIEW",
        "RECOMMENDED",
    ]
]

if not pending_items:
    st.info("No interventions currently require review.")

else:
    for item in pending_items:
        iid = item.get("intervention_id")
        eid = item.get("employee_id")
        current_status = item.get("status", "")
        intervention_type = item.get("intervention_type", "")
        cost = float(item.get("cost_usd") or 0)
        notes = item.get("hr_notes") or "No HR notes provided."

        with st.expander(
            f"{iid} | {eid} | {intervention_type} | {current_status}"
        ):
            col_d1, col_d2 = st.columns([3, 2])

            with col_d1:
                st.markdown(f"**Employee:** `{eid}`")
                st.markdown(f"**Intervention:** `{intervention_type}`")
                st.markdown(f"**Estimated Cost:** `${cost:,.2f}`")
                st.markdown(f"**Current Status:** `{current_status}`")
                st.markdown("**HR Notes:**")
                st.write(notes)

            with col_d2:
                st.markdown("**Human Reviewer Decision**")

                reviewer_notes = st.text_area(
                    "Decision Notes",
                    key=f"review_notes_{iid}",
                    placeholder="Enter at least 5 characters explaining the decision.",
                )

                allowed = ALLOWED_TRANSITIONS.get(current_status, [])

                if not allowed:
                    st.caption(
                        "No supported lifecycle transition is available."
                    )
                    continue

                selected_target = st.selectbox(
                    "Next Status",
                    allowed,
                    key=f"review_target_{iid}",
                )

                if st.button(
                    "Submit Decision",
                    key=f"review_submit_{iid}",
                    type="primary",
                ):
                    if len(reviewer_notes.strip()) < 5:
                        st.error(
                            "Please provide reviewer notes with at least 5 characters."
                        )
                    else:
                        result = api_client.transition_intervention(
                            intervention_id=iid,
                            target_status=selected_target,
                            reason=reviewer_notes.strip(),
                            actor_id="USR-HR-LEAD",
                        )

                        if result:
                            st.success(
                                f"{iid} updated to {selected_target}."
                            )
                            load_all_interventions.clear()
                            st.rerun()
                        else:
                            st.error(
                                "The transition failed. Check the backend "
                                "response and current intervention status."
                            )


# ---------------------------------------------------------------------
# All interventions table
# ---------------------------------------------------------------------

st.markdown(
    "<div class='wiq-section-header'>"
    "All Interventions & Lifecycle Tracking"
    "</div>",
    unsafe_allow_html=True,
)

st.caption(
    f"Showing {len(items)} matching records "
    f"out of {len(all_items)} total interventions."
)

if items:
    table_rows = []

    for item in items:
        table_rows.append({
            "Intervention ID": item.get("intervention_id"),
            "Employee ID": item.get("employee_id"),
            "Employee Name": item.get("employee_name"),
            "Department": item.get("department_name"),
            "Intervention Type": item.get("intervention_type"),
            "Status": item.get("status"),
            "Budget (USD)": float(item.get("cost_usd") or 0),
            "Proposed Date": str(item.get("proposed_date") or ""),
            "Action Date": str(item.get("action_date") or ""),
            "Outcome Date": str(item.get("outcome_evaluated_date") or ""),
            "Successful": item.get("is_successful"),
        })

    df_interventions = pd.DataFrame(table_rows)

    st.dataframe(
        df_interventions,
        use_container_width=True,
        hide_index=True,
    )

else:
    st.info("No intervention records match the selected filters.")


# ---------------------------------------------------------------------
# Manual lifecycle transition
# ---------------------------------------------------------------------

st.markdown("#### Manual Lifecycle Transition")

if items:
    selectable_items = [
        item for item in items
        if ALLOWED_TRANSITIONS.get(item.get("status", ""), [])
    ]

    if selectable_items:
        item_lookup = {
            item["intervention_id"]: item
            for item in selectable_items
        }

        selected_iid = st.selectbox(
            "Select Intervention",
            list(item_lookup.keys()),
            format_func=lambda iid: (
                f"{iid} | {item_lookup[iid].get('status')} | "
                f"{item_lookup[iid].get('employee_id')}"
            ),
        )

        selected_item = item_lookup[selected_iid]
        current_status = selected_item.get("status", "")

        allowed_targets = ALLOWED_TRANSITIONS.get(
            current_status, []
        )

        col_t1, col_t2 = st.columns(2)

        with col_t1:
            new_state = st.selectbox(
                "Allowed Next Status",
                allowed_targets,
                key="manual_next_status",
            )

        with col_t2:
            transition_notes = st.text_input(
                "Reason / Reviewer Notes",
                key="manual_transition_notes",
                placeholder="Explain the reason for this transition.",
            )

        if st.button("Update Intervention Status"):
            if len(transition_notes.strip()) < 5:
                st.error("Please provide at least 5 characters of notes.")
            else:
                result = api_client.transition_intervention(
                    intervention_id=selected_iid,
                    target_status=new_state,
                    reason=transition_notes.strip(),
                    actor_id="USR-HR-LEAD",
                )

                if result:
                    st.success(
                        f"{selected_iid} updated to {new_state}."
                    )
                    load_all_interventions.clear()
                    st.rerun()
                else:
                    st.error(
                        "Transition failed. Verify the current status "
                        "and backend validation response."
                    )

    else:
        st.info(
            "No records in the current filtered results have an "
            "available lifecycle transition."
        )


# ---------------------------------------------------------------------
# Immutable audit event history
# ---------------------------------------------------------------------

st.markdown("#### Intervention Audit History")

if items:
    audit_ids = [
        item.get("intervention_id")
        for item in items
        if item.get("events")
    ]

    if audit_ids:
        selected_audit_id = st.selectbox(
            "Select Intervention Audit Trail",
            audit_ids,
            key="audit_intervention_select",
        )

        audit_item = next(
            item for item in items
            if item.get("intervention_id") == selected_audit_id
        )

        events = audit_item.get("events", [])

        audit_rows = [
            {
                "Event ID": event.get("event_id"),
                "Previous Status": event.get("from_status") or "—",
                "New Status": event.get("to_status"),
                "Actor": event.get("actor"),
                "Notes": event.get("notes"),
                "Recorded At": str(event.get("recorded_at") or ""),
            }
            for event in events
        ]

        if audit_rows:
            st.dataframe(
                pd.DataFrame(audit_rows),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No audit events are available for this record.")
    else:
        st.info("No audit event history is available in the filtered records.")


# ---------------------------------------------------------------------
# Create a new intervention
# ---------------------------------------------------------------------

st.markdown(
    "<div class='wiq-section-header'>Propose New Intervention</div>",
    unsafe_allow_html=True,
)

with st.expander("Open New Intervention Entry Form"):
    with st.form("new_intervention_form"):
        col_n1, col_n2 = st.columns(2)

        with col_n1:
            new_employee_id = st.text_input(
                "Target Employee ID",
                placeholder="e.g. EMP-000001",
            )

            new_type = st.selectbox(
                "Intervention Type",
                INTERVENTION_TYPES,
            )

            new_risk_score_id = st.text_input(
                "Risk Score ID (Optional)",
                placeholder="Leave blank if not applicable",
            )

        with col_n2:
            new_cost = st.number_input(
                "Proposed Budget (USD)",
                min_value=0.0,
                value=750.0,
                step=100.0,
            )

            new_hr_notes = st.text_area(
                "HR Notes / Justification",
                placeholder=(
                    "Describe the proposed retention action, "
                    "business rationale, and intended outcome."
                ),
            )

        submit_new = st.form_submit_button(
            "Submit Intervention",
            type="primary",
        )

        if submit_new:
            if not new_employee_id.strip():
                st.error("Employee ID is required.")
            elif not new_hr_notes.strip():
                st.error("Please provide HR notes for the intervention.")
            else:
                payload = {
                    "employee_id": new_employee_id.strip(),
                    "intervention_type": new_type,
                    "cost_usd": float(new_cost),
                    "hr_notes": new_hr_notes.strip(),
                }

                if new_risk_score_id.strip():
                    payload["risk_score_id"] = new_risk_score_id.strip()

                result = api_client.propose_intervention(payload)

                if result:
                    st.success(
                        f"Intervention "
                        f"`{result.get('intervention_id', 'created')}` "
                        "submitted successfully."
                    )
                    load_all_interventions.clear()
                    st.rerun()
                else:
                    st.error(
                        "Intervention creation failed. Verify the "
                        "employee ID, risk score ID, and backend response."
                    )
