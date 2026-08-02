"""Streamlit entry point for the Fuzzy DEMATEL expert platform."""

from __future__ import annotations

import logging

import streamlit as st

from components.layout import (
    PAGE_LABELS,
    initialize_session_state,
    inject_global_styles,
    render_sidebar,
)
from config import APP_ICON, APP_TITLE
from pages import admin, consent, expert_code, matrix, research, submit, welcome
from progress import restore_progress_from_query
from utils import configure_logging

LOGGER = logging.getLogger(__name__)
PAGE_RENDERERS = (
    welcome.render,
    research.render,
    consent.render,
    expert_code.render,
    matrix.render,
    submit.render,
)


def main() -> None:
    """Configure and render the active guarded questionnaire step."""

    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "About": (
                "Scientific expert-response instrument for an 18×18 Fuzzy "
                "DEMATEL influence matrix."
            )
        },
    )
    configure_logging()
    initialize_session_state()
    inject_global_styles()

    admin_mode = str(st.query_params.get("admin", "")).lower() in {
        "1",
        "true",
        "yes",
    }
    if not admin_mode:
        restore_progress_from_query()
    render_sidebar(admin_mode=admin_mode)

    if admin_mode:
        admin.render()
        st.markdown(
            "<p class='footer-note'>Fuzzy DEMATEL Research Administration · "
            "Restricted access</p>",
            unsafe_allow_html=True,
        )
        return

    if st.session_state.get("resume_error"):
        st.warning(st.session_state["resume_error"])

    page_index = int(st.session_state["current_page"])
    if not 0 <= page_index < len(PAGE_RENDERERS):
        LOGGER.warning("Invalid page index %s; returning to welcome", page_index)
        st.session_state["current_page"] = 0
        page_index = 0

    try:
        PAGE_RENDERERS[page_index]()
    except Exception:
        LOGGER.exception(
            "Unable to render questionnaire page %s", PAGE_LABELS[page_index]
        )
        st.error(
            "This page could not be displayed. Your completed answers remain in "
            "this browser session; please refresh and try again."
        )

    st.markdown(
        "<p class='footer-note'>Fuzzy DEMATEL Expert Evaluation Platform · "
        "Balanced directed-relationship research instrument</p>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
