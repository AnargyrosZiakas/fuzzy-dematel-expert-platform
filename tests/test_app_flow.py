"""Application-level test of the guarded distributed questionnaire flow."""

from __future__ import annotations

from typing import Any

from streamlit.testing.v1 import AppTest

import pages.matrix as matrix_page
import pages.submit as submit_page


class FakeQuestionnaireRepository:
    """In-memory repository used to exercise autosave and completion UI."""

    def __init__(self) -> None:
        self.responses: list[dict[str, Any]] = []

    def assign_respondent(self, respondent_id, expert_code):
        return {
            "respondent_id": str(respondent_id),
            "expert_code": expert_code,
            "set_id": 1,
            "status": "in_progress",
            "started_at": "2026-08-02T12:00:00+00:00",
            "completed_at": None,
        }

    def load_responses(self, _respondent_id):
        return self.responses

    def save_response(self, record):
        self.responses = [
            existing
            for existing in self.responses
            if not (
                existing["from_factor"] == record["from_factor"]
                and existing["to_factor"] == record["to_factor"]
            )
        ]
        self.responses.append(dict(record))

    def complete_assignment(self, respondent_id):
        return {
            "respondent_id": str(respondent_id),
            "expert_code": "EXP-PILOT01",
            "set_id": 1,
            "status": "completed",
            "started_at": "2026-08-02T12:00:00+00:00",
            "completed_at": "2026-08-02T12:10:00+00:00",
        }


def _button_by_label(app: AppTest, label: str):
    matches = [button for button in app.button if button.label == label]
    assert len(matches) == 1
    return matches[0]


def test_complete_ui_flow_uses_one_readable_autosaved_question(
    monkeypatch,
) -> None:
    repository = FakeQuestionnaireRepository()
    monkeypatch.setattr(matrix_page, "get_repository", lambda: repository)
    monkeypatch.setattr(submit_page, "get_repository", lambda: repository)

    app = AppTest.from_file("app.py", default_timeout=60).run()
    app.button(key="welcome_next").click().run()
    app.button(key="research_next").click().run()
    app.checkbox(key="consent_checkbox").check().run()
    app.button(key="consent_next").click().run()
    app.text_input(key="expert_code_input").set_value("EXP-PILOT01").run()
    app.button(key="expert_next").click().run()

    assert app.session_state["assigned_set_id"] == 1
    assert len(app.radio) == 1
    assert len(app.selectbox) == 0
    assert any("Question 1 of 44" in item.value for item in app.markdown)

    fuzzy_options = ["VL", "LI", "I", "HI", "VH"]
    for question_index in range(44):
        response = fuzzy_options[question_index % len(fuzzy_options)]
        app.radio[0].set_value(response).run()
        selected_markup = [markdown.value for markdown in app.markdown]
        assert any(
            "selected-response completed" in markup
            and f"<strong>{response}</strong>" in markup
            for markup in selected_markup
        )
        if question_index < 43:
            _button_by_label(app, "Next question →").click().run()

    assert len(app.session_state["judgments"]) == 44
    assert len(repository.responses) == 44
    _button_by_label(app, "Review responses").click().run()
    submit_button = _button_by_label(app, "Submit response set")
    assert submit_button.disabled is False
    submit_button.click().run()

    assert app.session_state["submitted"] is True
    assert not app.exception
