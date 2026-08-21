"""Application-level test of the guarded hierarchical questionnaire flow."""

from __future__ import annotations

from typing import Any

from streamlit.testing.v1 import AppTest

import pages.matrix as matrix_page
import pages.submit as submit_page
from config import SCALE_CODES
from hierarchical_questionnaire import matrix_definitions, relationships_for_matrix


class FakeQuestionnaireRepository:
    """In-memory repository used to exercise autosave and completion UI."""

    def __init__(self) -> None:
        self.responses: list[dict[str, Any]] = []

    def start_questionnaire(self, respondent_id, expert_code):
        return {
            "respondent_id": str(respondent_id),
            "expert_code": expert_code,
            "design_version": "hierarchical_v2",
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
        assert len(self.responses) == 90
        return {
            "respondent_id": str(respondent_id),
            "expert_code": "EXP-PILOT01",
            "design_version": "hierarchical_v2",
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

    assert app.session_state["questionnaire"]["design_version"] == "hierarchical_v2"
    assert len(app.radio) == 1
    assert not app.exception
    saved = 0
    for matrix_index, matrix in enumerate(matrix_definitions()):
        assert any(matrix.label in title.value for title in app.title)
        relationships = relationships_for_matrix(matrix.id)
        next_label = (
            "Review questionnaire"
            if matrix_index == len(matrix_definitions()) - 1
            else "Continue →"
        )
        assert _button_by_label(app, next_label).disabled is True

        for relationship_index, relationship in enumerate(relationships):
            assert app.session_state["active_relationship_key"] == relationship.key
            response = SCALE_CODES[(saved + relationship_index) % len(SCALE_CODES)]
            app.radio[0].set_value(response).run()
            saved += 1

            cell = app.button(
                key=(
                    f"cell_{matrix.id}_{relationship.source_code}_"
                    f"{relationship.target_code}"
                )
            )
            assert cell.label == response
            assert app.session_state["judgments"][relationship.key] == response
            assert len(repository.responses) == saved
            assert not app.exception

            if relationship_index < len(relationships) - 1:
                assert (
                    app.session_state["active_relationship_key"]
                    == relationships[relationship_index + 1].key
                )

        assert _button_by_label(app, next_label).disabled is False
        _button_by_label(app, next_label).click().run()

    assert saved == 90
    assert len(app.session_state["judgments"]) == 90
    submit_button = _button_by_label(app, "Submit expert evaluation")
    assert submit_button.disabled is False
    submit_button.click().run()

    assert app.session_state["submitted"] is True
    assert app.session_state["questionnaire"]["status"] == "completed"
    assert not app.exception
