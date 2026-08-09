"""Application-service composition for Streamlit and Supabase."""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any

import streamlit as st

from config import MIN_EVALUATIONS_DEFAULT
from database import HierarchicalQuestionnaireRepository, SupabaseSettings


def server_secrets() -> dict[str, Any]:
    """Return server-side Streamlit secrets without leaking them to the UI."""

    try:
        return dict(st.secrets)
    except Exception:
        return {}


@st.cache_resource(show_spinner=False)
def _connect_repository(
    url: str,
    key: str,
    table_name: str,
    assignment_table: str,
    hierarchical_assignment_table: str,
    hierarchical_response_table: str,
    schema_name: str,
) -> HierarchicalQuestionnaireRepository:
    settings = SupabaseSettings(
        url=url,
        key=key,
        table_name=table_name,
        assignment_table=assignment_table,
        hierarchical_assignment_table=hierarchical_assignment_table,
        hierarchical_response_table=hierarchical_response_table,
        schema_name=schema_name,
    )
    return HierarchicalQuestionnaireRepository.connect(settings)


def get_repository() -> HierarchicalQuestionnaireRepository:
    """Return the cached production questionnaire repository."""

    settings = SupabaseSettings.from_sources(server_secrets())
    return _connect_repository(
        settings.url,
        settings.key,
        settings.table_name,
        settings.assignment_table,
        settings.hierarchical_assignment_table,
        settings.hierarchical_response_table,
        settings.schema_name,
    )


def minimum_evaluations() -> int:
    """Return the administrator coverage threshold, bounded to at least one."""

    supplied = server_secrets().get(
        "MIN_EVALUATIONS_PER_RELATIONSHIP",
        os.getenv("MIN_EVALUATIONS_PER_RELATIONSHIP", MIN_EVALUATIONS_DEFAULT),
    )
    try:
        return max(1, int(supplied))
    except (TypeError, ValueError):
        return MIN_EVALUATIONS_DEFAULT


def administrator_password_is_configured() -> bool:
    """Whether either supported administrator credential is configured."""

    secrets = server_secrets()
    return bool(
        secrets.get("ADMIN_PASSWORD")
        or secrets.get("ADMIN_PASSWORD_SHA256")
        or os.getenv("ADMIN_PASSWORD")
        or os.getenv("ADMIN_PASSWORD_SHA256")
    )


def verify_administrator_password(candidate: str) -> bool:
    """Compare an administrator password using constant-time checks."""

    secrets = server_secrets()
    plain = str(
        secrets.get("ADMIN_PASSWORD", os.getenv("ADMIN_PASSWORD", ""))
    )
    expected_hash = str(
        secrets.get(
            "ADMIN_PASSWORD_SHA256",
            os.getenv("ADMIN_PASSWORD_SHA256", ""),
        )
    ).lower()
    if plain:
        return hmac.compare_digest(candidate, plain)
    if expected_hash:
        candidate_hash = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
        return hmac.compare_digest(candidate_hash, expected_hash)
    return False
