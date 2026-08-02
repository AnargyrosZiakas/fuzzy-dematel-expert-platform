"""Final review and atomic completion of one assigned questionnaire set."""

from __future__ import annotations

import logging
from uuid import UUID

import pandas as pd
import streamlit as st

from components.layout import go_to_page, page_header
from database import (
    AssignmentError,
    DatabaseConfigurationError,
    SubmissionError,
)
from questionnaire_sets import get_questionnaire_set
from research_content import CONTACT_EMAIL, THANK_YOU_MESSAGE
from services import get_repository
from validation import validate_assigned_responses, validate_expert_code

LOGGER = logging.getLogger(__name__)


def _complete_submission() -> None:
    """Verify and atomically complete the respondent's assigned set."""

    set_id = st.session_state.get("assigned_set_id")
    respondent_id = st.session_state.get("respondent_id")
    if not set_id or not respondent_id:
        st.error("Your questionnaire assignment is unavailable.")
        return
    status = validate_assigned_responses(
        int(set_id), st.session_state["judgments"]
    )
    if not status.is_valid:
        st.error(
            f"Submission is blocked: {len(status.missing)} assigned "
            "relationship(s) are incomplete."
        )
        return

    try:
        with st.spinner("Finalising your securely saved responses…"):
            assignment = get_repository().complete_assignment(
                UUID(str(respondent_id))
            )
    except (
        DatabaseConfigurationError,
        AssignmentError,
        SubmissionError,
    ) as exc:
        st.error(str(exc))
        return
    except Exception:
        LOGGER.exception("Unexpected distributed submission failure")
        st.error(
            "An unexpected error prevented final submission. Your answers remain "
            "saved; please retry."
        )
        return

    st.session_state["assignment"] = dict(assignment)
    st.session_state["submitted"] = True


def _review_dataframe(set_id: int) -> pd.DataFrame:
    relationships = get_questionnaire_set(set_id)
    judgments = st.session_state["judgments"]
    return pd.DataFrame.from_records(
        {
            "Question": relationship.position,
            "Source": f"{relationship.source_code} — {relationship.source_name}",
            "Target": f"{relationship.target_code} — {relationship.target_name}",
            "Response": judgments.get(relationship.key, "Missing"),
        }
        for relationship in relationships
    )


def render() -> None:
    """Render validation, response review, completion, and receipt."""

    set_id = st.session_state.get("assigned_set_id")
    code_is_valid, _, _ = validate_expert_code(st.session_state["expert_code"])
    if not set_id or not code_is_valid:
        page_header(
            "Step 6 of 6",
            "Review and submit",
            "A valid questionnaire assignment is required before submission.",
        )
        st.warning("Return to the evaluation step to create or restore an assignment.")
        st.button(
            "← Back to evaluation",
            on_click=go_to_page,
            args=(4,),
        )
        return

    set_id = int(set_id)
    status = validate_assigned_responses(set_id, st.session_state["judgments"])
    assignment = st.session_state.get("assignment") or {}
    is_submitted = bool(st.session_state["submitted"]) or (
        assignment.get("status") == "completed"
    )

    page_header(
        "Step 6 of 6",
        "Review and submit",
        (
            f"Review questionnaire set {set_id}. Every selection has already been "
            "saved; final submission records one common completion timestamp."
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
            f"Questionnaire set: <strong>{set_id}</strong><br>"
            f"Stored evaluations: <strong>{status.completed}</strong></div>",
            unsafe_allow_html=True,
        )
        st.info(
            "Keep the respondent ID if the study protocol permits later queries."
        )
        st.caption(
            f"For any questions regarding the research: Anargyros Ziakas, "
            f"PhD Candidate, University of the Aegean · {CONTACT_EMAIL}"
        )
        return

    first, second, third = st.columns(3)
    first.metric("Questionnaire set", set_id)
    second.metric("Saved evaluations", f"{status.completed} / {status.required}")
    third.metric("Anonymous code", st.session_state["expert_code"])

    if status.is_valid:
        st.success("Validation passed. Your assigned response set is complete.")
    else:
        st.warning(
            f"Complete the remaining {len(status.missing)} relationship(s) before "
            "submitting."
        )

    with st.expander("Review all assigned responses", expanded=False):
        st.dataframe(
            _review_dataframe(set_id),
            hide_index=True,
            use_container_width=True,
        )

    st.markdown(
        "<div class='privacy-note'><strong>Final action</strong><br>"
        "Submitting marks this questionnaire set as complete. Your autosaved "
        "responses remain linked only to the anonymous respondent ID.</div>",
        unsafe_allow_html=True,
    )
    st.write("")
    back_column, _, submit_column = st.columns([1.2, 3, 1.5])
    with back_column:
        st.button(
            "← Back to evaluation",
            on_click=go_to_page,
            args=(4,),
            use_container_width=True,
        )
    with submit_column:
        st.button(
            "Submit response set",
            type="primary",
            disabled=not status.is_valid,
            on_click=_complete_submission,
            use_container_width=True,
        )
