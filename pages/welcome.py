"""Welcome step."""

from __future__ import annotations

import streamlit as st

from components.layout import navigation_buttons, page_header
from config import HIERARCHICAL_REQUIRED_COMPARISONS, MATRIX_SIZE
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
          <p>You will complete four short, clearly separated Fuzzy DEMATEL matrices:
          three criterion-level sections followed by relationships among the three
          research dimensions.</p>
          <div class="orientation-card">Please indicate how much the
          <strong>ROW factor</strong> influences the
          <strong>COLUMN factor</strong>.</div>
          <p>Each direction is evaluated separately. Cross-dimensional individual
          criterion pairs are not asked, and every saved answer can be recovered
          using your anonymous progress link.</p>
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
        f"<div class='metric-number'>{HIERARCHICAL_REQUIRED_COMPARISONS}</div>"
        "<div class='metric-caption'>directed evaluations</div>",
        unsafe_allow_html=True,
    )
    third.markdown(
        "<div class='metric-number'>4</div>"
        f"<div class='metric-caption'>manageable sections · "
        f"{EXPECTED_COMPLETION_TIME}</div>",
        unsafe_allow_html=True,
    )
    navigation_buttons(
        previous_page=None,
        next_page=1,
        next_label="Begin",
        key_prefix="welcome",
    )
