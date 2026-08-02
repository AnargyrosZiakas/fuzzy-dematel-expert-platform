"""Refresh-safe respondent progress restoration."""

from __future__ import annotations

import logging
from uuid import UUID

import streamlit as st

from database import AssignmentError, DatabaseConfigurationError
from questionnaire_sets import get_questionnaire_set
from services import get_repository

LOGGER = logging.getLogger(__name__)


def _first_unanswered_index(set_id: int, judgments: dict[str, str]) -> int:
    relationships = get_questionnaire_set(set_id)
    for index, relationship in enumerate(relationships):
        if relationship.key not in judgments:
            return index
    return max(0, len(relationships) - 1)


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
        assignment = repository.load_assignment(respondent_id)
        if assignment is None:
            st.session_state["resume_error"] = (
                "No saved questionnaire was found for this link."
            )
            return
        responses = repository.load_responses(respondent_id)
    except (DatabaseConfigurationError, AssignmentError) as exc:
        LOGGER.warning("Progress restoration failed: %s", exc)
        st.session_state["resume_error"] = str(exc)
        return

    judgments = {
        f"{record['from_factor']}|{record['to_factor']}": record[
            "linguistic_value"
        ]
        for record in responses
    }
    set_id = int(assignment["set_id"])
    st.session_state.update(
        {
            "respondent_id": str(respondent_id),
            "assignment": dict(assignment),
            "assigned_set_id": set_id,
            "expert_code": assignment["expert_code"],
            "expert_code_input": assignment["expert_code"],
            "consent_given": True,
            "consent_checkbox": True,
            "judgments": judgments,
            "question_index": _first_unanswered_index(set_id, judgments),
            "submitted": assignment["status"] == "completed",
            "current_page": 5 if assignment["status"] == "completed" else 4,
        }
    )
