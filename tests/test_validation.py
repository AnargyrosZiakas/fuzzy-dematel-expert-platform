"""Unit tests for the instrument's strict validation boundary."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from config import (
    CANNOT_ASSESS_VALUE,
    FACTOR_CODES,
    REQUIRED_COMPARISONS,
    TOTAL_CELLS,
)
from questionnaire_sets import get_questionnaire_set
from validation import (
    build_distributed_response_record,
    build_response_records,
    comparison_key,
    validate_assigned_responses,
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


def test_assigned_set_validation_accepts_cannot_assess() -> None:
    relationships = get_questionnaire_set(1)
    judgments = {
        relationship.key: CANNOT_ASSESS_VALUE
        for relationship in relationships
    }
    result = validate_assigned_responses(1, judgments)
    assert result.is_valid
    assert result.completed == len(relationships) == 44


def test_distributed_record_has_names_set_and_nullable_tfn() -> None:
    relationship = get_questionnaire_set(7)[0]
    record = build_distributed_response_record(
        respondent_id=UUID("12345678-1234-5678-1234-567812345678"),
        expert_code="EXP-TEST01",
        relationship=relationship,
        linguistic_value=CANNOT_ASSESS_VALUE,
        responded_at=datetime(2026, 8, 2, 12, 0, tzinfo=UTC),
    )
    assert record["set_id"] == 7
    assert record["from_factor"] == relationship.source_code
    assert record["source_variable_name"] == relationship.source_name
    assert record["target_variable_name"] == relationship.target_name
    assert record["is_diagonal"] is False
    assert record["tfn_l"] is record["tfn_m"] is record["tfn_u"] is None
