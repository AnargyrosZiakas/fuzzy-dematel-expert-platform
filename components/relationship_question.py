"""Readable single-relationship response control for distributed sets."""

from __future__ import annotations

from collections.abc import Callable
from html import escape

import streamlit as st

from config import (
    CANNOT_ASSESS_VALUE,
    RESPONSE_OPTIONS,
    SCALE_BY_CODE,
    load_factor_catalogue,
)
from models import DirectedRelationship


def format_response_option(value: str) -> str:
    """Return the complete participant-facing response label."""

    if value == CANNOT_ASSESS_VALUE:
        return CANNOT_ASSESS_VALUE
    item = SCALE_BY_CODE[value]
    return f"{item.code} — {item.label}"


def selected_response_acronym(value: str | None) -> str:
    """Return the persistent selected-state text or the clear placeholder."""

    return value if value in RESPONSE_OPTIONS else "Select"


def _definition_by_code() -> dict[str, str]:
    return {item.code: item.definition for item in load_factor_catalogue()}


def render_relationship_question(
    relationship: DirectedRelationship,
    *,
    selected_value: str | None,
    on_change: Callable[..., None] | None = None,
    on_change_args: tuple[object, ...] = (),
) -> str | None:
    """Render one directional prompt and return its current response."""

    definitions = _definition_by_code()
    widget_key = (
        f"response_{relationship.set_id}_"
        f"{relationship.source_code}_{relationship.target_code}"
    )
    if widget_key not in st.session_state and selected_value in RESPONSE_OPTIONS:
        st.session_state[widget_key] = selected_value

    st.markdown(
        f"""
        <div class="relationship-direction">
          <div class="variable-card source-card">
            <span class="variable-role">Source variable</span>
            <span class="variable-code">{escape(relationship.source_code)}</span>
            <strong>{escape(relationship.source_name)}</strong>
            <small>{escape(definitions[relationship.source_code])}</small>
          </div>
          <div class="direction-arrow" aria-hidden="true">→</div>
          <div class="variable-card target-card">
            <span class="variable-role">Target variable</span>
            <span class="variable-code">{escape(relationship.target_code)}</span>
            <strong>{escape(relationship.target_name)}</strong>
            <small>{escape(definitions[relationship.target_code])}</small>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"### To what extent does {relationship.source_name} "
        f"({relationship.source_code}) influence {relationship.target_name} "
        f"({relationship.target_code})?"
    )

    current_value = st.radio(
        "Select one response",
        RESPONSE_OPTIONS,
        index=(
            RESPONSE_OPTIONS.index(selected_value)
            if selected_value in RESPONSE_OPTIONS
            else None
        ),
        format_func=format_response_option,
        horizontal=True,
        key=widget_key,
        on_change=on_change,
        args=on_change_args,
    )
    display_value = selected_response_acronym(current_value)
    selected_class = " completed" if current_value in RESPONSE_OPTIONS else ""
    st.markdown(
        f"<div class='selected-response{selected_class}'>"
        "<span>Selected response</span>"
        f"<strong>{escape(display_value)}</strong></div>",
        unsafe_allow_html=True,
    )
    return current_value
