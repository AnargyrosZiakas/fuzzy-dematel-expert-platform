"""Round-trip tests for long and wide research exports."""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from uuid import UUID

import numpy as np
import pandas as pd

from config import FACTOR_CODES, TOTAL_CELLS
from export import (
    generate_administrator_exports,
    generate_exports,
    records_to_wide_dataframe,
)
from fuzzy_dematel import (
    load_distributed_export,
    load_long_export,
    load_wide_excel,
    tfn_arrays_from_long,
)
from models import AssignmentRecord, DistributedResponseRecord
from questionnaire_sets import get_questionnaire_set
from validation import build_distributed_response_record, build_response_records


def _records(complete_judgments: dict[str, str]):
    return build_response_records(
        submission_id=UUID("12345678-1234-5678-1234-567812345678"),
        expert_code="EXP-TEST01",
        judgments=complete_judgments,
        submitted_at=datetime(2026, 8, 2, 12, 0, tzinfo=UTC),
    )


def test_wide_matrix_has_exact_order_and_shape(
    complete_judgments: dict[str, str],
) -> None:
    wide = records_to_wide_dataframe(_records(complete_judgments), "tfn_m")
    assert wide.shape == (18, 18)
    assert list(wide.index) == list(FACTOR_CODES)
    assert list(wide.columns) == list(FACTOR_CODES)
    assert np.diag(wide.to_numpy(dtype=float)).tolist() == [0.0] * 18


def test_export_bundle_is_readable(
    complete_judgments: dict[str, str], tmp_path
) -> None:
    records = _records(complete_judgments)
    bundle = generate_exports(records)

    long_csv = pd.read_csv(BytesIO(bundle.long_csv))
    wide_csv = pd.read_csv(BytesIO(bundle.wide_csv), index_col=0)
    assert len(long_csv) == TOTAL_CELLS
    assert wide_csv.shape == (18, 18)

    long_path = tmp_path / "long.csv"
    long_path.write_bytes(bundle.long_csv)
    long_frame = load_long_export(long_path)
    lower, modal, upper = tfn_arrays_from_long(long_frame)
    assert lower.shape == modal.shape == upper.shape == (18, 18)
    assert np.all(lower <= modal)
    assert np.all(modal <= upper)

    wide_path = tmp_path / "wide.xlsx"
    wide_path.write_bytes(bundle.wide_excel)
    excel_lower, excel_modal, excel_upper = load_wide_excel(wide_path)
    assert np.array_equal(lower, excel_lower)
    assert np.array_equal(modal, excel_modal)
    assert np.array_equal(upper, excel_upper)


def test_excel_workbooks_contain_documented_sheets(
    complete_judgments: dict[str, str],
) -> None:
    bundle = generate_exports(_records(complete_judgments))
    long_book = pd.ExcelFile(BytesIO(bundle.long_excel))
    wide_book = pd.ExcelFile(BytesIO(bundle.wide_excel))
    assert long_book.sheet_names == ["Long_Data", "Metadata", "Factor_Definitions"]
    assert wide_book.sheet_names == [
        "Linguistic",
        "TFN_L",
        "TFN_M",
        "TFN_U",
        "Metadata",
        "Factor_Definitions",
    ]


def _distributed_dataset() -> tuple[
    list[DistributedResponseRecord], list[AssignmentRecord]
]:
    responses: list[DistributedResponseRecord] = []
    assignments: list[AssignmentRecord] = []
    timestamp = datetime(2026, 8, 2, 12, 0, tzinfo=UTC)
    for set_id in range(1, 8):
        respondent_id = UUID(f"00000000-0000-0000-0000-{set_id:012d}")
        assignments.append(
            AssignmentRecord(
                respondent_id=str(respondent_id),
                expert_code=f"EXP-SET{set_id}",
                set_id=set_id,
                status="completed",
                started_at=timestamp.isoformat(),
                completed_at=timestamp.isoformat(),
            )
        )
        responses.extend(
            build_distributed_response_record(
                respondent_id=respondent_id,
                expert_code=f"EXP-SET{set_id}",
                relationship=relationship,
                linguistic_value="I",
                responded_at=timestamp,
            )
            for relationship in get_questionnaire_set(set_id)
        )
    return responses, assignments


def test_administrator_export_reconstructs_complete_relationship_design(
    tmp_path,
) -> None:
    responses, assignments = _distributed_dataset()
    bundle = generate_administrator_exports(
        responses,
        assignments,
        minimum_evaluations=1,
    )
    csv_frame = pd.read_csv(BytesIO(bundle.responses_csv))
    assert len(csv_frame) == 306
    assert not (
        csv_frame["source_variable_code"]
        == csv_frame["target_variable_code"]
    ).any()

    csv_path = tmp_path / "distributed.csv"
    csv_path.write_bytes(bundle.responses_csv)
    loaded = load_distributed_export(csv_path)
    assert len(loaded) == 306

    book = pd.ExcelFile(BytesIO(bundle.complete_excel))
    assert book.sheet_names == [
        "Responses_Long",
        "Relationship_Coverage",
        "Evaluation_Count_Matrix",
        "Set_Summary",
        "Factor_Definitions",
        "Metadata",
    ]
    count_matrix = pd.read_excel(
        BytesIO(bundle.complete_excel),
        sheet_name="Evaluation_Count_Matrix",
        index_col=0,
    )
    assert count_matrix.shape == (18, 18)
    assert np.diag(count_matrix.to_numpy()).tolist() == [0] * 18
    assert (count_matrix.to_numpy().sum() == 306)
