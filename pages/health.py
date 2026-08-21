"""Read-only application and database health endpoint."""

from __future__ import annotations

import logging

import streamlit as st

from services import get_repository

LOGGER = logging.getLogger(__name__)


def render() -> None:
    """Report whether the deployment and its database are reachable."""

    st.title("Application status")
    try:
        get_repository().health_check()
    except Exception:
        LOGGER.exception("Public deployment health check failed")
        st.error("The questionnaire service is temporarily unavailable.")
        st.code("HEALTH_CHECK_FAILED", language=None)
        return

    st.success("The questionnaire and secure research database are available.")
    st.code("HEALTH_CHECK_OK", language=None)
    st.caption(
        "This read-only check does not create a respondent or store an answer."
    )
