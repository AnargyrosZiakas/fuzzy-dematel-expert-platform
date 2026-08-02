"""Application configuration and immutable research instrument constants."""

from __future__ import annotations

import csv
import os
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Final

from research_content import (
    CONTACT_EMAIL,
    DOCTORAL_RESEARCH_TITLE,
    RESEARCHER_NAME,
)

BASE_DIR: Final[Path] = Path(__file__).resolve().parent
FACTOR_DEFINITIONS_PATH: Final[Path] = BASE_DIR / "data" / "factors.csv"

FACTOR_CODES: Final[tuple[str, ...]] = (
    "C1",
    "C2",
    "C3",
    "C4",
    "C5",
    "C6",
    "E1",
    "E2",
    "E3",
    "E4",
    "S1",
    "S2",
    "S3",
    "S4",
    "S5",
    "S6",
    "S7",
    "S8",
)


@dataclass(frozen=True, slots=True)
class LinguisticScaleItem:
    """One linguistic judgment and its triangular fuzzy number (TFN)."""

    code: str
    label: str
    lower: float
    modal: float
    upper: float

    @property
    def tfn(self) -> tuple[float, float, float]:
        """Return the TFN as ``(lower, modal, upper)``."""

        return self.lower, self.modal, self.upper


SCALE_ITEMS: Final[tuple[LinguisticScaleItem, ...]] = (
    LinguisticScaleItem("VL", "Very Low Influence", 0.00, 0.00, 0.25),
    LinguisticScaleItem("LI", "Low Influence", 0.00, 0.25, 0.50),
    LinguisticScaleItem("I", "Moderate Influence", 0.25, 0.50, 0.75),
    LinguisticScaleItem("HI", "High Influence", 0.50, 0.75, 1.00),
    LinguisticScaleItem("VH", "Very High Influence", 0.75, 1.00, 1.00),
)
SCALE_BY_CODE: Final[Mapping[str, LinguisticScaleItem]] = {
    item.code: item for item in SCALE_ITEMS
}
SCALE_CODES: Final[tuple[str, ...]] = tuple(SCALE_BY_CODE)
CANNOT_ASSESS_VALUE: Final[str] = "Cannot Assess"
RESPONSE_OPTIONS: Final[tuple[str, ...]] = SCALE_CODES + (CANNOT_ASSESS_VALUE,)

MATRIX_SIZE: Final[int] = len(FACTOR_CODES)
TOTAL_CELLS: Final[int] = MATRIX_SIZE * MATRIX_SIZE
DIAGONAL_CELLS: Final[int] = MATRIX_SIZE
REQUIRED_COMPARISONS: Final[int] = TOTAL_CELLS - DIAGONAL_CELLS
QUESTIONNAIRE_SET_COUNT: Final[int] = 7
MIN_EVALUATIONS_DEFAULT: Final[int] = 3

APP_TITLE: Final[str] = "Fuzzy DEMATEL Expert Evaluation Platform"
APP_ICON: Final[str] = "∿"
DEFAULT_TABLE_NAME: Final[str] = "expert_responses"
DEFAULT_SCHEMA_NAME: Final[str] = "public"


@dataclass(frozen=True, slots=True)
class ResearchSettings:
    """Researcher-editable study metadata displayed to participants."""

    study_title: str
    research_description: str
    researcher_name: str
    contact_email: str

    @classmethod
    def from_environment(cls) -> ResearchSettings:
        """Build settings with workbook-approved defaults and optional overrides."""

        return cls(
            study_title=os.getenv("STUDY_TITLE", DOCTORAL_RESEARCH_TITLE),
            research_description=os.getenv(
                "RESEARCH_DESCRIPTION",
                (
                    "This questionnaire examines causal relationships among "
                    "cultural, economic and strategic factors associated with "
                    "sustainable airline strategy using Fuzzy DEMATEL."
                ),
            ),
            researcher_name=os.getenv("RESEARCHER_NAME", RESEARCHER_NAME),
            contact_email=os.getenv("RESEARCH_CONTACT_EMAIL", CONTACT_EMAIL),
        )


@dataclass(frozen=True, slots=True)
class FactorDefinition:
    """One factor's dimension, criterion name, and operational definition."""

    code: str
    dimension: str
    criterion: str
    definition: str

    @property
    def tooltip(self) -> str:
        """Return the complete matrix tooltip text."""

        return f"{self.criterion} — {self.definition}"


@lru_cache(maxsize=1)
def load_factor_catalogue() -> tuple[FactorDefinition, ...]:
    """Load and strictly validate the fixed factor catalogue."""

    expected_fields = [
        "factor_code",
        "dimension",
        "criterion",
        "full_definition",
    ]
    with FACTOR_DEFINITIONS_PATH.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != expected_fields:
            raise ValueError(
                "data/factors.csv must contain exactly the columns "
                + ",".join(expected_fields)
                + "."
            )
        catalogue = tuple(
            FactorDefinition(
                code=row["factor_code"].strip(),
                dimension=row["dimension"].strip(),
                criterion=row["criterion"].strip(),
                definition=row["full_definition"].strip(),
            )
            for row in reader
        )

    if tuple(item.code for item in catalogue) != FACTOR_CODES:
        raise ValueError(
            "data/factors.csv must contain each configured factor exactly once "
            "and in instrument order."
        )
    if any(
        not item.dimension or not item.criterion or not item.definition
        for item in catalogue
    ):
        raise ValueError(
            "Every factor requires a dimension, criterion, and definition."
        )
    return catalogue


@lru_cache(maxsize=1)
def load_factor_definitions() -> dict[str, str]:
    """Return complete criterion-and-definition text for matrix tooltips."""

    return {item.code: item.tooltip for item in load_factor_catalogue()}
