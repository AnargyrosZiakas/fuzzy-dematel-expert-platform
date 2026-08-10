"""Research description, instructions, scale, and criteria reference."""

from __future__ import annotations

from html import escape

import streamlit as st

from components.layout import navigation_buttons, page_header
from config import (
    SCALE_ITEMS,
    ResearchSettings,
    load_hierarchical_factor_catalogue,
)
from research_content import (
    CONTACT_EMAIL,
    DIRECT_INFLUENCE_REMINDER,
    DOCTORAL_RESEARCH_TITLE,
    INVITATION_PARAGRAPHS,
    METHOD_PURPOSE_PARAGRAPHS,
    RESEARCHER_NAME,
    RESEARCHER_ROLE,
)


def _paragraphs_html(paragraphs: tuple[str, ...]) -> str:
    return "".join(f"<p>{escape(paragraph)}</p>" for paragraph in paragraphs)


def _render_scale() -> None:
    rows = "".join(
        "<tr>"
        f"<td><strong>{item.code}</strong></td>"
        f"<td>{escape(item.label)}</td>"
        "</tr>"
        for item in SCALE_ITEMS
    )
    st.markdown(
        "<div class='table-scroll'><table class='research-table'>"
        "<thead><tr><th>Code</th><th>Influence judgement</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def _render_factor_catalogue() -> None:
    catalogue = load_hierarchical_factor_catalogue()
    dimensions = dict.fromkeys(item.dimension for item in catalogue)
    for dimension in dimensions:
        with st.expander(str(dimension), expanded=False):
            rows = []
            for item in catalogue:
                if item.dimension != dimension:
                    continue
                rows.append(
                    "<div class='factor-definition-row'>"
                    f"<div><span class='factor-badge'>{escape(item.code)}</span>"
                    f"<strong>{escape(item.criterion)}</strong></div>"
                    f"<div>{escape(item.definition)}</div></div>"
                )
            st.markdown(
                f"<div class='factor-catalogue'>{''.join(rows)}</div>",
                unsafe_allow_html=True,
            )


def render() -> None:
    """Present the approved academic information in digestible sections."""

    settings = ResearchSettings.from_environment()
    page_header(
        "Step 2 of 6",
        "Research information and instructions",
        settings.research_description,
    )
    st.markdown(
        f"""
        <div class="content-card">
          <p class="eyebrow">PhD research</p>
          <p class="study-title">“{escape(DOCTORAL_RESEARCH_TITLE)}”</p>
          <p><strong>{escape(RESEARCHER_NAME)}</strong><br>
          {escape(RESEARCHER_ROLE)}<br>
          Department of Tourism Economics and Management</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    about_column, task_column = st.columns(2)
    with about_column:
        st.markdown(
            "<div class='content-card'><h3>About the study</h3>"
            f"{_paragraphs_html(METHOD_PURPOSE_PARAGRAPHS[:1])}"
            "<p>The study examines causal relationships among cultural, economic "
            "and airline strategic factors in sustainable aviation.</p></div>",
            unsafe_allow_html=True,
        )
    with task_column:
        st.markdown(
            "<div class='content-card'><h3>What you will do</h3>"
            "<p>Complete four matrices in sequence:</p><ol>"
            "<li>Consumer-Cultural &amp; Behavioural</li>"
            "<li>Economic &amp; Market</li>"
            "<li>Airline Strategic &amp; Operational</li>"
            "<li>Relationships Between Dimensions</li></ol>"
            "<p>Only direct influence within each criterion group is evaluated. "
            "Each direction is separate.</p></div>",
            unsafe_allow_html=True,
        )

    st.subheader("How to answer")
    st.markdown(
        "<div class='orientation-card'>Please indicate how much the "
        "<strong>ROW factor</strong> influences the "
        "<strong>COLUMN factor</strong>.<div class='orientation-roles'>"
        "<span>ROW = CAUSE</span><span>COLUMN = AFFECTED FACTOR</span>"
        "</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='privacy-note'><strong>Direct influence</strong><br>"
        f"{escape(DIRECT_INFLUENCE_REMINDER)}</div>",
        unsafe_allow_html=True,
    )

    scale_column, details_column = st.columns(2)
    with scale_column:
        st.markdown("### Fuzzy DEMATEL scale")
        _render_scale()
        st.caption(
            "The mathematical fuzzy values are stored automatically; you only "
            "select the linguistic judgement."
        )
    with details_column:
        st.markdown(
            "<div class='content-card'><h3>Confidentiality</h3>"
            f"{_paragraphs_html(INVITATION_PARAGRAPHS[4:6])}"
            f"<p>Questions: <a href='mailto:{escape(CONTACT_EMAIL)}'>"
            f"{escape(CONTACT_EMAIL)}</a></p></div>",
            unsafe_allow_html=True,
        )
        st.write("")
        st.markdown(
            "<div class='content-card'><h3>Progress and review</h3>"
            "<p>Progress is saved after every selection. All four sections can "
            "be revisited and reviewed before submission.</p></div>",
            unsafe_allow_html=True,
        )

    st.subheader("Criteria reference")
    st.caption(
        "Definitions are also available inside every matrix through tooltips and "
        "the section reference panel."
    )
    _render_factor_catalogue()
    navigation_buttons(previous_page=0, next_page=2, key_prefix="research")
