"""Tests for workbook-derived research content and factor definitions."""

from __future__ import annotations

from pathlib import Path

from config import (
    FACTOR_CODES,
    HIERARCHICAL_FACTOR_CODES,
    ResearchSettings,
    load_factor_catalogue,
    load_hierarchical_factor_catalogue,
)
from research_content import CONSENT_STATEMENT, CONTACT_EMAIL


def test_factor_catalogue_is_complete_and_has_no_placeholders() -> None:
    catalogue = load_factor_catalogue()
    assert tuple(item.code for item in catalogue) == FACTOR_CODES
    assert len({item.criterion for item in catalogue}) == len(FACTOR_CODES)
    assert all(item.dimension and item.definition for item in catalogue)
    assert all("replace this" not in item.definition.lower() for item in catalogue)


def test_current_hierarchical_catalogue_has_renumbered_compliance_s7() -> None:
    catalogue = load_hierarchical_factor_catalogue()
    assert tuple(item.code for item in catalogue) == HIERARCHICAL_FACTOR_CODES
    assert len(catalogue) == 17
    assert catalogue[-1].code == "S7"
    assert "compliance" in catalogue[-1].criterion.lower()
    assert all("stakeholders" not in item.criterion.lower() for item in catalogue)


def test_workbook_research_defaults_are_ready_for_display() -> None:
    settings = ResearchSettings.from_environment()
    assert settings.researcher_name == "Anargyros Ziakas"
    assert settings.contact_email == CONTACT_EMAIL
    assert "Cultural Determinants" in settings.study_title
    assert CONSENT_STATEMENT.startswith("I confirm that I have read")


def test_participant_copy_does_not_state_a_completion_time() -> None:
    participant_files = (
        "research_content.py",
        "pages/welcome.py",
        "pages/research.py",
        "pages/consent.py",
    )
    copy = "\n".join(
        Path(path).read_text(encoding="utf-8") for path in participant_files
    ).lower()
    assert "10 minutes" not in copy
    assert "10 mins" not in copy
    assert "estimated completion time" not in copy
