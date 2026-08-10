"""Final review and atomic completion of the hierarchical questionnaire."""

from __future__ import annotations

import logging
from uuid import UUID

import pandas as pd
import streamlit as st

from components.layout import go_to_page, page_header
from config import HIERARCHICAL_REQUIRED_COMPARISONS
from database import AssignmentError, DatabaseConfigurationError, SubmissionError
from hierarchical_questionnaire import (
    all_hierarchical_relationships,
    matrix_definitions,
)
from research_content import CONTACT_EMAIL, THANK_YOU_MESSAGE
from services import get_repository
from validation import (
    validate_expert_code,
    validate_hierarchical_matrix,
    validate_hierarchical_questionnaire,
)

LOGGER = logging.getLogger(__name__)


def _return_to_matrix(index: int) -> None:
    st.session_state["current_matrix_index"] = index
    st.session_state["active_relationship_key"] = None
    go_to_page(4)


def _complete_submission() -> None:
    """Verify all 90 answers and complete the database session atomically."""

    respondent_id = st.session_state.get("respondent_id")
    if not respondent_id or not st.session_state.get("questionnaire"):
        st.error("Your questionnaire session is unavailable.")
        return
    status = validate_hierarchical_questionnaire(
        st.session_state.get("judgments", {})
    )
    if not status.is_valid:
        st.error(
            f"Submission is blocked: {len(status.missing)} required "
            "relationship(s) are incomplete."
        )
        return
    try:
        with st.spinner("Finalising your securely saved responses…"):
            questionnaire = get_repository().complete_questionnaire(
                UUID(str(respondent_id))
            )
    except (DatabaseConfigurationError, AssignmentError, SubmissionError) as exc:
        st.error(str(exc))
        return
    except Exception:
        LOGGER.exception("Unexpected hierarchical submission failure")
        st.error(
            "An unexpected error prevented final submission. Your answers remain "
            "saved; please retry."
        )
        return
    st.session_state["questionnaire"] = dict(questionnaire)
    st.session_state["submitted"] = True


def _review_dataframe() -> pd.DataFrame:
    judgments = st.session_state.get("judgments", {})
    return pd.DataFrame.from_records(
        {
            "Matrix": relationship.matrix_label,
            "Source": f"{relationship.source_code} — {relationship.source_name}",
            "Target": f"{relationship.target_code} — {relationship.target_name}",
            "Response": judgments.get(relationship.key, "Missing"),
        }
        for relationship in all_hierarchical_relationships()
    )


def render() -> None:
    """Render section-level validation, optional answer review, and submission."""

    questionnaire = st.session_state.get("questionnaire") or {}
    code_is_valid, _, _ = validate_expert_code(
        str(st.session_state.get("expert_code", ""))
    )
    if not questionnaire or not code_is_valid:
        page_header(
            "Step 6 of 6",
            "Review and submit",
            "A valid questionnaire session is required before submission.",
        )
        st.warning("Return to the evaluation to create or restore your session.")
        st.button("← Back to evaluation", on_click=go_to_page, args=(4,))
        return

    judgments = st.session_state.get("judgments", {})
    overall = validate_hierarchical_questionnaire(judgments)
    is_submitted = bool(st.session_state.get("submitted")) or (
        questionnaire.get("status") == "completed"
    )
    page_header(
        "Step 6 of 6",
        "Review and submit",
        (
            "Check each section below. Every selection has already been saved "
            "against your anonymous respondent ID."
        ),
    )

    if is_submitted:
        st.success("Your expert evaluation has been submitted successfully.")
        st.markdown("## Thank you for your contribution")
        st.markdown(
            f"<div class='content-card'>{THANK_YOU_MESSAGE}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='content-card'><strong>Submission receipt</strong><br>"
            f"Respondent ID: <code>{st.session_state['respondent_id']}</code><br>"
            "Questionnaire design: <strong>Hierarchical Fuzzy DEMATEL</strong><br>"
            f"Stored evaluations: <strong>{overall.completed}</strong></div>",
            unsafe_allow_html=True,
        )
        st.info("Keep the respondent ID if the study protocol permits later queries.")
        st.caption(
            "For research questions: Anargyros Ziakas, PhD Candidate, "
            f"University of the Aegean · {CONTACT_EMAIL}"
        )
        return

    st.progress(
        overall.completion_ratio,
        text=(
            f"Total · {overall.completed} / "
            f"{HIERARCHICAL_REQUIRED_COMPARISONS} completed"
        ),
    )
    for index, matrix in enumerate(matrix_definitions()):
        status = validate_hierarchical_matrix(matrix.id, judgments)
        with st.container(key=f"review_section_{matrix.id}"):
            label_column, status_column, action_column = st.columns([3, 1.1, 1.1])
            with label_column:
                st.markdown(f"**{matrix.label}**")
            with status_column:
                st.markdown(f"**{status.completed} / {status.required}**")
            with action_column:
                st.button(
                    "Review" if status.is_valid else "Complete",
                    key=f"review_return_{matrix.id}",
                    on_click=_return_to_matrix,
                    args=(index,),
                    use_container_width=True,
                )

    if overall.is_valid:
        st.success(
            "Validation passed: all 90 required directed relationships are saved."
        )
    else:
        st.warning(
            f"Complete the remaining {len(overall.missing)} relationship(s) before "
            "submitting. Use the section buttons above to return directly."
        )

    with st.expander("Review individual answers (optional)", expanded=False):
        st.dataframe(
            _review_dataframe(),
            hide_index=True,
            use_container_width=True,
            height=520,
        )

    st.markdown(
        "<div class='privacy-note'><strong>Final action</strong><br>"
        "Submitting marks this anonymous questionnaire complete. Saved answers "
        "cannot be changed afterwards.</div>",
        unsafe_allow_html=True,
    )
    st.write("")
    back_column, _, submit_column = st.columns([1.25, 3, 1.55])
    with back_column:
        st.button(
            "← Back to evaluation",
            on_click=_return_to_matrix,
            args=(3,),
            use_container_width=True,
        )
    with submit_column:
        st.button(
            "Submit expert evaluation",
            type="primary",
            disabled=not overall.is_valid,
            on_click=_complete_submission,
            use_container_width=True,
        )
