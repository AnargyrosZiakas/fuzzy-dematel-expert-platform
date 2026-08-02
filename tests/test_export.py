"""Round-trip tests for long and wide research exports."""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from uuid import UUID

import numpy as np
import pandas as pd

from config import FACTOR_CODES, TOTAL_CELLS
from export import generate_exports, records_to_wide_dataframe
from fuzzy_dematel import load_long_export, load_wide_excel, tfn_arrays_from_long
from validation import build_response_records


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

