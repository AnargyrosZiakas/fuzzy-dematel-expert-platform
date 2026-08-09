"""Refresh-safe progress restoration for the hierarchical questionnaire."""

from __future__ import annotations

import logging
from uuid import UUID

import streamlit as st

from database import AssignmentError, DatabaseConfigurationError
from hierarchical_questionnaire import matrix_definitions
from services import get_repository

LOGGER = logging.getLogger(__name__)


def _first_incomplete_matrix(judgments: dict[str, str]) -> int:
    """Return the first matrix containing an unanswered relationship."""

    for index, matrix in enumerate(matrix_definitions()):
        required = matrix.required_comparisons
        completed = sum(
            key.startswith(f"{matrix.id}|") for key in judgments
        )
        if completed < required:
            return index
    return len(matrix_definitions()) - 1


def restore_progress_from_query() -> None:
    """Restore an assignment from its anonymous URL token once per session."""

    if st.session_state.get("progress_restore_attempted"):
        return
    st.session_state["progress_restore_attempted"] = True

    raw_respondent_id = st.query_params.get("respondent")
    if not raw_respondent_id:
        return
    try:
        respondent_id = UUID(str(raw_respondent_id))
    except ValueError:
        st.session_state["resume_error"] = (
            "The saved-progress link is invalid. Start a new questionnaire."
        )
        return

    try:
        repository = get_repository()
        assignment = repository.load_questionnaire(respondent_id)
        if assignment is None:
            legacy = repository.load_legacy_assignment(respondent_id)
            if legacy is None:
                st.session_state["resume_error"] = (
                    "No saved questionnaire was found for this link."
                )
                return
            assignment = repository.start_questionnaire(
                respondent_id, legacy["expert_code"]
            )
            st.session_state["resume_error"] = (
                "This saved link used the earlier pilot questionnaire. A fresh "
                "hierarchical questionnaire has been opened; historical pilot "
                "answers remain preserved separately."
            )
        responses = repository.load_responses(respondent_id)
    except (DatabaseConfigurationError, AssignmentError) as exc:
        LOGGER.warning("Progress restoration failed: %s", exc)
        st.session_state["resume_error"] = str(exc)
        return

    judgments = {
        (
            f"{record['matrix_id']}|{record['source_code']}|"
            f"{record['target_code']}"
        ): record["linguistic_value"]
        for record in responses
    }
    st.session_state.update(
        {
            "respondent_id": str(respondent_id),
            "questionnaire": dict(assignment),
            "expert_code": assignment["expert_code"],
            "expert_code_input": assignment["expert_code"],
            "consent_given": True,
            "consent_checkbox": True,
            "judgments": judgments,
            "current_matrix_index": _first_incomplete_matrix(judgments),
            "submitted": assignment["status"] == "completed",
            "current_page": 5 if assignment["status"] == "completed" else 4,
        }
    )
