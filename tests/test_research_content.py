"""Tests for workbook-derived research content and factor definitions."""

from __future__ import annotations

from config import FACTOR_CODES, ResearchSettings, load_factor_catalogue
from research_content import CONSENT_STATEMENT, CONTACT_EMAIL


def test_factor_catalogue_is_complete_and_has_no_placeholders() -> None:
    catalogue = load_factor_catalogue()
    assert tuple(item.code for item in catalogue) == FACTOR_CODES
    assert len({item.criterion for item in catalogue}) == len(FACTOR_CODES)
    assert all(item.dimension and item.definition for item in catalogue)
    assert all("replace this" not in item.definition.lower() for item in catalogue)


def test_workbook_research_defaults_are_ready_for_display() -> None:
    settings = ResearchSettings.from_environment()
    assert settings.researcher_name == "Anargyros Ziakas"
    assert settings.contact_email == CONTACT_EMAIL
    assert "Cultural Determinants" in settings.study_title
    assert CONSENT_STATEMENT.startswith("I confirm that I have read")
