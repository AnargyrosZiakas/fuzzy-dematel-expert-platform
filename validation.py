"""Validation and canonical record construction for expert responses."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID

from config import (
    CANNOT_ASSESS_VALUE,
    FACTOR_CODES,
    REQUIRED_COMPARISONS,
    RESPONSE_OPTIONS,
    SCALE_BY_CODE,
    SCALE_CODES,
)
from hierarchical_questionnaire import (
    all_hierarchical_relationships,
    relationships_for_matrix,
)
from models import (
    DirectedRelationship,
    DistributedResponseRecord,
    HierarchicalRelationship,
    HierarchicalResponseRecord,
    MatrixValidationResult,
    ResponseRecord,
)
from questionnaire_sets import get_questionnaire_set

EXPERT_CODE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,63}$")


def comparison_key(from_factor: str, to_factor: str) -> str:
    """Return the stable session-state key for an ordered factor pair."""

    return f"{from_factor}|{to_factor}"


def hierarchical_comparison_key(
    matrix_id: str, source_code: str, target_code: str
) -> str:
    """Return the stable answer key for one hierarchical relationship."""

    return f"{matrix_id}|{source_code}|{target_code}"


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


def validate_assigned_responses(
    set_id: int,
    judgments: Mapping[str, str | None],
) -> MatrixValidationResult:
    """Validate only the relationships belonging to one assigned set."""

    relationships = get_questionnaire_set(set_id)
    missing: list[tuple[str, str]] = []
    invalid: list[tuple[str, str]] = []
    completed = 0
    for relationship in relationships:
        value = judgments.get(relationship.key)
        pair = (relationship.source_code, relationship.target_code)
        if value is None or value == "":
            missing.append(pair)
        elif value not in RESPONSE_OPTIONS:
            invalid.append(pair)
        else:
            completed += 1
    return MatrixValidationResult(
        completed=completed,
        required=len(relationships),
        missing=tuple(missing),
        invalid=tuple(invalid),
    )


def validate_hierarchical_matrix(
    matrix_id: str,
    judgments: Mapping[str, str | None],
) -> MatrixValidationResult:
    """Validate every required off-diagonal answer in one configured matrix."""

    relationships = relationships_for_matrix(matrix_id)
    missing: list[tuple[str, str]] = []
    invalid: list[tuple[str, str]] = []
    completed = 0
    for relationship in relationships:
        value = judgments.get(relationship.key)
        pair = (relationship.source_code, relationship.target_code)
        if value is None or value == "":
            missing.append(pair)
        elif value not in SCALE_CODES:
            invalid.append(pair)
        else:
            completed += 1
    return MatrixValidationResult(
        completed=completed,
        required=len(relationships),
        missing=tuple(missing),
        invalid=tuple(invalid),
    )


def validate_hierarchical_questionnaire(
    judgments: Mapping[str, str | None],
) -> MatrixValidationResult:
    """Validate all and only the 104 relationships in the hierarchical design."""

    relationships = all_hierarchical_relationships()
    missing: list[tuple[str, str]] = []
    invalid: list[tuple[str, str]] = []
    completed = 0
    for relationship in relationships:
        value = judgments.get(relationship.key)
        pair = (relationship.source_code, relationship.target_code)
        if value is None or value == "":
            missing.append(pair)
        elif value not in SCALE_CODES:
            invalid.append(pair)
        else:
            completed += 1
    return MatrixValidationResult(
        completed=completed,
        required=len(relationships),
        missing=tuple(missing),
        invalid=tuple(invalid),
    )


def build_hierarchical_response_record(
    *,
    respondent_id: UUID,
    expert_code: str,
    relationship: HierarchicalRelationship,
    linguistic_value: str,
    responded_at: datetime | None = None,
) -> HierarchicalResponseRecord:
    """Build one validated, analysis-ready hierarchical autosave record."""

    is_code_valid, normalized_code, code_error = validate_expert_code(expert_code)
    if not is_code_valid:
        raise ValueError(code_error)
    if relationship.source_code == relationship.target_code:
        raise ValueError("Diagonal relationships cannot be stored.")
    allowed_keys = {
        configured.key for configured in all_hierarchical_relationships()
    }
    if relationship.key not in allowed_keys:
        raise ValueError("This relationship is not part of the hierarchical design.")
    if linguistic_value not in SCALE_CODES:
        raise ValueError("Select one of the five valid linguistic responses.")

    lower, modal, upper = SCALE_BY_CODE[linguistic_value].tfn
    timestamp = responded_at or datetime.now(UTC)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)

    return HierarchicalResponseRecord(
        respondent_id=str(respondent_id),
        expert_code=normalized_code,
        matrix_id=relationship.matrix_id,
        source_code=relationship.source_code,
        source_name=relationship.source_name,
        target_code=relationship.target_code,
        target_name=relationship.target_name,
        linguistic_value=linguistic_value,
        tfn_l=lower,
        tfn_m=modal,
        tfn_u=upper,
        responded_at=timestamp.astimezone(UTC).isoformat(),
    )


def build_distributed_response_record(
    *,
    respondent_id: UUID,
    expert_code: str,
    relationship: DirectedRelationship,
    linguistic_value: str,
    responded_at: datetime | None = None,
) -> DistributedResponseRecord:
    """Build one canonical autosave record for an assigned relationship."""

    is_code_valid, normalized_code, code_error = validate_expert_code(expert_code)
    if not is_code_valid:
        raise ValueError(code_error)
    if relationship.source_code == relationship.target_code:
        raise ValueError("Diagonal relationships cannot be stored.")
    if linguistic_value not in RESPONSE_OPTIONS:
        raise ValueError("Select a valid linguistic response.")

    if linguistic_value == CANNOT_ASSESS_VALUE:
        lower = modal = upper = None
    else:
        lower, modal, upper = SCALE_BY_CODE[linguistic_value].tfn

    timestamp = responded_at or datetime.now(UTC)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)

    return DistributedResponseRecord(
        submission_id=str(respondent_id),
        expert_code=normalized_code,
        set_id=relationship.set_id,
        timestamp=timestamp.astimezone(UTC).isoformat(),
        from_factor=relationship.source_code,
        source_variable_name=relationship.source_name,
        to_factor=relationship.target_code,
        target_variable_name=relationship.target_name,
        linguistic_value=linguistic_value,
        tfn_l=lower,
        tfn_m=modal,
        tfn_u=upper,
        is_diagonal=False,
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
