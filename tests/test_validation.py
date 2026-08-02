"""Unit tests for the instrument's strict validation boundary."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from config import FACTOR_CODES, REQUIRED_COMPARISONS, TOTAL_CELLS
from validation import (
    build_response_records,
    comparison_key,
    validate_expert_code,
    validate_matrix,
)


def test_empty_matrix_reports_all_required_comparisons() -> None:
    result = validate_matrix({})
    assert result.completed == 0
    assert len(result.missing) == REQUIRED_COMPARISONS
    assert not result.is_valid


def test_complete_matrix_is_valid(complete_judgments: dict[str, str]) -> None:
    result = validate_matrix(complete_judgments)
    assert result.completed == REQUIRED_COMPARISONS
    assert result.completion_ratio == 1.0
    assert result.is_valid


def test_invalid_scale_value_is_not_counted(
    complete_judgments: dict[str, str],
) -> None:
    complete_judgments[comparison_key("C1", "C2")] = "MEDIUM"
    result = validate_matrix(complete_judgments)
    assert result.completed == REQUIRED_COMPARISONS - 1
    assert result.invalid == (("C1", "C2"),)
    assert not result.is_valid


@pytest.mark.parametrize(
    ("raw_code", "expected"),
    [("EXP-ABC123", True), ("a_b", True), ("ab", False), ("name@email", False)],
)
def test_expert_code_validation(raw_code: str, expected: bool) -> None:
    assert validate_expert_code(raw_code)[0] is expected


def test_build_records_creates_complete_matrix_with_zero_diagonal(
    complete_judgments: dict[str, str],
) -> None:
    submission_id = UUID("12345678-1234-5678-1234-567812345678")
    submitted_at = datetime(2026, 8, 2, 12, 0, tzinfo=UTC)
    records = build_response_records(
        submission_id=submission_id,
        expert_code="EXP-TEST01",
        judgments=complete_judgments,
        submitted_at=submitted_at,
    )

    assert len(records) == TOTAL_CELLS
    diagonal = [record for record in records if record["is_diagonal"]]
    assert len(diagonal) == len(FACTOR_CODES)
    assert all(record["linguistic_value"] == "0" for record in diagonal)
    assert all(
        (record["tfn_l"], record["tfn_m"], record["tfn_u"])
        == (0.0, 0.0, 0.0)
        for record in diagonal
    )


def test_build_records_rejects_incomplete_matrix() -> None:
    with pytest.raises(ValueError, match="incomplete"):
        build_response_records(
            submission_id=UUID("12345678-1234-5678-1234-567812345678"),
            expert_code="EXP-TEST01",
            judgments={},
        )

