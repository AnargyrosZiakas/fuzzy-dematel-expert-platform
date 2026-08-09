"""Unit tests for Supabase bulk-write behavior."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest

from config import TOTAL_CELLS
from database import (
    AutosaveError,
    DistributedQuestionnaireRepository,
    HierarchicalQuestionnaireRepository,
    SubmissionError,
    SupabaseResponseRepository,
    SupabaseSettings,
)
from hierarchical_questionnaire import all_hierarchical_relationships
from questionnaire_sets import get_questionnaire_set
from validation import (
    build_distributed_response_record,
    build_hierarchical_response_record,
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


class FakeDistributedQuery:
    def __init__(self, data=None) -> None:
        self.data = data or []
        self.upserted = None
        self.on_conflict = None

    def upsert(self, row, on_conflict: str, returning: str):
        self.upserted = row
        self.on_conflict = on_conflict
        assert returning == "minimal"
        return self

    def execute(self):
        return {"data": self.data}


class FakeDistributedClient:
    def __init__(self) -> None:
        self.query = FakeDistributedQuery()
        self.rpc_name = ""
        self.rpc_params = {}

    def table(self, _table_name: str) -> FakeDistributedQuery:
        return self.query

    def rpc(self, name: str, params: dict[str, Any]) -> FakeDistributedQuery:
        self.rpc_name = name
        self.rpc_params = params
        return self.query


def test_distributed_repository_assigns_through_atomic_rpc() -> None:
    respondent_id = UUID("12345678-1234-5678-1234-567812345678")
    client = FakeDistributedClient()
    client.query.data = [
        {
            "respondent_id": str(respondent_id),
            "expert_code": "EXP-TEST01",
            "set_id": 4,
            "status": "in_progress",
            "started_at": "2026-08-02T12:00:00+00:00",
            "completed_at": None,
        }
    ]
    repository = DistributedQuestionnaireRepository(
        client, SupabaseSettings("https://example.supabase.co", "secret")
    )
    assignment = repository.assign_respondent(respondent_id, "EXP-TEST01")
    assert assignment["set_id"] == 4
    assert client.rpc_name == "assign_questionnaire_set"
    assert client.rpc_params["p_respondent_id"] == str(respondent_id)


def test_distributed_repository_autosaves_only_assigned_pair() -> None:
    respondent_id = UUID("12345678-1234-5678-1234-567812345678")
    relationship = get_questionnaire_set(1)[0]
    record = build_distributed_response_record(
        respondent_id=respondent_id,
        expert_code="EXP-TEST01",
        relationship=relationship,
        linguistic_value="VH",
    )
    client = FakeDistributedClient()
    repository = DistributedQuestionnaireRepository(
        client, SupabaseSettings("https://example.supabase.co", "secret")
    )
    repository.save_response(record)
    assert client.query.upserted["linguistic_value"] == "VH"
    assert client.query.on_conflict == "submission_id,from_factor,to_factor"

    invalid_record = dict(record)
    invalid_record["to_factor"] = relationship.source_code
    with pytest.raises(AutosaveError, match="not part"):
        repository.save_response(invalid_record)  # type: ignore[arg-type]


def test_hierarchical_repository_starts_and_autosaves_allowed_pair() -> None:
    respondent_id = UUID("12345678-1234-5678-1234-567812345678")
    client = FakeDistributedClient()
    client.query.data = [
        {
            "respondent_id": str(respondent_id),
            "expert_code": "EXP-TEST01",
            "design_version": "hierarchical_v1",
            "status": "in_progress",
            "started_at": "2026-08-02T12:00:00+00:00",
            "completed_at": None,
        }
    ]
    repository = HierarchicalQuestionnaireRepository(
        client, SupabaseSettings("https://example.supabase.co", "secret")
    )
    questionnaire = repository.start_questionnaire(respondent_id, "EXP-TEST01")
    assert questionnaire["design_version"] == "hierarchical_v1"
    assert client.rpc_name == "start_hierarchical_questionnaire"

    relationship = all_hierarchical_relationships()[0]
    record = build_hierarchical_response_record(
        respondent_id=respondent_id,
        expert_code="EXP-TEST01",
        relationship=relationship,
        linguistic_value="VH",
    )
    repository.save_response(record)
    assert client.query.upserted["matrix_id"] == "cultural"
    assert client.query.upserted["linguistic_value"] == "VH"
    assert client.query.on_conflict == (
        "respondent_id,matrix_id,source_code,target_code"
    )
