"""Unit tests for Supabase bulk-write behavior."""

from __future__ import annotations

from typing import Any

import pytest

from config import TOTAL_CELLS
from database import (
    SubmissionError,
    SupabaseResponseRepository,
    SupabaseSettings,
)


class FakeQuery:
    def __init__(self) -> None:
        self.inserted: list[dict[str, Any]] | None = None
        self.returning: str | None = None
        self.executions = 0

    def insert(self, rows, returning: str):
        self.inserted = rows
        self.returning = returning
        return self

    def execute(self):
        self.executions += 1
        return {"data": None}


class FakeClient:
    def __init__(self) -> None:
        self.query = FakeQuery()
        self.table_name = ""

    def table(self, table_name: str) -> FakeQuery:
        self.table_name = table_name
        return self.query


def test_repository_uses_one_bulk_insert() -> None:
    client = FakeClient()
    settings = SupabaseSettings("https://example.supabase.co", "secret")
    repository = SupabaseResponseRepository(client, settings)
    rows = [
        {"submission_id": "same-id", "cell": index}
        for index in range(TOTAL_CELLS)
    ]

    repository.save_submission(rows)  # type: ignore[arg-type]

    assert client.table_name == "expert_responses"
    assert len(client.query.inserted or []) == TOTAL_CELLS
    assert client.query.returning == "minimal"
    assert client.query.executions == 1


def test_repository_rejects_partial_submission() -> None:
    client = FakeClient()
    repository = SupabaseResponseRepository(
        client, SupabaseSettings("https://example.supabase.co", "secret")
    )
    with pytest.raises(SubmissionError, match="expected 324"):
        repository.save_submission([])

