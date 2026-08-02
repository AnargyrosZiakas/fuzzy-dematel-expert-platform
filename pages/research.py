"""Research description, method, scale, and factor-catalogue step."""

from __future__ import annotations

from html import escape

import streamlit as st

from components.layout import navigation_buttons, page_header
from config import (
    CANNOT_ASSESS_VALUE,
    SCALE_ITEMS,
    ResearchSettings,
    load_factor_catalogue,
)
from research_content import (
    CONTACT_EMAIL,
    DIRECT_INFLUENCE_REMINDER,
    DOCTORAL_RESEARCH_TITLE,
    EVALUATION_INSTRUCTIONS,
    INVITATION_PARAGRAPHS,
    METHOD_PURPOSE_PARAGRAPHS,
    RESEARCHER_NAME,
    RESEARCHER_ROLE,
)

SCALE_EXPLANATIONS = (
    "No meaningful or only a negligible direct effect.",
    "A limited direct effect.",
    "A noticeable and moderate direct effect.",
    "A strong direct effect.",
    "A very strong or decisive direct effect.",
)


def _paragraphs_html(paragraphs: tuple[str, ...]) -> str:
    """Return trusted research copy as escaped HTML paragraphs."""

    return "".join(f"<p>{escape(paragraph)}</p>" for paragraph in paragraphs)


def _render_scale() -> None:
    """Render the five-level linguistic scale and exact TFN mapping."""

    rows = []
    for numerical_code, (item, explanation) in enumerate(
        zip(SCALE_ITEMS, SCALE_EXPLANATIONS, strict=True)
    ):
        rows.append(
            "<tr>"
            f"<td>{numerical_code}</td>"
            f"<td><strong>{item.code}</strong></td>"
            f"<td>{escape(item.label)}</td>"
            f"<td>{escape(explanation)}</td>"
            f"<td>({item.lower:.2f}, {item.modal:.2f}, {item.upper:.2f})</td>"
            "</tr>"
        )
    rows.append(
        "<tr>"
        "<td>—</td><td>—</td>"
        f"<td>{CANNOT_ASSESS_VALUE}</td>"
        "<td>Use only when a defensible professional judgement cannot be made.</td>"
        "<td>Not assigned</td>"
        "</tr>"
    )
    st.markdown(
        "<div class='table-scroll'><table class='research-table'>"
        "<thead><tr><th>Numerical code</th><th>Acronym</th>"
        "<th>Linguistic assessment</th><th>Explanation</th>"
        "<th>Triangular fuzzy number (TFN)</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def _render_factor_catalogue() -> None:
    """Render all criterion names and definitions in instrument order."""

    catalogue = load_factor_catalogue()
    dimensions = dict.fromkeys(item.dimension for item in catalogue)
    for dimension in dimensions:
        st.markdown(f"#### {escape(dimension)}")
        rows = []
        for item in catalogue:
            if item.dimension != dimension:
                continue
            rows.append(
                "<div class='factor-definition-row'>"
                f"<div><span class='factor-badge'>{escape(item.code)}</span>"
                f"<strong>{escape(item.criterion)}</strong></div>"
                f"<div>{escape(item.definition)}</div>"
                "</div>"
            )
        st.markdown(
            f"<div class='factor-catalogue'>{''.join(rows)}</div>",
            unsafe_allow_html=True,
        )


def render() -> None:
    """Explain the study, method, evaluation procedure, and all factors."""

    settings = ResearchSettings.from_environment()
    page_header(
        "Step 2 of 6",
        "Research information and instructions",
        settings.research_description,
    )

    invitation_intro = _paragraphs_html(INVITATION_PARAGRAPHS[:2])
    invitation_details = _paragraphs_html(INVITATION_PARAGRAPHS[2:])
    st.markdown(
        f"""
        <div class="content-card">
          <h3>Invitation to Participate</h3>
          {invitation_intro}
          <p class="study-title">“{escape(DOCTORAL_RESEARCH_TITLE)}”</p>
          {invitation_details}
          <p>For any questions regarding the research, please contact:<br>
          <strong>{escape(RESEARCHER_NAME)}</strong>, {escape(RESEARCHER_ROLE)}<br>
          <a href="mailto:{escape(CONTACT_EMAIL)}">{escape(CONTACT_EMAIL)}</a></p>
          <p>Thank you for your time and valuable contribution.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Purpose of the Method")
    purpose_html = _paragraphs_html(METHOD_PURPOSE_PARAGRAPHS)
    st.markdown(
        f"<div class='content-card'>{purpose_html}</div>",
        unsafe_allow_html=True,
    )

    st.subheader("How to Complete the Evaluation")
    st.markdown(_paragraphs_html(EVALUATION_INSTRUCTIONS), unsafe_allow_html=True)
    st.markdown(
        "<div class='orientation-card'>How much does the "
        "<strong>source variable</strong> directly influence the "
        "<strong>target variable</strong>?</div>",
        unsafe_allow_html=True,
    )

    st.subheader("Evaluation Scale")
    _render_scale()
    st.markdown(
        f"<div class='privacy-note'><strong>Important</strong><br>"
        f"{escape(DIRECT_INFLUENCE_REMINDER)}</div>",
        unsafe_allow_html=True,
    )

    st.subheader("Factors and Criteria")
    st.caption(
        "The complete study contains 18 factors. Each evaluation screen keeps the "
        "source and target codes visible and shows both variables' full definitions."
    )
    _render_factor_catalogue()

    navigation_buttons(
        previous_page=0,
        next_page=2,
        key_prefix="research",
    )
