"""Step-by-step four-matrix hierarchical Fuzzy DEMATEL evaluation."""

from __future__ import annotations

import logging
from uuid import UUID, uuid4

import streamlit as st

from components.fuzzy_matrix import (
    render_criteria_reference,
    render_fuzzy_matrix,
    render_scale_reference,
)
from components.layout import go_to_page, page_header
from config import HIERARCHICAL_REQUIRED_COMPARISONS
from database import AssignmentError, AutosaveError, DatabaseConfigurationError
from hierarchical_questionnaire import matrix_definitions
from models import HierarchicalRelationship
from research_content import DIRECT_INFLUENCE_REMINDER
from services import get_repository
from validation import (
    build_hierarchical_response_record,
    validate_expert_code,
    validate_hierarchical_matrix,
    validate_hierarchical_questionnaire,
)

LOGGER = logging.getLogger(__name__)


def _load_response_state(respondent_id: UUID) -> None:
    responses = get_repository().load_responses(respondent_id)
    st.session_state["judgments"] = {
        (
            f"{record['matrix_id']}|{record['source_code']}|"
            f"{record['target_code']}"
        ): record["linguistic_value"]
        for record in responses
    }


def _ensure_questionnaire() -> bool:
    """Create one anonymous, refresh-safe hierarchical session when needed."""

    if st.session_state.get("questionnaire"):
        return True
    code_is_valid, normalized_code, code_message = validate_expert_code(
        str(st.session_state.get("expert_code", ""))
    )
    if not code_is_valid:
        st.error(code_message)
        return False

    raw_respondent_id = st.session_state.get("respondent_id")
    respondent_id = UUID(str(raw_respondent_id)) if raw_respondent_id else uuid4()
    try:
        repository = get_repository()
        with st.spinner("Preparing your secure questionnaire…"):
            questionnaire = repository.start_questionnaire(
                respondent_id, normalized_code
            )
            _load_response_state(respondent_id)
    except (DatabaseConfigurationError, AssignmentError) as exc:
        st.error(str(exc))
        return False

    st.session_state.update(
        {
            "respondent_id": str(respondent_id),
            "questionnaire": dict(questionnaire),
            "current_matrix_index": 0,
        }
    )
    st.query_params["respondent"] = str(respondent_id)
    return True


def _autosave_response(
    relationship: HierarchicalRelationship,
    widget_key: str,
) -> None:
    """Persist one scale choice before marking the cell complete locally."""

    value = st.session_state.get(widget_key)
    if not isinstance(value, str):
        return
    try:
        record = build_hierarchical_response_record(
            respondent_id=UUID(str(st.session_state["respondent_id"])),
            expert_code=str(st.session_state["expert_code"]),
            relationship=relationship,
            linguistic_value=value,
        )
        get_repository().save_response(record)
    except (DatabaseConfigurationError, AutosaveError, ValueError) as exc:
        LOGGER.warning("Autosave failed for %s: %s", relationship.key, exc)
        st.session_state["autosave_error"] = str(exc)
        st.session_state["pending_relationship_key"] = relationship.key
        return

    judgments = dict(st.session_state.get("judgments", {}))
    judgments[relationship.key] = value
    st.session_state["judgments"] = judgments
    st.session_state["autosave_error"] = None
    st.session_state["pending_relationship_key"] = None


def _change_matrix(index: int) -> None:
    matrices = matrix_definitions()
    st.session_state["current_matrix_index"] = min(
        len(matrices) - 1, max(0, index)
    )
    st.session_state["active_relationship_key"] = None


def _continue_from_matrix(index: int) -> None:
    if index < len(matrix_definitions()) - 1:
        _change_matrix(index + 1)
    else:
        go_to_page(5)


def render() -> None:
    """Render exactly one of the four manageable matrix stages."""

    code_is_valid, _, _ = validate_expert_code(
        str(st.session_state.get("expert_code", ""))
    )
    if not st.session_state.get("consent_given") or not code_is_valid:
        st.warning("Complete the consent and anonymous-code steps first.")
        st.button("← Back to expert code", on_click=go_to_page, args=(3,))
        return
    if not _ensure_questionnaire():
        st.button("← Back to expert code", on_click=go_to_page, args=(3,))
        return

    matrices = matrix_definitions()
    index = min(
        len(matrices) - 1,
        max(0, int(st.session_state.get("current_matrix_index", 0))),
    )
    st.session_state["current_matrix_index"] = index
    matrix = matrices[index]
    judgments = st.session_state["judgments"]
    matrix_status = validate_hierarchical_matrix(matrix.id, judgments)
    overall_status = validate_hierarchical_questionnaire(judgments)
    overall_percent = round(overall_status.completion_ratio * 100)

    page_header(
        "Step 5 of 6 · Hierarchical evaluation",
        matrix.label,
        (
            f"Matrix {index + 1} of {len(matrices)} · "
            f"{matrix.required_comparisons} directed relationships"
        ),
    )
    st.markdown(
        "<div class='matrix-step-card'>"
        f"<strong>Step {index + 1} of 4</strong>"
        f"<span>{escape_label(matrix.short_label)}</span></div>",
        unsafe_allow_html=True,
    )
    st.progress(
        overall_status.completion_ratio,
        text=(
            f"Research progress · {overall_status.completed} of "
            f"{HIERARCHICAL_REQUIRED_COMPARISONS} saved ({overall_percent}%)"
        ),
    )
    st.markdown(
        f"**Current matrix:** {matrix_status.completed} of "
        f"{matrix_status.required} relationships completed"
    )
    st.progress(matrix_status.completion_ratio)

    st.markdown(
        "<div class='orientation-card matrix-orientation'>"
        "Please indicate how much the <strong>ROW factor</strong> influences the "
        "<strong>COLUMN factor</strong>.<div class='orientation-roles'>"
        "<span>ROW = CAUSE</span><span>COLUMN = AFFECTED FACTOR</span>"
        "</div></div>",
        unsafe_allow_html=True,
    )
    st.info(DIRECT_INFLUENCE_REMINDER)
    st.caption(
        "For the best matrix experience, a tablet or desktop computer is "
        "recommended. Mobile users can scroll horizontally."
    )
    render_scale_reference()
    render_criteria_reference(matrix)
    active = render_fuzzy_matrix(
        matrix,
        judgments=judgments,
        on_change=_autosave_response,
    )

    if (
        st.session_state.get("autosave_error")
        and st.session_state.get("pending_relationship_key") == active.key
    ):
        st.error(str(st.session_state["autosave_error"]))
        widget_key = (
            f"scale_selector_{active.matrix_id}_{active.source_code}_"
            f"{active.target_code}"
        )
        st.button(
            "Retry saving this response",
            on_click=_autosave_response,
            args=(active, widget_key),
            use_container_width=True,
        )
    elif active.key in st.session_state["judgments"]:
        st.markdown(
            "<p class='autosave-note'>✓ Saved automatically</p>",
            unsafe_allow_html=True,
        )

    if matrix_status.is_valid:
        st.success(f"{matrix.label} is complete and safely saved.")
    elif matrix_status.completed:
        st.caption(
            f"{len(matrix_status.missing)} relationship(s) remain in this matrix."
        )

    previous_column, _, next_column = st.columns([1.35, 3, 1.5])
    with previous_column:
        if index == 0:
            st.button(
                "← Expert code",
                on_click=go_to_page,
                args=(3,),
                use_container_width=True,
            )
        else:
            st.button(
                "← Previous matrix",
                on_click=_change_matrix,
                args=(index - 1,),
                use_container_width=True,
            )
    with next_column:
        st.button(
            "Review questionnaire" if index == 3 else "Continue →",
            type="primary",
            on_click=_continue_from_matrix,
            args=(index,),
            use_container_width=True,
        )


def escape_label(value: str) -> str:
    """Escape a matrix label used in a small trusted HTML fragment."""

    from html import escape

    return escape(value)
