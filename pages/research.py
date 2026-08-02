"""Research description step."""

from __future__ import annotations

import streamlit as st

from components.layout import navigation_buttons, page_header
from config import ResearchSettings


def render() -> None:
    """Explain the study purpose and what participation involves."""

    settings = ResearchSettings.from_environment()
    page_header(
        "Step 2 of 6",
        "About this research",
        settings.research_description,
    )
    left, right = st.columns([1.35, 1])
    with left:
        st.markdown(
            """
            <div class="content-card">
              <h3>What your expertise contributes</h3>
              <p>Fuzzy DEMATEL is designed to examine cause-and-effect structure in
              complex systems. Your linguistic assessments preserve uncertainty by
              being encoded as triangular fuzzy numbers.</p>
              <p>The analysis is directional. For each ordered pair, consider the
              direct influence of the row factor on the column factor—not whether the
              factors are merely associated.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            """
            <div class="content-card">
              <h3>What you will do</h3>
              <ol>
                <li>Review the informed-consent information.</li>
                <li>Enter a non-identifying expert code.</li>
                <li>Complete all 306 directed comparisons.</li>
                <li>Review and submit the complete matrix once.</li>
              </ol>
              <p>You may move back before submission without losing completed
              entries.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    navigation_buttons(
        previous_page=0,
        next_page=2,
        key_prefix="research",
    )
