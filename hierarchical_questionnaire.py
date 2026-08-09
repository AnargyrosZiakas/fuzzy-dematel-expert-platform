"""Scientific configuration for the four hierarchical DEMATEL matrices."""

from __future__ import annotations

from functools import lru_cache

from config import HIERARCHICAL_REQUIRED_COMPARISONS, load_factor_catalogue
from models import (
    HierarchicalRelationship,
    MatrixCriterion,
    MatrixDefinition,
)

MATRIX_IDS = ("cultural", "economic", "strategic", "dimension_level")

_MATRIX_METADATA = (
    (
        "cultural",
        "Consumer-Cultural & Behavioural",
        "Consumer-Cultural",
        ("C1", "C2", "C3", "C4", "C5", "C6"),
    ),
    (
        "economic",
        "Economic & Market",
        "Economic & Market",
        ("E1", "E2", "E3", "E4"),
    ),
    (
        "strategic",
        "Airline Strategic & Operational",
        "Strategic & Operational",
        ("S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"),
    ),
)

_DIMENSION_CRITERIA = (
    MatrixCriterion(
        "C",
        "Consumer-Cultural & Behavioural",
        "The passenger-side cultural, behavioural, knowledge, trust and "
        "origin-context dimension represented by criteria C1–C6.",
    ),
    MatrixCriterion(
        "E",
        "Economic & Market",
        "The origin-market and airline investment context represented by "
        "criteria E1–E4.",
    ),
    MatrixCriterion(
        "S",
        "Airline Strategic & Operational",
        "The airline strategy, capability, stakeholder and compliance dimension "
        "represented by criteria S1–S8.",
    ),
)


@lru_cache(maxsize=1)
def matrix_definitions() -> tuple[MatrixDefinition, ...]:
    """Build and validate the four matrices from the canonical factor catalogue."""

    factor_by_code = {item.code: item for item in load_factor_catalogue()}
    matrices: list[MatrixDefinition] = []
    for matrix_id, label, short_label, codes in _MATRIX_METADATA:
        criteria = tuple(
            MatrixCriterion(
                code=code,
                name=factor_by_code[code].criterion,
                definition=factor_by_code[code].definition,
            )
            for code in codes
        )
        matrices.append(MatrixDefinition(matrix_id, label, short_label, criteria))
    matrices.append(
        MatrixDefinition(
            id="dimension_level",
            label="Relationships Between Dimensions",
            short_label="Dimension Relationships",
            criteria=_DIMENSION_CRITERIA,
        )
    )
    result = tuple(matrices)
    validate_hierarchical_design(result)
    return result


def validate_hierarchical_design(
    matrices: tuple[MatrixDefinition, ...],
) -> None:
    """Raise when matrix membership or the fixed 104-pair contract is violated."""

    if tuple(matrix.id for matrix in matrices) != MATRIX_IDS:
        raise ValueError("Hierarchical matrix IDs or order have changed.")
    expected_sizes = (6, 4, 8, 3)
    if tuple(len(matrix.criteria) for matrix in matrices) != expected_sizes:
        raise ValueError("Hierarchical matrix sizes must be 6, 4, 8, and 3.")
    criterion_codes = [
        criterion.code
        for matrix in matrices[:3]
        for criterion in matrix.criteria
    ]
    if len(criterion_codes) != 18 or len(set(criterion_codes)) != 18:
        raise ValueError("Each criterion must belong to exactly one Level 1 matrix.")
    total = sum(matrix.required_comparisons for matrix in matrices)
    if total != HIERARCHICAL_REQUIRED_COMPARISONS:
        raise ValueError("The hierarchical design must contain exactly 104 pairs.")


def get_matrix_definition(matrix_id: str) -> MatrixDefinition:
    """Return one configured matrix by stable ID."""

    for matrix in matrix_definitions():
        if matrix.id == matrix_id:
            return matrix
    raise ValueError(f"Unknown hierarchical matrix ID: {matrix_id}")


@lru_cache(maxsize=1)
def all_hierarchical_relationships() -> tuple[HierarchicalRelationship, ...]:
    """Return all 104 allowed relationships in stable matrix/row order."""

    relationships: list[HierarchicalRelationship] = []
    for matrix in matrix_definitions():
        position = 0
        for source in matrix.criteria:
            for target in matrix.criteria:
                if source.code == target.code:
                    continue
                position += 1
                relationships.append(
                    HierarchicalRelationship(
                        matrix_id=matrix.id,
                        matrix_label=matrix.label,
                        position=position,
                        source_code=source.code,
                        source_name=source.name,
                        target_code=target.code,
                        target_name=target.name,
                    )
                )
    if len(relationships) != HIERARCHICAL_REQUIRED_COMPARISONS:
        raise ValueError("The hierarchical relationship catalogue is incomplete.")
    if len({relationship.key for relationship in relationships}) != len(
        relationships
    ):
        raise ValueError("Hierarchical relationships must be unique.")
    return tuple(relationships)


def relationships_for_matrix(
    matrix_id: str,
) -> tuple[HierarchicalRelationship, ...]:
    """Return the ordered off-diagonal relationships for one matrix."""

    get_matrix_definition(matrix_id)
    return tuple(
        relationship
        for relationship in all_hierarchical_relationships()
        if relationship.matrix_id == matrix_id
    )


def relationship_by_key(key: str) -> HierarchicalRelationship:
    """Resolve a stable hierarchical answer key."""

    for relationship in all_hierarchical_relationships():
        if relationship.key == key:
            return relationship
    raise ValueError("Unknown or prohibited hierarchical relationship.")
