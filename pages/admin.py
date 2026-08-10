"""Password-protected dashboard and exports for the hierarchical study."""

from __future__ import annotations

import logging

import streamlit as st

from components.layout import page_header
from config import HIERARCHICAL_REQUIRED_COMPARISONS
from database import AssignmentError, DatabaseConfigurationError
from export import (
    completed_hierarchical_responses_dataframe,
    generate_administrator_exports,
    generate_hierarchical_administrator_exports,
    hierarchical_coverage_dataframe,
    hierarchical_matrix_summary_dataframe,
    hierarchical_respondent_summary_dataframe,
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
    """Render questionnaire status, 90-pair coverage, and combined exports."""

    if not st.session_state.get("admin_authenticated"):
        _render_login()
        return

    page_header(
        "Restricted research administration",
        "Hierarchical questionnaire dashboard",
        (
            "Monitor completed respondents and relationship coverage across the "
            "four fixed matrices. Partial respondents are excluded from exports."
        ),
    )
    st.button("Sign out", on_click=_logout)

    try:
        with st.spinner("Loading research data…"):
            repository = get_repository()
            questionnaires = repository.fetch_all_questionnaires()
            responses = repository.fetch_all_responses()
    except (DatabaseConfigurationError, AssignmentError) as exc:
        LOGGER.warning("Administrator dashboard load failed: %s", exc)
        st.error(str(exc))
        return

    threshold = minimum_evaluations()
    completed = completed_hierarchical_responses_dataframe(
        responses, questionnaires
    )
    coverage = hierarchical_coverage_dataframe(
        completed, minimum_evaluations=threshold
    )
    respondent_summary = hierarchical_respondent_summary_dataframe(questionnaires)
    matrix_summary = hierarchical_matrix_summary_dataframe(completed)
    insufficient = coverage[~coverage["enough_evaluations"]]
    completed_respondents = sum(
        questionnaire["status"] == "completed"
        for questionnaire in questionnaires
    )

    first, second, third, fourth = st.columns(4)
    first.metric("Completed respondents", completed_respondents)
    second.metric("Completed evaluations", len(completed))
    third.metric(
        "Relationships evaluated",
        int((coverage["evaluation_count"] > 0).sum()),
    )
    fourth.metric(f"Below {threshold} evaluations", len(insufficient))

    st.subheader("Respondent status")
    if respondent_summary.empty:
        st.info("No hierarchical questionnaire sessions have been started yet.")
    else:
        status_counts = respondent_summary["status"].value_counts()
        st.bar_chart(status_counts)
        st.dataframe(
            respondent_summary,
            hide_index=True,
            use_container_width=True,
        )

    st.subheader("Evaluations collected by matrix")
    st.dataframe(matrix_summary, hide_index=True, use_container_width=True)

    st.subheader("Directed-relationship coverage")
    st.caption(
        "Each row is one allowed source → target relationship. Diagonal and "
        "cross-dimensional criterion pairs are absent by scientific design."
    )
    st.dataframe(
        coverage,
        hide_index=True,
        use_container_width=True,
        height=520,
    )

    st.subheader("Relationships needing more evaluations")
    if insufficient.empty:
        st.success(
            f"Every relationship has at least {threshold} completed evaluations."
        )
    else:
        st.warning(
            f"{len(insufficient)} of {HIERARCHICAL_REQUIRED_COMPARISONS} "
            "relationships have fewer than "
            f"{threshold} completed evaluations."
        )
        st.dataframe(
            insufficient[
                [
                    "matrix_id",
                    "source_code",
                    "target_code",
                    "evaluation_count",
                    "minimum_required",
                ]
            ],
            hide_index=True,
            use_container_width=True,
            height=360,
        )

    exports = generate_hierarchical_administrator_exports(
        responses,
        questionnaires,
        minimum_evaluations=threshold,
    )
    st.subheader("Hierarchical research export")
    st.caption(
        "The raw long-form rows preserve respondent ID, matrix, direction, "
        "linguistic value, TFN and timestamp. They reconstruct the 6×6, 4×4, "
        "7×7 and 3×3 matrices without inventing missing answers."
    )
    csv_column, excel_column = st.columns(2)
    with csv_column:
        st.download_button(
            "Download completed responses (CSV)",
            exports.responses_csv,
            file_name="fuzzy_dematel_hierarchical_responses.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with excel_column:
        st.download_button(
            "Download complete workbook (Excel)",
            exports.complete_excel,
            file_name="fuzzy_dematel_hierarchical_dataset.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            use_container_width=True,
        )

    with st.expander("Historical seven-set data", expanded=False):
        st.caption(
            "Records collected under the earlier pilot design remain separate and "
            "available here; they are never mixed with hierarchical responses."
        )
        try:
            legacy_assignments = repository.fetch_legacy_assignments()
            legacy_responses = repository.fetch_legacy_responses()
            legacy_exports = generate_administrator_exports(
                legacy_responses,
                legacy_assignments,
                minimum_evaluations=threshold,
            )
        except Exception as exc:  # pragma: no cover - remote legacy path
            LOGGER.warning("Historical export load failed: %s", exc)
            st.warning("Historical data could not be loaded right now.")
        else:
            if not legacy_assignments:
                st.info("No historical seven-set sessions were found.")
            else:
                legacy_csv, legacy_excel = st.columns(2)
                with legacy_csv:
                    st.download_button(
                        "Download historical CSV",
                        legacy_exports.responses_csv,
                        file_name="fuzzy_dematel_historical_sets.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                with legacy_excel:
                    st.download_button(
                        "Download historical Excel",
                        legacy_exports.complete_excel,
                        file_name="fuzzy_dematel_historical_sets.xlsx",
                        mime=(
                            "application/vnd.openxmlformats-officedocument."
                            "spreadsheetml.sheet"
                        ),
                        use_container_width=True,
                    )
