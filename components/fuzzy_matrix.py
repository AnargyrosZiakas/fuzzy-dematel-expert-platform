"""Reusable, accessible hierarchical Fuzzy DEMATEL matrix components."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from html import escape

import streamlit as st

from config import SCALE_BY_CODE, SCALE_CODES, SCALE_ITEMS
from hierarchical_questionnaire import relationships_for_matrix
from models import HierarchicalRelationship, MatrixDefinition


def format_scale_option(code: str) -> str:
    """Return the full participant-facing label for a scale code."""

    item = SCALE_BY_CODE[code]
    return f"{item.code} — {item.label}"


def render_scale_reference() -> None:
    """Render the exact five linguistic choices without exposing calculations."""

    chips = "".join(
        f"<span class='scale-chip'><strong>{item.code}</strong> · "
        f"{escape(item.label)}</span>"
        for item in SCALE_ITEMS
    )
    st.markdown(
        f"<div class='scale-reference' aria-label='Influence scale'>{chips}</div>",
        unsafe_allow_html=True,
    )


def render_criteria_reference(matrix: MatrixDefinition) -> None:
    """Render a compact expandable definition list for the active matrix."""

    with st.expander("View criteria definitions", expanded=False):
        for criterion in matrix.criteria:
            st.markdown(
                "<div class='criterion-reference'>"
                f"<span class='factor-badge'>{escape(criterion.code)}</span>"
                f"<div><strong>{escape(criterion.name)}</strong><br>"
                f"<span>{escape(criterion.definition)}</span></div></div>",
                unsafe_allow_html=True,
            )


def _activate_relationship(key: str) -> None:
    st.session_state["active_relationship_key"] = key


def _active_relationship(
    matrix: MatrixDefinition,
    judgments: Mapping[str, str | None],
) -> HierarchicalRelationship:
    relationships = relationships_for_matrix(matrix.id)
    active_key = str(st.session_state.get("active_relationship_key", ""))
    for relationship in relationships:
        if relationship.key == active_key:
            return relationship
    relationship = next(
        (
            item
            for item in relationships
            if judgments.get(item.key) not in SCALE_CODES
        ),
        relationships[0],
    )
    st.session_state["active_relationship_key"] = relationship.key
    return relationship


def _axis_highlight_styles(
    matrix: MatrixDefinition, relationship: HierarchicalRelationship
) -> str:
    """Build narrowly scoped CSS for the active row, column, and cell."""

    row_selectors = [
        f".st-key-cell_{matrix.id}_{relationship.source_code}_{criterion.code} button"
        for criterion in matrix.criteria
        if criterion.code != relationship.source_code
    ]
    column_selectors = [
        f".st-key-cell_{matrix.id}_{criterion.code}_{relationship.target_code} button"
        for criterion in matrix.criteria
        if criterion.code != relationship.target_code
    ]
    active_selector = (
        f".st-key-cell_{matrix.id}_{relationship.source_code}_"
        f"{relationship.target_code} button"
    )
    axis_selectors = ",".join(row_selectors + column_selectors)
    return (
        "<style>"
        f"{axis_selectors}{{border-color:#7FB8B0;}}"
        f"{active_selector}{{outline:3px solid rgba(15,118,110,.28);"
        "outline-offset:1px;box-shadow:0 0 0 1px #0F766E;}}"
        "</style>"
    )


def _render_active_panel(
    relationship: HierarchicalRelationship,
    *,
    selected_value: str | None,
    on_change: Callable[..., None],
) -> None:
    selected_label = (
        format_scale_option(selected_value)
        if selected_value in SCALE_CODES
        else "Not answered"
    )
    st.markdown(
        "<div class='active-relationship-card'>"
        "<span class='active-kicker'>Current relationship</span>"
        f"<div class='active-code'>{escape(relationship.source_code)} "
        f"→ {escape(relationship.target_code)}</div>"
        "<div class='active-names'>"
        f"<strong>{escape(relationship.source_name)}</strong>"
        "<span>↓ influences ↓</span>"
        f"<strong>{escape(relationship.target_name)}</strong>"
        "</div>"
        f"<div class='active-selection'>Selected influence: "
        f"<strong>{escape(selected_label)}</strong></div></div>",
        unsafe_allow_html=True,
    )
    widget_key = (
        f"scale_selector_{relationship.matrix_id}_"
        f"{relationship.source_code}_{relationship.target_code}"
    )
    if widget_key not in st.session_state and selected_value in SCALE_CODES:
        st.session_state[widget_key] = selected_value
    st.radio(
        (
            f"How much does {relationship.source_code} influence "
            f"{relationship.target_code}?"
        ),
        SCALE_CODES,
        index=(
            SCALE_CODES.index(selected_value)
            if selected_value in SCALE_CODES
            else None
        ),
        format_func=format_scale_option,
        horizontal=True,
        key=widget_key,
        on_change=on_change,
        args=(relationship, widget_key),
    )


def render_fuzzy_matrix(
    matrix: MatrixDefinition,
    *,
    judgments: Mapping[str, str | None],
    on_change: Callable[..., None],
) -> HierarchicalRelationship:
    """Render one matrix with readable cell states and an active selector panel."""

    relationship_lookup = {
        (item.source_code, item.target_code): item
        for item in relationships_for_matrix(matrix.id)
    }
    active = _active_relationship(matrix, judgments)
    st.markdown(_axis_highlight_styles(matrix, active), unsafe_allow_html=True)
    minimum_grid_width = max(620, 110 * (len(matrix.criteria) + 1))
    st.markdown(
        "<style>"
        f".st-key-matrix_grid_{matrix.id} > "
        "div[data-testid='stLayoutWrapper']"
        f"{{min-width:{minimum_grid_width}px;}}"
        "</style>",
        unsafe_allow_html=True,
    )

    with st.container(key=f"relationship_panel_{matrix.id}"):
        _render_active_panel(
            active,
            selected_value=judgments.get(active.key),
            on_change=on_change,
        )

    st.caption(
        "Select a matrix cell, then choose its influence level above. Completed "
        "cells always display the saved acronym."
    )
    with st.container(key=f"matrix_grid_{matrix.id}"):
        header_columns = st.columns(
            [1.36] + [1.0] * len(matrix.criteria), gap="small"
        )
        with header_columns[0]:
            st.markdown(
                "<div class='axis-corner'>ROW<br><strong>CAUSE</strong></div>",
                unsafe_allow_html=True,
            )
        for column, criterion in zip(
            header_columns[1:], matrix.criteria, strict=True
        ):
            active_class = (
                " active-axis" if criterion.code == active.target_code else ""
            )
            with column:
                st.markdown(
                    f"<div class='matrix-axis-label{active_class}' "
                    f"title='{escape(criterion.name, quote=True)}'>"
                    f"{escape(criterion.code)}<small>AFFECTED</small></div>",
                    unsafe_allow_html=True,
                )

        for source in matrix.criteria:
            row_columns = st.columns(
                [1.36] + [1.0] * len(matrix.criteria), gap="small"
            )
            row_active_class = (
                " active-axis" if source.code == active.source_code else ""
            )
            completed_in_row = sum(
                judgments.get(
                    relationship_lookup[(source.code, target.code)].key
                )
                in SCALE_CODES
                for target in matrix.criteria
                if target.code != source.code
            )
            with row_columns[0]:
                st.markdown(
                    f"<div class='matrix-row-label{row_active_class}' "
                    f"title='{escape(source.name, quote=True)}'>"
                    f"<strong>{escape(source.code)}</strong>"
                    f"<small>CAUSE · {completed_in_row}/"
                    f"{len(matrix.criteria) - 1}</small></div>",
                    unsafe_allow_html=True,
                )
            for column, target in zip(
                row_columns[1:], matrix.criteria, strict=True
            ):
                with column:
                    if source.code == target.code:
                        st.button(
                            "—",
                            key=f"diagonal_{matrix.id}_{source.code}",
                            disabled=True,
                            help="Self-influence is not evaluated.",
                            use_container_width=True,
                        )
                        continue
                    relationship = relationship_lookup[(source.code, target.code)]
                    selected = judgments.get(relationship.key)
                    completed = selected in SCALE_CODES
                    st.button(
                        str(selected) if completed else "Select",
                        key=(
                            f"cell_{matrix.id}_{source.code}_{target.code}"
                        ),
                        type="primary" if completed else "secondary",
                        help=(
                            f"{source.code} → {target.code}: How much does "
                            f"{source.name} influence {target.name}?"
                        ),
                        on_click=_activate_relationship,
                        args=(relationship.key,),
                        use_container_width=True,
                    )
    return active
