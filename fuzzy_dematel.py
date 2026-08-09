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
from export import (
    ADMIN_RESPONSE_COLUMNS,
    HIERARCHICAL_RESPONSE_COLUMNS,
    LONG_COLUMNS,
)
from hierarchical_questionnaire import (
    all_hierarchical_relationships,
    matrix_definitions,
)
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


def load_hierarchical_export(path: str | Path) -> pd.DataFrame:
    """Read and validate raw four-matrix responses without aggregating them."""

    source = Path(path)
    if source.suffix.lower() == ".csv":
        frame = pd.read_csv(source)
    elif source.suffix.lower() in {".xlsx", ".xlsm"}:
        frame = pd.read_excel(source, sheet_name="Responses_Long")
    else:
        raise ValueError("Use a .csv or .xlsx hierarchical-response export.")

    missing_columns = set(HIERARCHICAL_RESPONSE_COLUMNS).difference(frame.columns)
    if missing_columns:
        raise ValueError(
            f"Hierarchical export is missing columns: {sorted(missing_columns)}"
        )
    duplicate_columns = [
        "respondent_id",
        "matrix_id",
        "source_code",
        "target_code",
    ]
    if frame.duplicated(duplicate_columns).any():
        raise ValueError("A respondent has duplicate hierarchical relationships.")
    allowed = {
        (
            relationship.matrix_id,
            relationship.source_code,
            relationship.target_code,
        )
        for relationship in all_hierarchical_relationships()
    }
    observed = set(
        zip(
            frame["matrix_id"],
            frame["source_code"],
            frame["target_code"],
            strict=True,
        )
    )
    if not observed.issubset(allowed):
        raise ValueError(
            "Export contains a diagonal, cross-dimensional, or unknown relationship."
        )
    return frame[HIERARCHICAL_RESPONSE_COLUMNS].copy()


def hierarchical_tfn_matrices_from_long(
    frame: pd.DataFrame,
    respondent_id: str,
) -> dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Reconstruct the four TFN matrices for one completed anonymous expert."""

    respondent = frame[frame["respondent_id"].astype(str) == str(respondent_id)]
    result: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for matrix in matrix_definitions():
        subset = respondent[respondent["matrix_id"] == matrix.id]
        if len(subset) != matrix.required_comparisons:
            raise ValueError(
                f"Respondent is missing answers in the {matrix.id} matrix."
            )
        codes = [criterion.code for criterion in matrix.criteria]
        arrays: list[np.ndarray] = []
        for value_column in ("tfn_l", "tfn_m", "tfn_u"):
            wide = subset.pivot(
                index="source_code",
                columns="target_code",
                values=value_column,
            ).reindex(index=codes, columns=codes)
            for code in codes:
                wide.loc[code, code] = 0.0
            values = wide.to_numpy(dtype=float)
            if values.shape != (len(codes), len(codes)) or np.isnan(values).any():
                raise ValueError(f"Invalid {matrix.id} {value_column} matrix.")
            arrays.append(values)
        result[matrix.id] = (arrays[0], arrays[1], arrays[2])
    return result
