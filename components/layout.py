"""Shared application layout, styling, and guarded step navigation."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from config import APP_TITLE, REQUIRED_COMPARISONS
from validation import validate_matrix

PAGE_LABELS = (
    "Welcome",
    "Research",
    "Consent",
    "Expert code",
    "Influence matrix",
    "Submit",
)


def initialize_session_state() -> None:
    """Initialize durable values that must survive Streamlit widget cleanup."""

    defaults: dict[str, object] = {
        "current_page": 0,
        "consent_given": False,
        "expert_code": "",
        "judgments": {},
        "submitted": False,
        "submitted_records": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def inject_global_styles() -> None:
    """Apply an accessible research-oriented visual system."""

    st.markdown(
        """
        <style>
        :root {
            --ink: #102A43;
            --navy: #163A5F;
            --teal: #0F766E;
            --teal-soft: #E6F4F1;
            --gold: #C8912E;
            --paper: #F7F9FC;
            --line: #D9E2EC;
        }
        .stApp { background: var(--paper); color: var(--ink); }
        [data-testid="stHeader"] { background: transparent; }
        .block-container { max-width: 1500px; padding-top: 2rem; }
        h1, h2, h3 { color: var(--ink); letter-spacing: -0.02em; }
        h1 { font-weight: 720; }
        .eyebrow {
            color: var(--teal); font-size: 0.78rem; font-weight: 750;
            letter-spacing: 0.12em; text-transform: uppercase;
        }
        .hero-card, .content-card {
            background: #FFFFFF; border: 1px solid var(--line);
            border-radius: 18px; padding: 1.4rem 1.5rem;
            box-shadow: 0 10px 30px rgba(16, 42, 67, 0.06);
        }
        .hero-card { border-top: 4px solid var(--teal); }
        .study-title {
            color: var(--navy); font-size: 1.08rem; font-weight: 700;
            line-height: 1.55;
        }
        .orientation-card {
            background: var(--navy); color: #FFFFFF; border-radius: 16px;
            padding: 1rem 1.2rem; text-align: center; margin: 1rem 0;
        }
        .orientation-card strong { color: #A7F3D0; }
        .scale-chip {
            display: inline-block; background: var(--teal-soft); color: #134E4A;
            border: 1px solid #B7DDD7; border-radius: 999px;
            padding: 0.3rem 0.65rem; margin: 0.15rem 0.2rem 0.15rem 0;
            font-size: 0.82rem; white-space: nowrap;
        }
        .metric-number { font-size: 2.1rem; font-weight: 760; color: var(--navy); }
        .metric-caption { color: #526D82; margin-top: -0.3rem; }
        .privacy-note {
            background: #FFF8E8; border-left: 4px solid var(--gold);
            border-radius: 8px; padding: 0.8rem 1rem;
        }
        .table-scroll { overflow-x: auto; margin: 0.75rem 0 1rem; }
        .research-table {
            width: 100%; border-collapse: collapse; background: #FFFFFF;
            border-radius: 12px; overflow: hidden;
        }
        .research-table th {
            background: var(--teal); color: #FFFFFF; text-align: left;
            padding: 0.7rem; white-space: nowrap;
        }
        .research-table td {
            border-bottom: 1px solid var(--line); padding: 0.7rem;
            vertical-align: top;
        }
        .factor-catalogue {
            background: #FFFFFF; border: 1px solid var(--line);
            border-radius: 14px; overflow: hidden; margin-bottom: 1.25rem;
        }
        .factor-definition-row {
            display: grid; grid-template-columns: minmax(260px, 0.8fr) 1.4fr;
            gap: 1.2rem; padding: 0.9rem 1rem;
            border-bottom: 1px solid var(--line); line-height: 1.5;
        }
        .factor-definition-row:last-child { border-bottom: 0; }
        .factor-badge {
            display: inline-block; min-width: 2.3rem; margin-right: 0.55rem;
            padding: 0.18rem 0.35rem; border-radius: 7px;
            background: var(--teal-soft); color: var(--teal);
            font-weight: 800; text-align: center;
        }
        .step-list { margin: 1.2rem 0; }
        .step-item {
            display: flex; gap: 0.65rem; align-items: center;
            padding: 0.42rem 0; color: #627D98; font-size: 0.9rem;
        }
        .step-dot {
            align-items: center; border: 1px solid #BCCCDC; border-radius: 50%;
            display: inline-flex; height: 1.45rem; justify-content: center;
            min-width: 1.45rem; font-size: 0.72rem; font-weight: 700;
        }
        .step-item.active { color: var(--ink); font-weight: 700; }
        .step-item.active .step-dot {
            background: var(--teal); color: white; border-color: var(--teal);
        }
        .step-item.done .step-dot {
            background: var(--teal-soft); color: var(--teal);
            border-color: #8BC9C0;
        }
        .stButton > button[kind="primary"] {
            background: var(--teal); border-color: var(--teal);
        }
        .stButton > button, .stDownloadButton > button {
            border-radius: 10px; min-height: 2.65rem;
        }
        .footer-note { color: #829AB1; font-size: 0.78rem; margin-top: 2rem; }
        .st-key-matrix_grid {
            background: #FFFFFF; border: 1px solid var(--line); border-radius: 14px;
            overflow-x: auto; padding: 0.7rem;
            box-shadow: 0 7px 22px rgba(16,42,67,.05);
        }
        .st-key-matrix_grid > div[data-testid="stVerticalBlock"] {
            min-width: 1460px;
        }
        .st-key-matrix_grid div[data-testid="stSelectbox"]
        div[data-baseweb="select"] > div {
            min-height: 38px; padding-left: 0.35rem; padding-right: 0.2rem;
        }
        .st-key-matrix_grid div[data-testid="stTextInput"] input {
            min-height: 38px; text-align: center; font-weight: 700;
        }
        .factor-code {
            display: inline-flex; align-items: center; justify-content: center;
            min-width: 2rem; font-weight: 760; color: var(--navy); cursor: help;
            border-bottom: 1px dotted #627D98;
        }
        .row-progress { color: #829AB1; font-size: 0.68rem; }
        @media (max-width: 760px) {
            .block-container { padding-top: 1rem; }
            .hero-card, .content-card { padding: 1rem; }
            .factor-definition-row { grid-template-columns: 1fr; gap: 0.5rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    """Render read-only study progress without bypassing the guarded flow."""

    current_page = int(st.session_state["current_page"])
    matrix_status = validate_matrix(st.session_state["judgments"])
    with st.sidebar:
        st.markdown(
            "<p class='eyebrow'>Research instrument</p>",
            unsafe_allow_html=True,
        )
        st.markdown(f"### {APP_TITLE}")
        st.markdown("<div class='step-list'>", unsafe_allow_html=True)
        for index, label in enumerate(PAGE_LABELS):
            if index == current_page:
                state = "active"
            elif index < current_page:
                state = "done"
            else:
                state = ""
            marker = "✓" if index < current_page else str(index + 1)
            st.markdown(
                f"<div class='step-item {state}'><span class='step-dot'>{marker}</span>"
                f"<span>{label}</span></div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
        st.divider()
        st.caption("Matrix completion")
        st.progress(matrix_status.completion_ratio)
        st.markdown(
            f"**{matrix_status.completed} / {REQUIRED_COMPARISONS}** comparisons"
        )
        st.caption("Responses stay in this browser session until final submission.")


def go_to_page(page_index: int) -> None:
    """Set the next valid step from a Streamlit button callback."""

    st.session_state["current_page"] = min(
        len(PAGE_LABELS) - 1, max(0, page_index)
    )


def _go_to_page_after_validation(
    page_index: int,
    validator: Callable[[], bool] | None,
) -> None:
    """Move forward only when an optional page validator succeeds."""

    if validator is None or validator():
        go_to_page(page_index)


def navigation_buttons(
    *,
    previous_page: int | None,
    next_page: int | None,
    next_label: str = "Continue",
    next_disabled: bool = False,
    on_next: Callable[[], bool] | None = None,
    key_prefix: str,
) -> None:
    """Render consistent Back/Continue controls.

    ``on_next`` may validate or persist page state. Returning ``False`` keeps
    the participant on the current page.
    """

    st.write("")
    left, _, right = st.columns([1, 3, 1])
    with left:
        if previous_page is not None:
            st.button(
                "← Back",
                key=f"{key_prefix}_back",
                on_click=go_to_page,
                args=(previous_page,),
                use_container_width=True,
            )
    with right:
        if next_page is not None:
            st.button(
                next_label,
                key=f"{key_prefix}_next",
                type="primary",
                disabled=next_disabled,
                on_click=_go_to_page_after_validation,
                args=(next_page, on_next),
                use_container_width=True,
            )


def page_header(eyebrow: str, title: str, description: str) -> None:
    """Render the consistent heading used by all questionnaire steps."""

    st.markdown(f"<p class='eyebrow'>{eyebrow}</p>", unsafe_allow_html=True)
    st.title(title)
    st.markdown(description)
