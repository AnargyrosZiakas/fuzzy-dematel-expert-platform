"""Application-level test of the guarded questionnaire flow."""

from __future__ import annotations

from streamlit.testing.v1 import AppTest


def test_complete_ui_flow_reaches_enabled_submit() -> None:
    """Exercise consent, code, all 306 dropdowns, and final preflight."""

    app = AppTest.from_file("app.py", default_timeout=60).run()
    app.button(key="welcome_next").click().run()
    app.button(key="research_next").click().run()

    app.checkbox(key="consent_checkbox").check().run()
    assert app.session_state["consent_given"] is True
    app.button(key="consent_next").click().run()

    app.text_input(key="expert_code_input").set_value("EXP-PILOT01").run()
    app.button(key="expert_next").click().run()

    assert len(app.selectbox) == 306
    assert len(app.text_input) == 18
    assert app.button(key="matrix_next").disabled is True

    for dropdown in app.selectbox:
        dropdown.set_value("I")
    app.run()

    assert len(app.session_state["judgments"]) == 306
    assert app.button(key="matrix_next").disabled is False
    app.button(key="matrix_next").click().run()

    submit_buttons = [
        button for button in app.button if button.label == "Submit complete matrix"
    ]
    assert len(submit_buttons) == 1
    assert submit_buttons[0].disabled is False
    assert not app.exception

