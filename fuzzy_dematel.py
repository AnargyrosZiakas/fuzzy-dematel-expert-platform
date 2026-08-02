"""Input adapters reserved for the future Fuzzy DEMATEL engine.

No DEMATEL calculations are implemented in this module. Its only purpose is to
lock in and validate the export contract so the later mathematical engine can
consume today's research data without a database migration.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from config import FACTOR_CODES
from export import ADMIN_RESPONSE_COLUMNS, LONG_COLUMNS
from questionnaire_sets import all_relationships


def load_long_export(path: str | Path) -> pd.DataFrame:
    """Read and validate a long CSV or long Excel export."""

    source = Path(path)
    if source.suffix.lower() == ".csv":
        frame = pd.read_csv(source)
    elif source.suffix.lower() in {".xlsx", ".xlsm"}:
        frame = pd.read_excel(source, sheet_name="Long_Data")
    else:
        raise ValueError("Use a .csv or .xlsx long-format export.")

    missing_columns = set(LONG_COLUMNS).difference(frame.columns)
    if missing_columns:
        raise ValueError(
            f"Long export is missing columns: {sorted(missing_columns)}"
        )
    if len(frame) != len(FACTOR_CODES) ** 2:
        raise ValueError("Long export must contain exactly 324 matrix cells.")
    if frame.duplicated(["from_factor", "to_factor"]).any():
        raise ValueError("Long export contains duplicate ordered factor pairs.")
    return frame[LONG_COLUMNS].copy()


def tfn_arrays_from_long(
    frame: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return ordered lower, modal, and upper 18×18 arrays without analysis."""

    arrays: list[np.ndarray] = []
    for value_column in ("tfn_l", "tfn_m", "tfn_u"):
        matrix = (
            frame.pivot(
                index="from_factor", columns="to_factor", values=value_column
            )
            .reindex(index=FACTOR_CODES, columns=FACTOR_CODES)
            .to_numpy(dtype=float)
        )
        if matrix.shape != (18, 18) or np.isnan(matrix).any():
            raise ValueError(f"Invalid {value_column} matrix in long export.")
        arrays.append(matrix)
    return arrays[0], arrays[1], arrays[2]


def load_wide_excel(
    path: str | Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Read the three numeric TFN sheets from a wide Excel export."""

    arrays: list[np.ndarray] = []
    for sheet_name in ("TFN_L", "TFN_M", "TFN_U"):
        frame = pd.read_excel(path, sheet_name=sheet_name, index_col=0)
        frame = frame.reindex(index=FACTOR_CODES, columns=FACTOR_CODES)
        matrix = frame.to_numpy(dtype=float)
        if matrix.shape != (18, 18) or np.isnan(matrix).any():
            raise ValueError(f"Invalid or incomplete {sheet_name} sheet.")
        arrays.append(matrix)
    return arrays[0], arrays[1], arrays[2]


def load_distributed_export(path: str | Path) -> pd.DataFrame:
    """Read raw multi-respondent set data without mathematical aggregation."""

    source = Path(path)
    if source.suffix.lower() == ".csv":
        frame = pd.read_csv(source)
    elif source.suffix.lower() in {".xlsx", ".xlsm"}:
        frame = pd.read_excel(source, sheet_name="Responses_Long")
    else:
        raise ValueError("Use a .csv or .xlsx distributed-response export.")

    missing_columns = set(ADMIN_RESPONSE_COLUMNS).difference(frame.columns)
    if missing_columns:
        raise ValueError(
            f"Distributed export is missing columns: {sorted(missing_columns)}"
        )
    if frame.duplicated(
        [
            "respondent_id",
            "source_variable_code",
            "target_variable_code",
        ]
    ).any():
        raise ValueError("A respondent has duplicate directed relationships.")
    if (
        frame["source_variable_code"] == frame["target_variable_code"]
    ).any():
        raise ValueError("Distributed exports cannot contain diagonal evaluations.")

    expected_set_by_pair = {
        (relationship.source_code, relationship.target_code): relationship.set_id
        for relationship in all_relationships()
    }
    for row in frame.itertuples(index=False):
        pair = (row.source_variable_code, row.target_variable_code)
        if expected_set_by_pair.get(pair) != int(row.set_id):
            raise ValueError("A response does not match the audited set partition.")
    return frame[ADMIN_RESPONSE_COLUMNS].copy()
