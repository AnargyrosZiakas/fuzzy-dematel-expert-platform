"""Welcome step."""

from __future__ import annotations

import streamlit as st

from components.layout import navigation_buttons, page_header
from config import MATRIX_SIZE, REQUIRED_COMPARISONS


def render() -> None:
    """Render the study welcome and instrument overview."""

    page_header(
        "Expert evaluation · Fuzzy DEMATEL",
        "Map influence. Reveal structure.",
        (
            "Thank you for contributing your expert judgment to this PhD research. "
            "This instrument records the directed influence between every pair of "
            "study factors."
        ),
    )
    st.markdown(
        """
        <div class="hero-card">
          <h3>A complete scientific influence matrix</h3>
          <p>You will assess one precise question throughout the instrument:</p>
          <div class="orientation-card">How much does the <strong>ROW factor</strong>
          influence the <strong>COLUMN factor</strong>?</div>
          <p>Your responses are directional: C1 → C2 and C2 → C1 are separate
          judgments. No off-diagonal comparison is optional.</p>
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
        "<div class='metric-number'>5</div>"
        "<div class='metric-caption'>linguistic influence levels</div>",
        unsafe_allow_html=True,
    )
    navigation_buttons(
        previous_page=None,
        next_page=1,
        next_label="Begin",
        key_prefix="welcome",
    )
