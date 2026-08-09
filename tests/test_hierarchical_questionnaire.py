"""Scientific-contract tests for the hierarchical Fuzzy DEMATEL design."""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from uuid import UUID

import numpy as np
import pandas as pd
import pytest

from config import HIERARCHICAL_REQUIRED_COMPARISONS, SCALE_ITEMS
from export import generate_hierarchical_administrator_exports
from fuzzy_dematel import (
    hierarchical_tfn_matrices_from_long,
    load_hierarchical_export,
)
from hierarchical_questionnaire import (
    all_hierarchical_relationships,
    matrix_definitions,
)
from models import HierarchicalQuestionnaireRecord
from validation import (
    build_hierarchical_response_record,
    validate_hierarchical_matrix,
    validate_hierarchical_questionnaire,
)


def test_exact_matrix_sizes_and_no_cross_dimension_pairs() -> None:
    matrices = matrix_definitions()
    assert [len(matrix.criteria) for matrix in matrices] == [6, 4, 8, 3]
    assert [matrix.required_comparisons for matrix in matrices] == [30, 12, 56, 6]
    relationships = all_hierarchical_relationships()
    assert len(relationships) == HIERARCHICAL_REQUIRED_COMPARISONS == 104
    assert len({relationship.key for relationship in relationships}) == 104
    assert all(
        relationship.source_code != relationship.target_code
        for relationship in relationships
    )

    level_one_prefixes = {"cultural": "C", "economic": "E", "strategic": "S"}
    for relationship in relationships:
        if relationship.matrix_id in level_one_prefixes:
            prefix = level_one_prefixes[relationship.matrix_id]
            assert relationship.source_code.startswith(prefix)
            assert relationship.target_code.startswith(prefix)
        else:
            assert relationship.source_code in {"C", "E", "S"}
            assert relationship.target_code in {"C", "E", "S"}


def test_exact_scale_labels_and_tfn_values() -> None:
    assert [(item.code, item.label, item.tfn) for item in SCALE_ITEMS] == [
        ("VL", "Very Low Influence", (0.0, 0.0, 0.25)),
        ("LI", "Low Influence", (0.0, 0.25, 0.5)),
        ("I", "Influence", (0.25, 0.5, 0.75)),
        ("HI", "High Influence", (0.5, 0.75, 1.0)),
        ("VH", "Very High Influence", (0.75, 1.0, 1.0)),
    ]


def test_hierarchical_validation_requires_all_104_answers() -> None:
    relationships = all_hierarchical_relationships()
    judgments = {relationship.key: "I" for relationship in relationships}
    result = validate_hierarchical_questionnaire(judgments)
    assert result.is_valid
    assert result.completed == result.required == 104
    judgments.pop(relationships[-1].key)
    result = validate_hierarchical_questionnaire(judgments)
    assert not result.is_valid
    assert result.completed == 103

    for matrix, required in zip(matrix_definitions(), (30, 12, 56, 6), strict=True):
        status = validate_hierarchical_matrix(matrix.id, judgments)
        assert status.required == required


@pytest.mark.parametrize("value", ["VL", "LI", "I", "HI", "VH"])
def test_all_five_values_build_analysis_ready_records(value: str) -> None:
    relationship = all_hierarchical_relationships()[0]
    record = build_hierarchical_response_record(
        respondent_id=UUID("12345678-1234-5678-1234-567812345678"),
        expert_code="EXP-TEST01",
        relationship=relationship,
        linguistic_value=value,
        responded_at=datetime(2026, 8, 2, 12, 0, tzinfo=UTC),
    )
    assert record["linguistic_value"] == value
    expected = next(item.tfn for item in SCALE_ITEMS if item.code == value)
    assert (record["tfn_l"], record["tfn_m"], record["tfn_u"]) == expected


def _completed_dataset():
    respondent_id = UUID("12345678-1234-5678-1234-567812345678")
    timestamp = datetime(2026, 8, 2, 12, 0, tzinfo=UTC)
    questionnaire = HierarchicalQuestionnaireRecord(
        respondent_id=str(respondent_id),
        expert_code="EXP-TEST01",
        design_version="hierarchical_v1",
        status="completed",
        started_at=timestamp.isoformat(),
        completed_at=timestamp.isoformat(),
    )
    responses = [
        build_hierarchical_response_record(
            respondent_id=respondent_id,
            expert_code="EXP-TEST01",
            relationship=relationship,
            linguistic_value=("VL", "LI", "I", "HI", "VH")[index % 5],
            responded_at=timestamp,
        )
        for index, relationship in enumerate(all_hierarchical_relationships())
    ]
    return responses, [questionnaire]


def test_hierarchical_export_round_trip_reconstructs_four_matrices(tmp_path) -> None:
    responses, questionnaires = _completed_dataset()
    bundle = generate_hierarchical_administrator_exports(
        responses, questionnaires, minimum_evaluations=1
    )
    csv_frame = pd.read_csv(BytesIO(bundle.responses_csv))
    assert len(csv_frame) == 104
    assert set(csv_frame["matrix_id"]) == {
        "cultural",
        "economic",
        "strategic",
        "dimension_level",
    }

    csv_path = tmp_path / "hierarchical.csv"
    csv_path.write_bytes(bundle.responses_csv)
    loaded = load_hierarchical_export(csv_path)
    matrices = hierarchical_tfn_matrices_from_long(
        loaded, questionnaires[0]["respondent_id"]
    )
    assert {key: values[0].shape for key, values in matrices.items()} == {
        "cultural": (6, 6),
        "economic": (4, 4),
        "strategic": (8, 8),
        "dimension_level": (3, 3),
    }
    for lower, modal, upper in matrices.values():
        assert np.all(np.diag(lower) == 0)
        assert np.all(lower <= modal)
        assert np.all(modal <= upper)

    book = pd.ExcelFile(BytesIO(bundle.complete_excel))
    assert book.sheet_names == [
        "Responses_Long",
        "Responses_Wide",
        "Relationship_Coverage",
        "Respondent_Summary",
        "Matrix_Summary",
        "Cultural_Counts",
        "Economic_Counts",
        "Strategic_Counts",
        "Dimension_Counts",
        "Criteria_Definitions",
        "Metadata",
    ]


def test_database_migration_documents_the_104_pair_contract() -> None:
    sql = Path("sql/hierarchical_migration.sql").read_text(encoding="utf-8")
    assert "hierarchical_questionnaires" in sql
    assert "hierarchical_relationships" in sql
    assert "hierarchical_responses" in sql
    assert "response_count <> 104" in sql
