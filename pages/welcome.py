"""Welcome step."""

from __future__ import annotations

import streamlit as st

from components.layout import navigation_buttons, page_header
from config import MATRIX_SIZE, QUESTIONNAIRE_SET_COUNT
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
          <p>The research covers a complete scientific influence matrix across all
          respondents. You will be automatically assigned one balanced subset and
          will assess one precise question throughout:</p>
          <div class="orientation-card">To what extent does the
          <strong>source variable</strong> influence the
          <strong>target variable</strong>?</div>
          <p>Your responses are directional: C1 → C2 and C2 → C1 are separate
          judgements. Your progress is saved automatically after each selection.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")
    first, second, third = st.columns(3)
    first.markdown(
        f"<div class='metric-number'>{MATRIX_SIZE}</div>"
        "<div class='metric-caption'>research variables</div>",
        unsafe_allow_html=True,
    )
    second.markdown(
        "<div class='metric-number'>43–44</div>"
        "<div class='metric-caption'>assigned evaluations</div>",
        unsafe_allow_html=True,
    )
    third.markdown(
        f"<div class='metric-number'>{QUESTIONNAIRE_SET_COUNT}</div>"
        f"<div class='metric-caption'>balanced sets · "
        f"{EXPECTED_COMPLETION_TIME}</div>",
        unsafe_allow_html=True,
    )
    navigation_buttons(
        previous_page=None,
        next_page=1,
        next_label="Begin",
        key_prefix="welcome",
    )
