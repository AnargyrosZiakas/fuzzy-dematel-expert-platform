"""Supabase persistence adapter for complete expert matrices."""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from config import DEFAULT_SCHEMA_NAME, DEFAULT_TABLE_NAME, TOTAL_CELLS
from models import ResponseRecord

LOGGER = logging.getLogger(__name__)


class DatabaseConfigurationError(RuntimeError):
    """Raised when required Supabase settings are absent or malformed."""


class SubmissionError(RuntimeError):
    """Raised when a complete matrix cannot be persisted."""


@dataclass(frozen=True, slots=True)
class SupabaseSettings:
    """Connection details loaded from server-side secrets or environment."""

    url: str
    key: str
    table_name: str = DEFAULT_TABLE_NAME
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
            schema_name=read("SUPABASE_SCHEMA", DEFAULT_SCHEMA_NAME),
        )


class SupabaseResponseRepository:
    """Write-only repository that persists one complete matrix atomically."""

    def __init__(self, client: Any, settings: SupabaseSettings) -> None:
        self._client = client
        self._settings = settings

    @classmethod
    def connect(cls, settings: SupabaseSettings) -> SupabaseResponseRepository:
        """Create a repository without importing Supabase during unit tests."""

        try:
            from supabase import create_client
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise DatabaseConfigurationError(
                "The supabase package is not installed."
            ) from exc

        try:
            client = create_client(settings.url, settings.key)
        except Exception as exc:  # pragma: no cover - remote client behavior
            raise DatabaseConfigurationError(
                "The Supabase client could not be initialized."
            ) from exc
        return cls(client=client, settings=settings)

    def save_submission(self, records: Sequence[ResponseRecord]) -> None:
        """Insert all 324 cells in a single Supabase/PostgREST request.

        A single bulk insert is transactional in PostgreSQL: either the whole
        matrix is stored or no rows are stored. The database constraints in
        ``sql/schema.sql`` provide a second validation boundary.
        """

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
            LOGGER.info(
                "Stored complete expert matrix submission_id=%s",
                next(iter(submission_ids)),
            )
        except Exception as exc:  # pragma: no cover - remote behavior
            LOGGER.exception("Supabase submission failed")
            raise SubmissionError(
                "The response could not be stored. Your answers remain in this "
                "browser session; please retry."
            ) from exc

