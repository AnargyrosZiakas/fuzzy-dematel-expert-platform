"""Supabase persistence adapters for respondent sets and legacy matrices."""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from config import (
    DEFAULT_HIERARCHICAL_ASSIGNMENT_TABLE,
    DEFAULT_HIERARCHICAL_RESPONSE_TABLE,
    DEFAULT_SCHEMA_NAME,
    DEFAULT_TABLE_NAME,
    TOTAL_CELLS,
)
from hierarchical_questionnaire import all_hierarchical_relationships
from models import (
    AssignmentRecord,
    DistributedResponseRecord,
    HierarchicalQuestionnaireRecord,
    HierarchicalResponseRecord,
    ResponseRecord,
)
from questionnaire_sets import get_questionnaire_set

LOGGER = logging.getLogger(__name__)


class DatabaseConfigurationError(RuntimeError):
    """Raised when required Supabase settings are absent or malformed."""


class SubmissionError(RuntimeError):
    """Raised when a completed questionnaire cannot be persisted."""


class AssignmentError(RuntimeError):
    """Raised when an assignment cannot be created, loaded, or completed."""


class AutosaveError(RuntimeError):
    """Raised when an individual relationship response cannot be saved."""


@dataclass(frozen=True, slots=True)
class SupabaseSettings:
    """Connection details loaded from server-side secrets or environment."""

    url: str
    key: str
    table_name: str = DEFAULT_TABLE_NAME
    assignment_table: str = "questionnaire_assignments"
    hierarchical_assignment_table: str = DEFAULT_HIERARCHICAL_ASSIGNMENT_TABLE
    hierarchical_response_table: str = DEFAULT_HIERARCHICAL_RESPONSE_TABLE
    schema_name: str = DEFAULT_SCHEMA_NAME

    @classmethod
    def from_sources(
        cls, secrets_mapping: Mapping[str, Any] | None = None
    ) -> SupabaseSettings:
        """Load settings, preferring Streamlit secrets over environment values."""

        supplied = secrets_mapping or {}

        def read(name: str, default: str = "") -> str:
            value = supplied.get(name, os.getenv(name, default))
            return str(value).strip() if value is not None else ""

        url = read("SUPABASE_URL")
        key = read("SUPABASE_KEY")
        if not url or not key:
            raise DatabaseConfigurationError(
                "Supabase is not configured. Add SUPABASE_URL and SUPABASE_KEY "
                "to the server-side Streamlit secrets."
            )
        if not url.startswith("https://"):
            raise DatabaseConfigurationError(
                "SUPABASE_URL must be an HTTPS project URL."
            )
        return cls(
            url=url,
            key=key,
            table_name=read("SUPABASE_TABLE", DEFAULT_TABLE_NAME),
            assignment_table=read(
                "SUPABASE_ASSIGNMENTS_TABLE", "questionnaire_assignments"
            ),
            hierarchical_assignment_table=read(
                "SUPABASE_HIERARCHICAL_ASSIGNMENTS_TABLE",
                DEFAULT_HIERARCHICAL_ASSIGNMENT_TABLE,
            ),
            hierarchical_response_table=read(
                "SUPABASE_HIERARCHICAL_RESPONSES_TABLE",
                DEFAULT_HIERARCHICAL_RESPONSE_TABLE,
            ),
            schema_name=read("SUPABASE_SCHEMA", DEFAULT_SCHEMA_NAME),
        )


def _create_client(settings: SupabaseSettings) -> Any:
    """Create the optional Supabase client with friendly configuration errors."""

    try:
        from supabase import create_client
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise DatabaseConfigurationError(
            "The supabase package is not installed."
        ) from exc

    try:
        return create_client(settings.url, settings.key)
    except Exception as exc:  # pragma: no cover - remote client behavior
        raise DatabaseConfigurationError(
            "The Supabase client could not be initialized."
        ) from exc


def _response_data(response: Any) -> list[dict[str, Any]]:
    """Normalize Supabase and test-double responses into mapping rows."""

    if isinstance(response, dict):
        data = response.get("data")
    else:
        data = getattr(response, "data", None)
    if data is None:
        return []
    if isinstance(data, dict):
        return [dict(data)]
    return [dict(row) for row in data]


def _is_transient_database_error(error: BaseException) -> bool:
    """Return whether an exception chain represents a temporary network fault."""

    transient_names = {
        "ConnectError",
        "ConnectTimeout",
        "NetworkError",
        "PoolTimeout",
        "ReadError",
        "ReadTimeout",
        "RemoteProtocolError",
        "WriteError",
        "WriteTimeout",
    }
    current: BaseException | None = error
    visited: set[int] = set()
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        if isinstance(current, (ConnectionError, TimeoutError)):
            return True
        if current.__class__.__name__ in transient_names:
            return True
        current = current.__cause__ or current.__context__
    return False


def _execute_with_transient_retry[T](
    operation: Callable[[], T],
    *,
    attempts: int = 3,
) -> T:
    """Retry safe Supabase operations after short-lived connectivity failures."""

    last_error: BaseException | None = None
    for attempt in range(max(1, attempts)):
        try:
            return operation()
        except Exception as exc:
            last_error = exc
            if attempt >= attempts - 1 or not _is_transient_database_error(exc):
                raise
            time.sleep(0.3 * (2**attempt))
    raise RuntimeError(
        "Database operation failed without an exception."
    ) from last_error


class SupabaseResponseRepository:
    """Legacy adapter retained for reading historical complete matrices."""

    def __init__(self, client: Any, settings: SupabaseSettings) -> None:
        self._client = client
        self._settings = settings

    @classmethod
    def connect(cls, settings: SupabaseSettings) -> SupabaseResponseRepository:
        """Create a legacy repository without importing Supabase in tests."""

        return cls(client=_create_client(settings), settings=settings)

    def save_submission(self, records: Sequence[ResponseRecord]) -> None:
        """Persist one historical 324-cell matrix in a single request."""

        if len(records) != TOTAL_CELLS:
            raise SubmissionError(
                f"Refusing to store {len(records)} rows; expected {TOTAL_CELLS}."
            )
        submission_ids = {record["submission_id"] for record in records}
        if len(submission_ids) != 1:
            raise SubmissionError("All rows must have the same submission UUID.")

        try:
            query_root = self._client
            if self._settings.schema_name != DEFAULT_SCHEMA_NAME:
                query_root = self._client.schema(self._settings.schema_name)
            (
                query_root.table(self._settings.table_name)
                .insert(list(records), returning="minimal")
                .execute()
            )
        except Exception as exc:  # pragma: no cover - remote behavior
            LOGGER.exception("Legacy Supabase submission failed")
            raise SubmissionError("The legacy matrix could not be stored.") from exc


class DistributedQuestionnaireRepository:
    """Balanced assignment, autosave, completion, and administrator repository."""

    def __init__(self, client: Any, settings: SupabaseSettings) -> None:
        self._client = client
        self._settings = settings

    @classmethod
    def connect(
        cls, settings: SupabaseSettings
    ) -> DistributedQuestionnaireRepository:
        """Create a Supabase-backed distributed-questionnaire repository."""

        return cls(client=_create_client(settings), settings=settings)

    def _query_root(self) -> Any:
        if self._settings.schema_name == DEFAULT_SCHEMA_NAME:
            return self._client
        return self._client.schema(self._settings.schema_name)

    def assign_respondent(
        self, respondent_id: UUID, expert_code: str
    ) -> AssignmentRecord:
        """Atomically assign or return a respondent's balanced set."""

        try:
            response = (
                self._query_root()
                .rpc(
                    "assign_questionnaire_set",
                    {
                        "p_respondent_id": str(respondent_id),
                        "p_expert_code": expert_code,
                    },
                )
                .execute()
            )
            rows = _response_data(response)
            if len(rows) != 1:
                raise AssignmentError("The assignment service returned no set.")
            return AssignmentRecord(**rows[0])
        except AssignmentError:
            raise
        except Exception as exc:  # pragma: no cover - remote behavior
            LOGGER.exception("Questionnaire-set assignment failed")
            raise AssignmentError(
                "Your questionnaire set could not be assigned. Please try again."
            ) from exc

    def load_assignment(self, respondent_id: UUID) -> AssignmentRecord | None:
        """Load one existing assignment for refresh-safe resume."""

        try:
            response = (
                self._query_root()
                .table(self._settings.assignment_table)
                .select("*")
                .eq("respondent_id", str(respondent_id))
                .limit(1)
                .execute()
            )
            rows = _response_data(response)
            return AssignmentRecord(**rows[0]) if rows else None
        except Exception as exc:  # pragma: no cover - remote behavior
            LOGGER.exception("Unable to load respondent assignment")
            raise AssignmentError(
                "Saved questionnaire progress could not be loaded."
            ) from exc

    def load_responses(
        self, respondent_id: UUID
    ) -> list[DistributedResponseRecord]:
        """Load all autosaved relationships for one respondent."""

        try:
            response = (
                self._query_root()
                .table(self._settings.table_name)
                .select("*")
                .eq("submission_id", str(respondent_id))
                .eq("is_diagonal", False)
                .execute()
            )
            return [
                DistributedResponseRecord(**row)
                for row in _response_data(response)
            ]
        except Exception as exc:  # pragma: no cover - remote behavior
            LOGGER.exception("Unable to load respondent responses")
            raise AssignmentError(
                "Saved relationship responses could not be loaded."
            ) from exc

    def save_response(self, record: DistributedResponseRecord) -> None:
        """Upsert one validated response immediately for automatic progress save."""

        expected_pairs = {
            (item.source_code, item.target_code)
            for item in get_questionnaire_set(int(record["set_id"]))
        }
        pair = (record["from_factor"], record["to_factor"])
        if pair not in expected_pairs or pair[0] == pair[1]:
            raise AutosaveError("This relationship is not part of the assigned set.")

        try:
            (
                self._query_root()
                .table(self._settings.table_name)
                .upsert(
                    dict(record),
                    on_conflict="submission_id,from_factor,to_factor",
                    returning="minimal",
                )
                .execute()
            )
        except Exception as exc:  # pragma: no cover - remote behavior
            LOGGER.exception("Relationship autosave failed")
            raise AutosaveError(
                "This response could not be saved. Please retry before continuing."
            ) from exc

    def complete_assignment(self, respondent_id: UUID) -> AssignmentRecord:
        """Atomically verify every assigned response and mark completion."""

        try:
            response = (
                self._query_root()
                .rpc(
                    "complete_questionnaire_assignment",
                    {"p_respondent_id": str(respondent_id)},
                )
                .execute()
            )
            rows = _response_data(response)
            if len(rows) != 1:
                raise AssignmentError("Completion confirmation was not returned.")
            return AssignmentRecord(**rows[0])
        except AssignmentError:
            raise
        except Exception as exc:  # pragma: no cover - remote behavior
            LOGGER.exception("Questionnaire completion failed")
            raise SubmissionError(
                "Your completed set could not be submitted. Saved answers remain "
                "available; please retry."
            ) from exc

    def _fetch_all(self, table_name: str) -> list[dict[str, Any]]:
        """Read a complete table through deterministic PostgREST pagination."""

        rows: list[dict[str, Any]] = []
        page_size = 1000
        start = 0
        while True:
            response = (
                self._query_root()
                .table(table_name)
                .select("*")
                .range(start, start + page_size - 1)
                .execute()
            )
            page = _response_data(response)
            rows.extend(page)
            if len(page) < page_size:
                return rows
            start += page_size

    def fetch_all_assignments(self) -> list[AssignmentRecord]:
        """Return all assignments for administrator reporting."""

        try:
            return [
                AssignmentRecord(**row)
                for row in self._fetch_all(self._settings.assignment_table)
            ]
        except Exception as exc:  # pragma: no cover - remote behavior
            LOGGER.exception("Administrator assignment query failed")
            raise AssignmentError(
                "Assignment statistics could not be loaded."
            ) from exc

    def fetch_all_responses(self) -> list[DistributedResponseRecord]:
        """Return all distributed responses for administrator reporting/export."""

        try:
            return [
                DistributedResponseRecord(**row)
                for row in self._fetch_all(self._settings.table_name)
                if row.get("set_id") is not None and not row.get("is_diagonal")
            ]
        except Exception as exc:  # pragma: no cover - remote behavior
            LOGGER.exception("Administrator response query failed")
            raise AssignmentError("Response statistics could not be loaded.") from exc


class HierarchicalQuestionnaireRepository:
    """Persistence for the versioned four-matrix hierarchical questionnaire."""

    def __init__(self, client: Any, settings: SupabaseSettings) -> None:
        self._client = client
        self._settings = settings

    @classmethod
    def connect(
        cls, settings: SupabaseSettings
    ) -> HierarchicalQuestionnaireRepository:
        """Create a Supabase-backed hierarchical repository."""

        return cls(client=_create_client(settings), settings=settings)

    def _query_root(self) -> Any:
        if self._settings.schema_name == DEFAULT_SCHEMA_NAME:
            return self._client
        return self._client.schema(self._settings.schema_name)

    def start_questionnaire(
        self, respondent_id: UUID, expert_code: str
    ) -> HierarchicalQuestionnaireRecord:
        """Atomically create or return an anonymous questionnaire session."""

        try:
            response = _execute_with_transient_retry(
                lambda: self._query_root()
                .rpc(
                    "start_hierarchical_questionnaire",
                    {
                        "p_respondent_id": str(respondent_id),
                        "p_expert_code": expert_code,
                    },
                )
                .execute()
            )
            rows = _response_data(response)
            if len(rows) != 1:
                raise AssignmentError("The questionnaire service returned no session.")
            return HierarchicalQuestionnaireRecord(**rows[0])
        except AssignmentError:
            raise
        except Exception as exc:  # pragma: no cover - remote behavior
            LOGGER.exception("Hierarchical questionnaire start failed")
            if _is_transient_database_error(exc):
                raise AssignmentError(
                    "The secure research database is temporarily unavailable. "
                    "Please wait a moment and choose Retry secure connection."
                ) from exc
            raise AssignmentError(
                "Your questionnaire could not be started. Please try again."
            ) from exc

    def load_questionnaire(
        self, respondent_id: UUID
    ) -> HierarchicalQuestionnaireRecord | None:
        """Load one hierarchical session for refresh-safe recovery."""

        try:
            response = _execute_with_transient_retry(
                lambda: self._query_root()
                .table(self._settings.hierarchical_assignment_table)
                .select("*")
                .eq("respondent_id", str(respondent_id))
                .limit(1)
                .execute()
            )
            rows = _response_data(response)
            return HierarchicalQuestionnaireRecord(**rows[0]) if rows else None
        except Exception as exc:  # pragma: no cover - remote behavior
            LOGGER.exception("Unable to load hierarchical questionnaire")
            raise AssignmentError(
                "Saved questionnaire progress could not be loaded."
            ) from exc

    def load_responses(
        self, respondent_id: UUID
    ) -> list[HierarchicalResponseRecord]:
        """Load every autosaved hierarchical answer for one respondent."""

        try:
            response = _execute_with_transient_retry(
                lambda: self._query_root()
                .table(self._settings.hierarchical_response_table)
                .select("*")
                .eq("respondent_id", str(respondent_id))
                .execute()
            )
            return [
                HierarchicalResponseRecord(**row)
                for row in _response_data(response)
            ]
        except Exception as exc:  # pragma: no cover - remote behavior
            LOGGER.exception("Unable to load hierarchical responses")
            raise AssignmentError(
                "Saved relationship responses could not be loaded."
            ) from exc

    def save_response(self, record: HierarchicalResponseRecord) -> None:
        """Upsert one allowed answer immediately for automatic progress saving."""

        allowed_keys = {
            (
                relationship.matrix_id,
                relationship.source_code,
                relationship.target_code,
            )
            for relationship in all_hierarchical_relationships()
        }
        key = (
            record["matrix_id"],
            record["source_code"],
            record["target_code"],
        )
        if key not in allowed_keys or key[1] == key[2]:
            raise AutosaveError(
                "This relationship is not part of the hierarchical questionnaire."
            )
        try:
            _execute_with_transient_retry(
                lambda: self._query_root()
                .table(self._settings.hierarchical_response_table)
                .upsert(
                    dict(record),
                    on_conflict=(
                        "respondent_id,matrix_id,source_code,target_code"
                    ),
                    returning="minimal",
                )
                .execute()
            )
        except Exception as exc:  # pragma: no cover - remote behavior
            LOGGER.exception("Hierarchical relationship autosave failed")
            raise AutosaveError(
                "This response could not be saved. Please retry before continuing."
            ) from exc

    def complete_questionnaire(
        self, respondent_id: UUID
    ) -> HierarchicalQuestionnaireRecord:
        """Verify all 90 answers and atomically mark the session completed."""

        try:
            response = _execute_with_transient_retry(
                lambda: self._query_root()
                .rpc(
                    "complete_hierarchical_questionnaire",
                    {"p_respondent_id": str(respondent_id)},
                )
                .execute()
            )
            rows = _response_data(response)
            if len(rows) != 1:
                raise AssignmentError("Completion confirmation was not returned.")
            return HierarchicalQuestionnaireRecord(**rows[0])
        except AssignmentError:
            raise
        except Exception as exc:  # pragma: no cover - remote behavior
            LOGGER.exception("Hierarchical questionnaire completion failed")
            raise SubmissionError(
                "Your questionnaire could not be submitted. Saved answers remain "
                "available; please retry."
            ) from exc

    def _fetch_all(self, table_name: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        page_size = 1000
        start = 0
        while True:
            response = (
                self._query_root()
                .table(table_name)
                .select("*")
                .range(start, start + page_size - 1)
                .execute()
            )
            page = _response_data(response)
            rows.extend(page)
            if len(page) < page_size:
                return rows
            start += page_size

    def fetch_all_questionnaires(self) -> list[HierarchicalQuestionnaireRecord]:
        """Return all hierarchical sessions for administrator reporting."""

        try:
            return [
                HierarchicalQuestionnaireRecord(**row)
                for row in self._fetch_all(
                    self._settings.hierarchical_assignment_table
                )
            ]
        except Exception as exc:  # pragma: no cover - remote behavior
            LOGGER.exception("Administrator questionnaire query failed")
            raise AssignmentError(
                "Questionnaire statistics could not be loaded."
            ) from exc

    def fetch_all_responses(self) -> list[HierarchicalResponseRecord]:
        """Return all hierarchical answers for administrator reporting/export."""

        try:
            return [
                HierarchicalResponseRecord(**row)
                for row in self._fetch_all(self._settings.hierarchical_response_table)
            ]
        except Exception as exc:  # pragma: no cover - remote behavior
            LOGGER.exception("Administrator hierarchical response query failed")
            raise AssignmentError("Response statistics could not be loaded.") from exc

    def fetch_legacy_assignments(self) -> list[AssignmentRecord]:
        """Retain administrator access to historical seven-set assignments."""

        return [
            AssignmentRecord(**row)
            for row in self._fetch_all(self._settings.assignment_table)
        ]

    def load_legacy_assignment(
        self, respondent_id: UUID
    ) -> AssignmentRecord | None:
        """Load one pre-migration seven-set session without modifying it."""

        try:
            response = (
                self._query_root()
                .table(self._settings.assignment_table)
                .select("*")
                .eq("respondent_id", str(respondent_id))
                .limit(1)
                .execute()
            )
            rows = _response_data(response)
            return AssignmentRecord(**rows[0]) if rows else None
        except Exception as exc:  # pragma: no cover - remote behavior
            LOGGER.exception("Unable to load historical questionnaire")
            raise AssignmentError(
                "Saved historical questionnaire progress could not be loaded."
            ) from exc

    def fetch_legacy_responses(self) -> list[DistributedResponseRecord]:
        """Retain administrator access to historical seven-set answers."""

        return [
            DistributedResponseRecord(**row)
            for row in self._fetch_all(self._settings.table_name)
            if row.get("set_id") is not None and not row.get("is_diagonal")
        ]
