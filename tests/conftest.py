"""Shared deterministic test fixtures."""

from __future__ import annotations

import pytest

from config import FACTOR_CODES
from validation import comparison_key


@pytest.fixture
def complete_judgments() -> dict[str, str]:
    """Return a complete, non-uniform set of 306 valid judgments."""

    scale = ("VL", "LI", "I", "HI", "VH")
    return {
        comparison_key(from_factor, to_factor): scale[(row + column) % len(scale)]
        for row, from_factor in enumerate(FACTOR_CODES)
        for column, to_factor in enumerate(FACTOR_CODES)
        if from_factor != to_factor
    }

