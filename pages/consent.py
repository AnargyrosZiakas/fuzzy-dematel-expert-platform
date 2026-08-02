"""Informed-consent step."""

from __future__ import annotations

import streamlit as st

from components.layout import navigation_buttons, page_header
from config import ResearchSettings
from research_content import ANONYMITY_REMINDER, CONSENT_STATEMENT


def _persist_consent() -> None:
    st.session_state["consent_given"] = bool(
        st.session_state.get("consent_checkbox", False)
    )


def render() -> None:
    """Present consent information and require an affirmative choice."""

    settings = ResearchSettings.from_environment()
    page_header(
        "Step 3 of 6",
        "Informed consent",
        "Please read each point before deciding whether to participate.",
    )
    st.markdown(
        f"""
        <div class="content-card">
          <h3>Participation information</h3>
          <ul>
            <li><strong>Purpose:</strong> collect expert judgements for doctoral
            research using Fuzzy DEMATEL.</li>
            <li><strong>Task:</strong> complete all 306 directed, off-diagonal
            influence comparisons.</li>
            <li><strong>Voluntary participation:</strong> participation is voluntary.
            You may leave at any time before submitting, without providing a reason
            or experiencing negative consequences.</li>
            <li><strong>Time:</strong> completion is expected to take approximately
            10 minutes.</li>
            <li><strong>Anonymity:</strong> you will not be asked for your name,
            email address, employer or other directly identifying information.</li>
            <li><strong>Confidentiality:</strong> responses are used exclusively for
            academic research and accessed only by the researcher and, where
            academically necessary, the supervisory team.</li>
            <li><strong>Contact:</strong> {settings.researcher_name} ·
            {settings.contact_email}</li>
          </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")
    st.markdown(
        f"<div class='privacy-note'><strong>Privacy reminder</strong><br>"
        f"{ANONYMITY_REMINDER}</div>",
        unsafe_allow_html=True,
    )
    st.write("")
    if "consent_checkbox" not in st.session_state:
        st.session_state["consent_checkbox"] = st.session_state["consent_given"]
    st.checkbox(
        CONSENT_STATEMENT,
        key="consent_checkbox",
        on_change=_persist_consent,
    )
    if not st.session_state["consent_given"]:
        st.info("Consent is required before the expert evaluation can begin.")
    navigation_buttons(
        previous_page=1,
        next_page=3,
        next_disabled=not bool(st.session_state["consent_given"]),
        key_prefix="consent",
    )
