"""Application configuration and immutable research instrument constants."""

from __future__ import annotations

import csv
import os
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Final

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
    LinguisticScaleItem("I", "Influence", 0.25, 0.50, 0.75),
    LinguisticScaleItem("HI", "High Influence", 0.50, 0.75, 1.00),
    LinguisticScaleItem("VH", "Very High Influence", 0.75, 1.00, 1.00),
)
SCALE_BY_CODE: Final[Mapping[str, LinguisticScaleItem]] = {
    item.code: item for item in SCALE_ITEMS
}
SCALE_CODES: Final[tuple[str, ...]] = tuple(SCALE_BY_CODE)

MATRIX_SIZE: Final[int] = len(FACTOR_CODES)
TOTAL_CELLS: Final[int] = MATRIX_SIZE * MATRIX_SIZE
DIAGONAL_CELLS: Final[int] = MATRIX_SIZE
REQUIRED_COMPARISONS: Final[int] = TOTAL_CELLS - DIAGONAL_CELLS

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
    ethics_reference: str

    @classmethod
    def from_environment(cls) -> ResearchSettings:
        """Build settings from environment variables with safe neutral defaults."""

        return cls(
            study_title=os.getenv("STUDY_TITLE", APP_TITLE),
            research_description=os.getenv(
                "RESEARCH_DESCRIPTION",
                (
                    "This study gathers structured expert judgments about the "
                    "direction and strength of influence among 18 research factors. "
                    "Responses will be analysed with the Fuzzy DEMATEL methodology."
                ),
            ),
            researcher_name=os.getenv(
                "RESEARCHER_NAME", "PhD Research Team"
            ),
            contact_email=os.getenv(
                "RESEARCH_CONTACT_EMAIL", "research-contact@example.edu"
            ),
            ethics_reference=os.getenv(
                "ETHICS_REFERENCE", "Configure the approved ethics reference"
            ),
        )


@lru_cache(maxsize=1)
def load_factor_definitions() -> dict[str, str]:
    """Load and strictly validate the fixed factor-definition catalogue."""

    with FACTOR_DEFINITIONS_PATH.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["factor_code", "full_definition"]:
            raise ValueError(
                "data/factors.csv must contain exactly the columns "
                "factor_code,full_definition."
            )
        definitions = {
            row["factor_code"].strip(): row["full_definition"].strip()
            for row in reader
        }

    if tuple(definitions) != FACTOR_CODES:
        raise ValueError(
            "data/factors.csv must contain each configured factor exactly once "
            "and in instrument order."
        )
    if any(not definition for definition in definitions.values()):
        raise ValueError("Every factor requires a non-empty full definition.")
    return definitions

