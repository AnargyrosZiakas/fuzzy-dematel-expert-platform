"""Informed-consent step."""

from __future__ import annotations

import streamlit as st

from components.layout import navigation_buttons, page_header
from config import ResearchSettings


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
            <li><strong>Purpose:</strong> collect expert judgments for a PhD study
            using Fuzzy DEMATEL.</li>
            <li><strong>Task:</strong> complete all 306 directed, off-diagonal
            influence comparisons.</li>
            <li><strong>Voluntary participation:</strong> participation is voluntary.
            You may stop before final submission.</li>
            <li><strong>Data:</strong> do not provide your name, email, or other
            directly identifying information in the expert-code field.</li>
            <li><strong>Withdrawal:</strong> because the submitted matrix is linked
            only to an anonymous code, later withdrawal may require that code.</li>
            <li><strong>Contact:</strong> {settings.researcher_name} ·
            {settings.contact_email}</li>
            <li><strong>Ethics reference:</strong> {settings.ethics_reference}</li>
          </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")
    if "consent_checkbox" not in st.session_state:
        st.session_state["consent_checkbox"] = st.session_state["consent_given"]
    st.checkbox(
        "I have read the information above, I am eligible to participate, and I "
        "voluntarily consent to take part in this research.",
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
