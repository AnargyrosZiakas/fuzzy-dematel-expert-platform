"""One-question-at-a-time evaluation for an assigned relationship set."""

from __future__ import annotations

import logging
from uuid import UUID, uuid4

import streamlit as st

from components.layout import go_to_page, page_header
from components.matrix_grid import render_scale_legend
from components.relationship_question import render_relationship_question
from database import (
    AssignmentError,
    AutosaveError,
    DatabaseConfigurationError,
)
from models import DirectedRelationship
from questionnaire_sets import get_questionnaire_set
from research_content import DIRECT_INFLUENCE_REMINDER
from services import get_repository
from validation import (
    build_distributed_response_record,
    validate_assigned_responses,
    validate_expert_code,
)

LOGGER = logging.getLogger(__name__)


def _load_response_state(respondent_id: UUID) -> None:
    repository = get_repository()
    responses = repository.load_responses(respondent_id)
    st.session_state["judgments"] = {
        f"{record['from_factor']}|{record['to_factor']}": record[
            "linguistic_value"
        ]
        for record in responses
    }


def _ensure_assignment() -> bool:
    """Create one balanced assignment and durable resume URL when needed."""

    if st.session_state.get("assigned_set_id"):
        return True

    code_is_valid, normalized_code, code_message = validate_expert_code(
        st.session_state["expert_code"]
    )
    if not code_is_valid:
        st.error(code_message)
        return False

    raw_respondent_id = st.session_state.get("respondent_id")
    respondent_id = UUID(str(raw_respondent_id)) if raw_respondent_id else uuid4()
    try:
        repository = get_repository()
        with st.spinner("Assigning your balanced questionnaire set…"):
            assignment = repository.assign_respondent(
                respondent_id, normalized_code
            )
            _load_response_state(respondent_id)
    except (DatabaseConfigurationError, AssignmentError) as exc:
        st.error(str(exc))
        return False

    st.session_state.update(
        {
            "respondent_id": str(respondent_id),
            "assignment": dict(assignment),
            "assigned_set_id": int(assignment["set_id"]),
            "question_index": 0,
        }
    )
    st.query_params["respondent"] = str(respondent_id)
    return True


def _autosave_response(
    relationship: DirectedRelationship,
    widget_key: str,
) -> None:
    """Persist one selection and only then mark it complete locally."""

    value = st.session_state.get(widget_key)
    if not isinstance(value, str):
        return
    try:
        record = build_distributed_response_record(
            respondent_id=UUID(str(st.session_state["respondent_id"])),
            expert_code=st.session_state["expert_code"],
            relationship=relationship,
            linguistic_value=value,
        )
        get_repository().save_response(record)
    except (DatabaseConfigurationError, AutosaveError, ValueError) as exc:
        LOGGER.warning("Autosave failed for %s: %s", relationship.key, exc)
        st.session_state["autosave_error"] = str(exc)
        st.session_state["pending_relationship_key"] = relationship.key
        return

    judgments = dict(st.session_state["judgments"])
    judgments[relationship.key] = value
    st.session_state["judgments"] = judgments
    st.session_state["autosave_error"] = None
    st.session_state["pending_relationship_key"] = None


def _retry_autosave(
    relationship: DirectedRelationship,
    widget_key: str,
) -> None:
    _autosave_response(relationship, widget_key)


def _change_question(delta: int, question_count: int) -> None:
    index = int(st.session_state.get("question_index", 0)) + delta
    st.session_state["question_index"] = min(question_count - 1, max(0, index))


def render() -> None:
    """Render one readable relationship at a time with immediate autosave."""

    code_is_valid, _, _ = validate_expert_code(st.session_state["expert_code"])
    if not st.session_state["consent_given"] or not code_is_valid:
        st.warning("Complete the consent and anonymous-code steps first.")
        st.button(
            "← Back to expert code",
            on_click=go_to_page,
            args=(3,),
        )
        return
    if not _ensure_assignment():
        st.button(
            "← Back to expert code",
            on_click=go_to_page,
            args=(3,),
        )
        return

    set_id = int(st.session_state["assigned_set_id"])
    relationships = get_questionnaire_set(set_id)
    question_count = len(relationships)
    index = min(
        question_count - 1,
        max(0, int(st.session_state.get("question_index", 0))),
    )
    st.session_state["question_index"] = index
    relationship = relationships[index]
    status = validate_assigned_responses(set_id, st.session_state["judgments"])

    page_header(
        "Step 5 of 6",
        "Direct influence evaluation",
        (
            f"Questionnaire set {set_id} contains {question_count} unique directed "
            "relationships. The complete 18×18 matrix is not shown."
        ),
    )
    st.markdown(f"**Question {index + 1} of {question_count}**")
    st.progress(
        (index + 1) / question_count,
        text=f"Question {index + 1} of {question_count}",
    )
    st.caption(
        f"Completed and saved: {status.completed} of {status.required} evaluations"
    )
    render_scale_legend()
    st.markdown(
        "<span class='scale-chip'><strong>Cannot Assess</strong> · "
        "Use only when a defensible judgement cannot be made</span>",
        unsafe_allow_html=True,
    )
    st.info(DIRECT_INFLUENCE_REMINDER)

    widget_key = (
        f"response_{relationship.set_id}_"
        f"{relationship.source_code}_{relationship.target_code}"
    )
    selected_value = st.session_state["judgments"].get(relationship.key)
    render_relationship_question(
        relationship,
        selected_value=selected_value,
        on_change=_autosave_response,
        on_change_args=(relationship, widget_key),
    )

    if (
        st.session_state.get("autosave_error")
        and st.session_state.get("pending_relationship_key") == relationship.key
    ):
        st.error(st.session_state["autosave_error"])
        st.button(
            "Retry saving this response",
            on_click=_retry_autosave,
            args=(relationship, widget_key),
            use_container_width=True,
        )
    elif relationship.key in st.session_state["judgments"]:
        st.markdown(
            "<p class='autosave-note'>✓ Saved automatically</p>",
            unsafe_allow_html=True,
        )

    current_is_saved = relationship.key in st.session_state["judgments"]
    previous_column, _, next_column = st.columns([1.25, 3, 1.5])
    with previous_column:
        st.button(
            "← Previous question",
            disabled=index == 0,
            on_click=_change_question,
            args=(-1, question_count),
            use_container_width=True,
        )
    with next_column:
        if index < question_count - 1:
            st.button(
                "Next question →",
                type="primary",
                disabled=not current_is_saved,
                on_click=_change_question,
                args=(1, question_count),
                use_container_width=True,
            )
        else:
            final_status = validate_assigned_responses(
                set_id, st.session_state["judgments"]
            )
            st.button(
                "Review responses",
                type="primary",
                disabled=not final_status.is_valid,
                on_click=go_to_page,
                args=(5,),
                use_container_width=True,
            )

    if status.is_valid and index < question_count - 1:
        st.success(
            "All assigned relationships are saved. Continue to the final question "
            "to review and submit."
        )
