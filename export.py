"""Deterministic CSV and Excel exports for the future DEMATEL engine."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from io import BytesIO
from typing import Literal

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from config import FACTOR_CODES, load_factor_definitions
from models import ResponseRecord

LONG_COLUMNS = [
    "submission_id",
    "expert_code",
    "timestamp",
    "from_factor",
    "to_factor",
    "linguistic_value",
    "tfn_l",
    "tfn_m",
    "tfn_u",
    "is_diagonal",
]


@dataclass(frozen=True, slots=True)
class ExportBundle:
    """In-memory files generated for one submitted expert matrix."""

    long_csv: bytes
    wide_csv: bytes
    long_excel: bytes
    wide_excel: bytes


def records_to_long_dataframe(
    records: Sequence[ResponseRecord],
) -> pd.DataFrame:
    """Return a stable row-major long-format dataframe."""

    frame = pd.DataFrame.from_records(records, columns=LONG_COLUMNS)
    expected_rows = len(FACTOR_CODES) ** 2
    if len(frame) != expected_rows:
        raise ValueError(f"Expected {expected_rows} records; received {len(frame)}.")

    factor_order = {factor: index for index, factor in enumerate(FACTOR_CODES)}
    frame["_from_order"] = frame["from_factor"].map(factor_order)
    frame["_to_order"] = frame["to_factor"].map(factor_order)
    if frame[["_from_order", "_to_order"]].isna().any().any():
        raise ValueError("Records contain an unknown factor code.")
    frame = frame.sort_values(["_from_order", "_to_order"]).drop(
        columns=["_from_order", "_to_order"]
    )
    return frame.reset_index(drop=True)


def records_to_wide_dataframe(
    records: Sequence[ResponseRecord],
    value: Literal["linguistic_value", "tfn_l", "tfn_m", "tfn_u"],
) -> pd.DataFrame:
    """Pivot one canonical value into an ordered 18×18 wide matrix."""

    long_frame = records_to_long_dataframe(records)
    if long_frame.duplicated(["from_factor", "to_factor"]).any():
        raise ValueError("Duplicate ordered factor pairs cannot be exported.")

    wide = long_frame.pivot(
        index="from_factor", columns="to_factor", values=value
    ).reindex(index=FACTOR_CODES, columns=FACTOR_CODES)
    if wide.isna().any().any():
        raise ValueError("The wide matrix is missing one or more factor pairs.")
    wide.index.name = "from_factor"
    wide.columns.name = "to_factor"
    return wide


def _definitions_dataframe() -> pd.DataFrame:
    definitions = load_factor_definitions()
    return pd.DataFrame(
        {
            "factor_code": FACTOR_CODES,
            "full_definition": [definitions[code] for code in FACTOR_CODES],
        }
    )


def _metadata_dataframe(long_frame: pd.DataFrame) -> pd.DataFrame:
    first = long_frame.iloc[0]
    return pd.DataFrame(
        {
            "field": [
                "submission_id",
                "expert_code",
                "timestamp",
                "matrix_orientation",
                "off_diagonal_comparisons",
                "diagonal_rule",
            ],
            "value": [
                first["submission_id"],
                first["expert_code"],
                first["timestamp"],
                "ROW factor influences COLUMN factor",
                "306",
                "Fixed zero TFN (0.00, 0.00, 0.00)",
            ],
        }
    )


def _format_workbook(writer: pd.ExcelWriter) -> None:
    """Apply restrained, machine-safe formatting to every workbook sheet."""

    header_fill = PatternFill("solid", fgColor="163A5F")
    header_font = Font(color="FFFFFF", bold=True)
    for worksheet in writer.book.worksheets:
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions
        for cell in worksheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")
        for column_cells in worksheet.columns:
            max_length = min(
                60,
                max(
                    len(str(cell.value)) if cell.value is not None else 0
                    for cell in column_cells
                )
                + 2,
            )
            worksheet.column_dimensions[
                get_column_letter(column_cells[0].column)
            ].width = max(10, max_length)


def _dataframe_to_csv_bytes(frame: pd.DataFrame, *, index: bool) -> bytes:
    return frame.to_csv(index=index, lineterminator="\n").encode("utf-8-sig")


def _long_excel_bytes(long_frame: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        long_frame.to_excel(writer, sheet_name="Long_Data", index=False)
        _metadata_dataframe(long_frame).to_excel(
            writer, sheet_name="Metadata", index=False
        )
        _definitions_dataframe().to_excel(
            writer, sheet_name="Factor_Definitions", index=False
        )
        _format_workbook(writer)
    return buffer.getvalue()


def _wide_excel_bytes(
    long_frame: pd.DataFrame, records: Sequence[ResponseRecord]
) -> bytes:
    buffer = BytesIO()
    sheet_map = {
        "Linguistic": "linguistic_value",
        "TFN_L": "tfn_l",
        "TFN_M": "tfn_m",
        "TFN_U": "tfn_u",
    }
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for sheet_name, value_column in sheet_map.items():
            records_to_wide_dataframe(records, value_column).to_excel(
                writer, sheet_name=sheet_name, index=True
            )
        _metadata_dataframe(long_frame).to_excel(
            writer, sheet_name="Metadata", index=False
        )
        _definitions_dataframe().to_excel(
            writer, sheet_name="Factor_Definitions", index=False
        )
        _format_workbook(writer)
    return buffer.getvalue()


def generate_exports(records: Sequence[ResponseRecord]) -> ExportBundle:
    """Generate CSV and Excel files in both long and wide layouts."""

    long_frame = records_to_long_dataframe(records)
    linguistic_wide = records_to_wide_dataframe(records, "linguistic_value")
    return ExportBundle(
        long_csv=_dataframe_to_csv_bytes(long_frame, index=False),
        wide_csv=_dataframe_to_csv_bytes(linguistic_wide, index=True),
        long_excel=_long_excel_bytes(long_frame),
        wide_excel=_wide_excel_bytes(long_frame, records),
    )

