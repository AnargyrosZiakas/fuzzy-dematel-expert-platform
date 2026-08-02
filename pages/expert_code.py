"""Anonymous expert-code step."""

from __future__ import annotations

import streamlit as st

from components.layout import navigation_buttons, page_header
from utils import generate_anonymous_code
from validation import validate_expert_code


def _persist_code() -> None:
    st.session_state["expert_code"] = str(
        st.session_state.get("expert_code_input", "")
    ).strip()


def _validate_and_store_code() -> bool:
    is_valid, normalized, message = validate_expert_code(
        str(st.session_state.get("expert_code_input", ""))
    )
    if not is_valid:
        st.error(message)
        return False
    st.session_state["expert_code"] = normalized
    return True


def _generate_code() -> None:
    code = generate_anonymous_code()
    st.session_state["expert_code"] = code
    st.session_state["expert_code_input"] = code


def render() -> None:
    """Collect or generate a privacy-preserving expert code."""

    if not st.session_state["consent_given"]:
        st.warning("Please provide informed consent before continuing.")
        navigation_buttons(
            previous_page=2,
            next_page=None,
            key_prefix="expert_guard",
        )
        return

    page_header(
        "Step 4 of 6",
        "Anonymous expert code",
        (
            "Use the code provided by the research team, or generate one here. "
            "It identifies a submission without collecting your identity."
        ),
    )
    st.markdown(
        "<div class='privacy-note'><strong>Privacy reminder</strong><br>Do not "
        "use your name, initials, email address, employee number, or another "
        "code that directly identifies you.</div>",
        unsafe_allow_html=True,
    )
    st.write("")
    if "expert_code_input" not in st.session_state:
        st.session_state["expert_code_input"] = st.session_state["expert_code"]
    input_column, button_column = st.columns([3, 1])
    with input_column:
        st.text_input(
            "Expert code",
            key="expert_code_input",
            placeholder="Example: EXP-7K9M2Q4R",
            max_chars=64,
            on_change=_persist_code,
            help="Allowed: letters, numbers, hyphens, and underscores.",
        )
    with button_column:
        st.write("")
        st.button(
            "Generate code",
            key="generate_expert_code",
            on_click=_generate_code,
            use_container_width=True,
        )
    navigation_buttons(
        previous_page=2,
        next_page=4,
        on_next=_validate_and_store_code,
        key_prefix="expert",
    )
