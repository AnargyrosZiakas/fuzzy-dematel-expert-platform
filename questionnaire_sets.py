"""Deterministic balanced partition of the 306 directed relationships."""

from __future__ import annotations

from collections import Counter
from functools import lru_cache

from config import (
    FACTOR_CODES,
    QUESTIONNAIRE_SET_COUNT,
    REQUIRED_COMPARISONS,
    load_factor_catalogue,
)
from models import DirectedRelationship

# Rows and columns follow FACTOR_CODES. ``0`` marks the forbidden diagonal and
# digits 1–7 identify the assigned set. This audited partition is deliberately
# explicit so Python, SQL, tests, and future data audits share a stable design.
SET_ASSIGNMENT_MATRIX = (
    "041356352726771451",
    "303422777661154514",
    "320256461377245561",
    "566077124371536244",
    "114302643736742525",
    "512760235641416735",
    "261143066213557472",
    "742325101563523647",
    "553157310442617236",
    "274561145074362723",
    "637615422502431317",
    "163614723450675372",
    "132574532764064156",
    "475741243125206163",
    "747634651517320232",
    "426273376155173054",
    "457431417235325606",
    "675136574344112620",
)


@lru_cache(maxsize=1)
def build_questionnaire_sets() -> dict[int, tuple[DirectedRelationship, ...]]:
    """Return seven balanced, disjoint sets covering all directed pairs once.

    The explicit audited partition gives set sizes of 44, 44, 44, 44, 44, 43,
    and 43 while each variable appears as a source and target two or three times
    per set.
    """

    factor_names = {
        item.code: item.criterion for item in load_factor_catalogue()
    }
    mutable_sets: dict[int, list[DirectedRelationship]] = {
        set_id: [] for set_id in range(1, QUESTIONNAIRE_SET_COUNT + 1)
    }

    for source_index, source_code in enumerate(FACTOR_CODES):
        for target_index, target_code in enumerate(FACTOR_CODES):
            set_id = int(SET_ASSIGNMENT_MATRIX[source_index][target_index])
            if set_id == 0:
                continue
            relationships = mutable_sets[set_id]
            relationships.append(
                DirectedRelationship(
                    set_id=set_id,
                    position=len(relationships) + 1,
                    source_code=source_code,
                    source_name=factor_names[source_code],
                    target_code=target_code,
                    target_name=factor_names[target_code],
                )
            )

    questionnaire_sets = {
        set_id: tuple(relationships)
        for set_id, relationships in mutable_sets.items()
    }
    validate_questionnaire_sets(questionnaire_sets)
    return questionnaire_sets


def validate_questionnaire_sets(
    questionnaire_sets: dict[int, tuple[DirectedRelationship, ...]],
) -> None:
    """Raise ``ValueError`` if the scientific partition contract is violated."""

    expected_set_ids = set(range(1, QUESTIONNAIRE_SET_COUNT + 1))
    if set(questionnaire_sets) != expected_set_ids:
        raise ValueError("Questionnaire set IDs must be exactly 1 through 7.")

    relationships = [
        relationship
        for set_relationships in questionnaire_sets.values()
        for relationship in set_relationships
    ]
    pairs = [
        (relationship.source_code, relationship.target_code)
        for relationship in relationships
    ]
    if len(pairs) != REQUIRED_COMPARISONS or len(set(pairs)) != len(pairs):
        raise ValueError("The seven sets must cover all 306 directed pairs once.")
    if any(source == target for source, target in pairs):
        raise ValueError("Diagonal relationships are forbidden.")

    expected_pairs = {
        (source, target)
        for source in FACTOR_CODES
        for target in FACTOR_CODES
        if source != target
    }
    if set(pairs) != expected_pairs:
        raise ValueError("The relationship partition is incomplete.")

    sizes = [len(questionnaire_sets[set_id]) for set_id in expected_set_ids]
    if min(sizes) < 43 or max(sizes) > 45:
        raise ValueError("Every set must contain approximately 43–45 pairs.")

    for set_relationships in questionnaire_sets.values():
        sources = Counter(item.source_code for item in set_relationships)
        targets = Counter(item.target_code for item in set_relationships)
        if any(sources[code] not in {2, 3} for code in FACTOR_CODES):
            raise ValueError("Source-variable allocation is not balanced.")
        if any(targets[code] not in {2, 3} for code in FACTOR_CODES):
            raise ValueError("Target-variable allocation is not balanced.")


def get_questionnaire_set(set_id: int) -> tuple[DirectedRelationship, ...]:
    """Return one validated questionnaire set by ID."""

    try:
        return build_questionnaire_sets()[set_id]
    except KeyError as exc:
        raise ValueError(f"Unknown questionnaire set ID: {set_id}") from exc


def all_relationships() -> tuple[DirectedRelationship, ...]:
    """Return all relationships in stable source/target matrix order."""

    relationship_by_pair = {
        (item.source_code, item.target_code): item
        for relationships in build_questionnaire_sets().values()
        for item in relationships
    }
    return tuple(
        relationship_by_pair[(source, target)]
        for source in FACTOR_CODES
        for target in FACTOR_CODES
        if source != target
    )
