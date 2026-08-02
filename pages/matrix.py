"""Fixed influence-matrix step."""

from __future__ import annotations

import streamlit as st

from components.layout import navigation_buttons, page_header
from components.matrix_grid import render_matrix_grid, render_scale_legend
from config import REQUIRED_COMPARISONS
from research_content import DIRECT_INFLUENCE_REMINDER
from validation import validate_expert_code, validate_matrix


def render() -> None:
    """Render and validate all directed factor comparisons."""

    code_is_valid, _, _ = validate_expert_code(st.session_state["expert_code"])
    if not st.session_state["consent_given"] or not code_is_valid:
        st.warning("Complete the consent and anonymous-code steps first.")
        navigation_buttons(
            previous_page=3,
            next_page=None,
            key_prefix="matrix_guard",
        )
        return

    status = validate_matrix(st.session_state["judgments"])
    page_header(
        "Step 5 of 6",
        "Direct influence matrix",
        (
            "For every editable cell, assess how much the row factor directly "
            "influences the column factor. Hover over any factor code for its "
            "full definition."
        ),
    )
    st.markdown(
        "<div class='orientation-card'>How much does the "
        "<strong>ROW factor</strong> influence the "
        "<strong>COLUMN factor</strong>?</div>",
        unsafe_allow_html=True,
    )
    render_scale_legend()
    st.write("")
    st.progress(
        status.completion_ratio,
        text=f"Completed comparisons: {status.completed} / {REQUIRED_COMPARISONS}",
    )
    st.caption(
        "The 18 diagonal cells are disabled and fixed at 0. Scroll "
        "horizontally if needed."
    )
    st.info(DIRECT_INFLUENCE_REMINDER)
    render_matrix_grid()

    status = validate_matrix(st.session_state["judgments"])
    st.write("")
    st.progress(
        status.completion_ratio,
        text=f"Completed comparisons: {status.completed} / {REQUIRED_COMPARISONS}",
    )
    if status.is_valid:
        st.success(
            "All 306 required comparisons are complete. You may review and submit."
        )
    else:
        st.info(
            f"Complete the remaining {len(status.missing)} comparison(s) before "
            "continuing."
        )
    navigation_buttons(
        previous_page=3,
        next_page=5,
        next_label="Review submission",
        next_disabled=not status.is_valid,
        key_prefix="matrix",
    )
