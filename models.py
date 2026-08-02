"""Typed domain models shared across application layers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict


class ResponseRecord(TypedDict):
    """Database and long-format export representation of one matrix cell."""

    submission_id: str
    expert_code: str
    timestamp: str
    from_factor: str
    to_factor: str
    linguistic_value: str
    tfn_l: float
    tfn_m: float
    tfn_u: float
    is_diagonal: bool


@dataclass(frozen=True, slots=True)
class MatrixValidationResult:
    """Completeness and validity status for the 18×18 instrument."""

    completed: int
    required: int
    missing: tuple[tuple[str, str], ...]
    invalid: tuple[tuple[str, str], ...]

    @property
    def is_valid(self) -> bool:
        """Whether all required off-diagonal judgments are present and valid."""

        return not self.missing and not self.invalid

    @property
    def completion_ratio(self) -> float:
        """Return a bounded progress ratio for UI progress components."""

        if self.required == 0:
            return 1.0
        return min(1.0, max(0.0, self.completed / self.required))

