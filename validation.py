"""Validation and canonical record construction for expert responses."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID

from config import (
    FACTOR_CODES,
    REQUIRED_COMPARISONS,
    SCALE_BY_CODE,
)
from models import MatrixValidationResult, ResponseRecord

EXPERT_CODE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,63}$")


def comparison_key(from_factor: str, to_factor: str) -> str:
    """Return the stable session-state key for an ordered factor pair."""

    return f"{from_factor}|{to_factor}"


def validate_expert_code(raw_code: str) -> tuple[bool, str, str]:
    """Validate and normalize a non-identifying expert code.

    Returns:
        A tuple of ``(is_valid, normalized_code, friendly_message)``.
    """

    normalized = raw_code.strip()
    if not normalized:
        return False, "", "Enter your anonymous expert code to continue."
    if not EXPERT_CODE_PATTERN.fullmatch(normalized):
        return (
            False,
            normalized,
            "Use 3–64 letters, numbers, hyphens, or underscores. Do not enter "
            "your name or email address.",
        )
    return True, normalized, ""


def validate_matrix(
    judgments: Mapping[str, str | None],
) -> MatrixValidationResult:
    """Validate all 306 required off-diagonal comparisons."""

    missing: list[tuple[str, str]] = []
    invalid: list[tuple[str, str]] = []
    completed = 0

    for from_factor in FACTOR_CODES:
        for to_factor in FACTOR_CODES:
            if from_factor == to_factor:
                continue
            value = judgments.get(comparison_key(from_factor, to_factor))
            if value is None or value == "":
                missing.append((from_factor, to_factor))
            elif value not in SCALE_BY_CODE:
                invalid.append((from_factor, to_factor))
            else:
                completed += 1

    return MatrixValidationResult(
        completed=completed,
        required=REQUIRED_COMPARISONS,
        missing=tuple(missing),
        invalid=tuple(invalid),
    )


def build_response_records(
    *,
    submission_id: UUID,
    expert_code: str,
    judgments: Mapping[str, str | None],
    submitted_at: datetime | None = None,
) -> list[ResponseRecord]:
    """Build the canonical 324-row representation for persistence and export.

    The 18 diagonal cells are created as explicit zero records. Off-diagonal
    records are accepted only after complete matrix validation.
    """

    is_code_valid, normalized_code, code_error = validate_expert_code(expert_code)
    if not is_code_valid:
        raise ValueError(code_error)

    matrix_validation = validate_matrix(judgments)
    if not matrix_validation.is_valid:
        raise ValueError(
            "The matrix is incomplete or contains invalid linguistic values."
        )

    timestamp = submitted_at or datetime.now(UTC)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    timestamp_iso = timestamp.astimezone(UTC).isoformat()

    records: list[ResponseRecord] = []
    for from_factor in FACTOR_CODES:
        for to_factor in FACTOR_CODES:
            is_diagonal = from_factor == to_factor
            if is_diagonal:
                value = "0"
                lower, modal, upper = 0.0, 0.0, 0.0
            else:
                value = str(judgments[comparison_key(from_factor, to_factor)])
                lower, modal, upper = SCALE_BY_CODE[value].tfn

            records.append(
                ResponseRecord(
                    submission_id=str(submission_id),
                    expert_code=normalized_code,
                    timestamp=timestamp_iso,
                    from_factor=from_factor,
                    to_factor=to_factor,
                    linguistic_value=value,
                    tfn_l=lower,
                    tfn_m=modal,
                    tfn_u=upper,
                    is_diagonal=is_diagonal,
                )
            )

    return records

