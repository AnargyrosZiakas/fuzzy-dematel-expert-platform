"""Welcome step."""

from __future__ import annotations

import streamlit as st

from components.layout import navigation_buttons, page_header
from config import MATRIX_SIZE, REQUIRED_COMPARISONS
from research_content import (
    DOCTORAL_RESEARCH_TITLE,
    EXPECTED_COMPLETION_TIME,
    INSTITUTION_LINE,
)


def render() -> None:
    """Render the study welcome and instrument overview."""

    page_header(
        INSTITUTION_LINE,
        "Fuzzy DEMATEL Expert Evaluation",
        (
            "You are kindly invited to contribute your professional judgement to "
            "this doctoral research."
        ),
    )
    st.markdown(
        f"""
        <div class="hero-card">
          <h3>Invitation to participate</h3>
          <p>This expert evaluation forms part of the doctoral research entitled:</p>
          <p class="study-title">“{DOCTORAL_RESEARCH_TITLE}”</p>
          <p>The questionnaire uses a complete scientific influence matrix. You
          will assess one precise question throughout the instrument:</p>
          <div class="orientation-card">How much does the <strong>ROW factor</strong>
          influence the <strong>COLUMN factor</strong>?</div>
          <p>Your responses are directional: C1 → C2 and C2 → C1 are separate
          judgements. No off-diagonal comparison is optional.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")
    first, second, third = st.columns(3)
    first.markdown(
        f"<div class='metric-number'>{MATRIX_SIZE}×{MATRIX_SIZE}</div>"
        "<div class='metric-caption'>fixed matrix</div>",
        unsafe_allow_html=True,
    )
    second.markdown(
        f"<div class='metric-number'>{REQUIRED_COMPARISONS}</div>"
        "<div class='metric-caption'>expert comparisons</div>",
        unsafe_allow_html=True,
    )
    third.markdown(
        "<div class='metric-number'>≈10 min</div>"
        f"<div class='metric-caption'>{EXPECTED_COMPLETION_TIME}</div>",
        unsafe_allow_html=True,
    )
    navigation_buttons(
        previous_page=None,
        next_page=1,
        next_label="Begin",
        key_prefix="welcome",
    )
