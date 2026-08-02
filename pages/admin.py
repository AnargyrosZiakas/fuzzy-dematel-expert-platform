"""Password-protected administrator coverage dashboard and exports."""

from __future__ import annotations

import logging

import streamlit as st

from components.layout import page_header
from database import AssignmentError, DatabaseConfigurationError
from export import (
    completed_responses_dataframe,
    generate_administrator_exports,
    relationship_coverage_dataframe,
    set_summary_dataframe,
)
from services import (
    administrator_password_is_configured,
    get_repository,
    minimum_evaluations,
    verify_administrator_password,
)

LOGGER = logging.getLogger(__name__)


def _authenticate() -> None:
    candidate = str(st.session_state.get("admin_password_input", ""))
    if verify_administrator_password(candidate):
        st.session_state["admin_authenticated"] = True
        st.session_state["admin_login_error"] = None
        st.session_state["admin_password_input"] = ""
    else:
        st.session_state["admin_login_error"] = "Incorrect administrator password."


def _logout() -> None:
    st.session_state["admin_authenticated"] = False


def _render_login() -> None:
    page_header(
        "Restricted access",
        "Administrator dashboard",
        "Enter the server-configured administrator password to continue.",
    )
    if not administrator_password_is_configured():
        st.error(
            "Administrator access is not configured. Add ADMIN_PASSWORD or "
            "ADMIN_PASSWORD_SHA256 to the encrypted Streamlit secrets."
        )
        return
    st.text_input(
        "Administrator password",
        type="password",
        key="admin_password_input",
        on_change=_authenticate,
    )
    if st.session_state.get("admin_login_error"):
        st.error(st.session_state["admin_login_error"])
    st.button("Sign in", type="primary", on_click=_authenticate)


def render() -> None:
    """Render secure coverage metrics and combined researcher downloads."""

    if not st.session_state.get("admin_authenticated"):
        _render_login()
        return

    page_header(
        "Restricted research administration",
        "Questionnaire coverage dashboard",
        (
            "Monitor balanced-set completion and relationship-level coverage. "
            "Partial respondents are excluded from analysis counts and exports."
        ),
    )
    st.button("Sign out", on_click=_logout)

    try:
        with st.spinner("Loading research coverage…"):
            repository = get_repository()
            assignments = repository.fetch_all_assignments()
            responses = repository.fetch_all_responses()
    except (DatabaseConfigurationError, AssignmentError) as exc:
        LOGGER.warning("Administrator dashboard load failed: %s", exc)
        st.error(str(exc))
        return

    threshold = minimum_evaluations()
    completed = completed_responses_dataframe(responses, assignments)
    coverage = relationship_coverage_dataframe(
        completed,
        minimum_evaluations=threshold,
    )
    set_summary = set_summary_dataframe(assignments)
    insufficient = coverage[~coverage["enough_evaluations"]]
    completed_respondents = int(
        (set_summary["completed_respondents"]).sum()
    )

    first, second, third, fourth = st.columns(4)
    first.metric("Completed respondents", completed_respondents)
    second.metric("Completed evaluations", len(completed))
    third.metric("Covered relationships", int((coverage["evaluation_count"] > 0).sum()))
    fourth.metric(
        f"Below {threshold} usable evaluations",
        len(insufficient),
    )

    st.subheader("Completed responses per set")
    st.bar_chart(
        set_summary.set_index("set_id")["completed_respondents"],
        x_label="Questionnaire set",
        y_label="Completed respondents",
    )
    st.dataframe(
        set_summary,
        hide_index=True,
        use_container_width=True,
    )

    st.subheader("Directed-relationship coverage")
    st.caption(
        "Usable counts exclude ‘Cannot Assess’. Diagonal relationships are absent "
        "by design."
    )
    st.dataframe(
        coverage[
            [
                "set_id",
                "source_variable_code",
                "source_variable_name",
                "target_variable_code",
                "target_variable_name",
                "evaluation_count",
                "cannot_assess_count",
                "usable_evaluation_count",
                "enough_evaluations",
            ]
        ],
        hide_index=True,
        use_container_width=True,
        height=520,
    )

    st.subheader("Relationships needing more evaluations")
    if insufficient.empty:
        st.success(
            f"Every directed relationship has at least {threshold} usable evaluations."
        )
    else:
        st.warning(
            f"{len(insufficient)} relationships have fewer than {threshold} usable "
            "evaluations."
        )
        st.dataframe(
            insufficient[
                [
                    "set_id",
                    "source_variable_code",
                    "target_variable_code",
                    "usable_evaluation_count",
                    "minimum_required",
                ]
            ],
            hide_index=True,
            use_container_width=True,
            height=360,
        )

    exports = generate_administrator_exports(
        responses,
        assignments,
        minimum_evaluations=threshold,
    )
    st.subheader("Combined research export")
    st.caption(
        "The long-form response file plus the relationship map can reconstruct the "
        "complete 18×18 direct-relation design. No mathematical aggregation is "
        "performed."
    )
    csv_column, excel_column = st.columns(2)
    with csv_column:
        st.download_button(
            "Download all completed responses (CSV)",
            exports.responses_csv,
            file_name="fuzzy_dematel_all_responses.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with excel_column:
        st.download_button(
            "Download complete research workbook (Excel)",
            exports.complete_excel,
            file_name="fuzzy_dematel_complete_dataset.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
