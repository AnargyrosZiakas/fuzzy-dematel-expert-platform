"""Scientific partition tests for the seven distributed questionnaire sets."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from config import FACTOR_CODES, REQUIRED_COMPARISONS
from questionnaire_sets import SET_ASSIGNMENT_MATRIX, build_questionnaire_sets


def test_sets_cover_every_directed_relationship_exactly_once() -> None:
    questionnaire_sets = build_questionnaire_sets()
    pairs = [
        (relationship.source_code, relationship.target_code)
        for relationships in questionnaire_sets.values()
        for relationship in relationships
    ]
    assert len(pairs) == REQUIRED_COMPARISONS
    assert len(set(pairs)) == REQUIRED_COMPARISONS
    assert all(source != target for source, target in pairs)
    assert set(pairs) == {
        (source, target)
        for source in FACTOR_CODES
        for target in FACTOR_CODES
        if source != target
    }


def test_set_sizes_and_source_target_roles_are_balanced() -> None:
    questionnaire_sets = build_questionnaire_sets()
    assert [len(questionnaire_sets[index]) for index in range(1, 8)] == [
        44,
        44,
        44,
        44,
        44,
        43,
        43,
    ]
    for relationships in questionnaire_sets.values():
        source_counts = Counter(item.source_code for item in relationships)
        target_counts = Counter(item.target_code for item in relationships)
        assert all(source_counts[code] in {2, 3} for code in FACTOR_CODES)
        assert all(target_counts[code] in {2, 3} for code in FACTOR_CODES)


def test_database_seed_matches_the_audited_python_partition() -> None:
    schema = Path("sql/schema.sql").read_text(encoding="utf-8")
    sql_rows = re.findall(r"\(\d+,\s+'([0-7]{18})'\)", schema)
    assert tuple(sql_rows) == SET_ASSIGNMENT_MATRIX
