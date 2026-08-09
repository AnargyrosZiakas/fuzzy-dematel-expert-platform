"""Application-level test of the guarded hierarchical questionnaire flow."""

from __future__ import annotations

from typing import Any

from streamlit.testing.v1 import AppTest

import pages.matrix as matrix_page
import pages.submit as submit_page
from hierarchical_questionnaire import all_hierarchical_relationships


class FakeQuestionnaireRepository:
    """In-memory repository used to exercise autosave and completion UI."""

    def __init__(self) -> None:
        self.responses: list[dict[str, Any]] = []

    def start_questionnaire(self, respondent_id, expert_code):
        return {
            "respondent_id": str(respondent_id),
            "expert_code": expert_code,
            "design_version": "hierarchical_v1",
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
                existing["matrix_id"] == record["matrix_id"]
                and existing["source_code"] == record["source_code"]
                and existing["target_code"] == record["target_code"]
            )
        ]
        self.responses.append(dict(record))

    def complete_questionnaire(self, respondent_id):
        return {
            "respondent_id": str(respondent_id),
            "expert_code": "EXP-PILOT01",
            "design_version": "hierarchical_v1",
            "status": "completed",
            "started_at": "2026-08-02T12:00:00+00:00",
            "completed_at": "2026-08-02T12:10:00+00:00",
        }


def _button_by_label(app: AppTest, label: str):
    matches = [button for button in app.button if button.label == label]
    assert len(matches) == 1
    return matches[0]


def test_complete_hierarchical_ui_flow_and_visible_cell_states(monkeypatch) -> None:
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

    assert app.session_state["questionnaire"]["design_version"] == "hierarchical_v1"
    assert len(app.radio) == 1
    assert not app.exception
    assert any(
        "Consumer-Cultural & Behavioural" in title.value
        for title in app.title
    )

    for response in ("VL", "LI", "I", "HI", "VH"):
        app.radio[0].set_value(response).run()
        cell = app.button(key="cell_cultural_C1_C2")
        assert cell.label == response
        assert response in app.session_state["judgments"].values()
        assert not app.exception

    for expected_title in (
        "Economic & Market",
        "Airline Strategic & Operational",
        "Relationships Between Dimensions",
    ):
        _button_by_label(app, "Continue →").click().run()
        assert any(expected_title in title.value for title in app.title)

    app.session_state["judgments"] = {
        relationship.key: "I"
        for relationship in all_hierarchical_relationships()
    }
    app.run()
    _button_by_label(app, "Review questionnaire").click().run()
    submit_button = _button_by_label(app, "Submit expert evaluation")
    assert submit_button.disabled is False
    submit_button.click().run()

    assert app.session_state["submitted"] is True
    assert not app.exception
