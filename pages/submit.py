"""Final validation, Supabase submission, and export download step."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

import streamlit as st

from components.layout import go_to_page, page_header
from config import REQUIRED_COMPARISONS
from database import (
    DatabaseConfigurationError,
    SubmissionError,
    SupabaseResponseRepository,
    SupabaseSettings,
)
from export import generate_exports
from models import ResponseRecord
from validation import (
    build_response_records,
    validate_expert_code,
    validate_matrix,
)

LOGGER = logging.getLogger(__name__)


def _server_secrets() -> dict[str, Any]:
    try:
        return dict(st.secrets)
    except Exception:
        return {}


def _submit() -> None:
    """Validate, create one UUID, persist atomically, and retain a receipt."""

    status = validate_matrix(st.session_state["judgments"])
    code_is_valid, normalized_code, code_message = validate_expert_code(
        st.session_state["expert_code"]
    )
    if not st.session_state["consent_given"]:
        st.error("Informed consent is required before submission.")
        return
    if not code_is_valid:
        st.error(code_message)
        return
    if not status.is_valid:
        st.error(
            f"Submission is blocked: {len(status.missing)} comparison(s) are missing."
        )
        return

    try:
        submission_id = uuid4()
        records = build_response_records(
            submission_id=submission_id,
            expert_code=normalized_code,
            judgments=st.session_state["judgments"],
        )
        settings = SupabaseSettings.from_sources(_server_secrets())
        repository = SupabaseResponseRepository.connect(settings)
        with st.spinner("Securely storing the complete matrix…"):
            repository.save_submission(records)
        st.session_state["submitted_records"] = records
        st.session_state["submitted"] = True
    except (DatabaseConfigurationError, SubmissionError, ValueError) as exc:
        st.error(str(exc))
    except Exception:
        LOGGER.exception("Unexpected submission failure")
        st.error(
            "An unexpected error prevented submission. Your answers are still "
            "available in this browser session; please retry."
        )


def _render_downloads(records: list[ResponseRecord]) -> None:
    bundle = generate_exports(records)
    submission_id = records[0]["submission_id"]
    prefix = f"fuzzy_dematel_{submission_id}"
    st.markdown("### Research data files")
    st.caption(
        "The four files contain the same submitted matrix in analysis-ready layouts."
    )
    first, second = st.columns(2)
    with first:
        st.download_button(
            "Download long CSV",
            bundle.long_csv,
            file_name=f"{prefix}_long.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.download_button(
            "Download long Excel",
            bundle.long_excel,
            file_name=f"{prefix}_long.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with second:
        st.download_button(
            "Download wide CSV",
            bundle.wide_csv,
            file_name=f"{prefix}_wide.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.download_button(
            "Download wide Excel (TFN sheets)",
            bundle.wide_excel,
            file_name=f"{prefix}_wide.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


def render() -> None:
    """Render preflight checks, one-time submission, receipt, and exports."""

    status = validate_matrix(st.session_state["judgments"])
    code_is_valid, _, _ = validate_expert_code(st.session_state["expert_code"])
    can_submit = (
        bool(st.session_state["consent_given"])
        and code_is_valid
        and status.is_valid
    )

    page_header(
        "Step 6 of 6",
        "Review and submit",
        (
            "Confirm the validation summary below. Final submission stores one "
            "complete, immutable expert matrix under a unique UUID."
        ),
    )

    if st.session_state["submitted"]:
        records = st.session_state.get("submitted_records")
        if not records:
            st.error("The submission receipt is unavailable in this session.")
            return
        submission_id = records[0]["submission_id"]
        st.success("Your expert evaluation has been submitted successfully.")
        st.markdown(
            f"<div class='content-card'><strong>Submission receipt</strong><br>"
            f"UUID: <code>{submission_id}</code><br>"
            f"Stored matrix cells: <strong>{len(records)}</strong></div>",
            unsafe_allow_html=True,
        )
        st.info(
            "Keep the UUID if the study protocol permits later withdrawal or queries."
        )
        _render_downloads(records)
        return

    first, second, third = st.columns(3)
    first.metric(
        "Consent",
        "Confirmed" if st.session_state["consent_given"] else "Missing",
    )
    second.metric("Expert code", "Valid" if code_is_valid else "Missing")
    second.caption(
        st.session_state["expert_code"] if code_is_valid else "Return to step 4"
    )
    third.metric("Comparisons", f"{status.completed} / {REQUIRED_COMPARISONS}")

    if can_submit:
        st.success("Validation passed. The complete 18×18 matrix is ready to submit.")
    else:
        messages = []
        if not st.session_state["consent_given"]:
            messages.append("consent is not confirmed")
        if not code_is_valid:
            messages.append("the expert code is invalid")
        if not status.is_valid:
            messages.append(f"{len(status.missing)} comparisons are missing")
        st.warning("Submission is not yet available: " + "; ".join(messages) + ".")

    st.markdown(
        "<div class='privacy-note'><strong>Final action</strong><br>After a "
        "successful submission, this browser session prevents accidental "
        "duplicate submission.</div>",
        unsafe_allow_html=True,
    )
    st.write("")
    back_column, _, submit_column = st.columns([1, 3, 1.4])
    with back_column:
        if st.button("← Back to matrix", use_container_width=True):
            go_to_page(4)
    with submit_column:
        st.button(
            "Submit complete matrix",
            type="primary",
            disabled=not can_submit,
            on_click=_submit,
            use_container_width=True,
        )
