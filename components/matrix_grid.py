"""Fixed 18×18 Fuzzy DEMATEL matrix component."""

from __future__ import annotations

from html import escape

import streamlit as st

from config import FACTOR_CODES, SCALE_CODES, SCALE_ITEMS, load_factor_definitions
from validation import comparison_key


def _widget_key(from_factor: str, to_factor: str) -> str:
    return f"judgment_{from_factor}_{to_factor}"


def _store_judgment(
    from_factor: str, to_factor: str, widget_key: str
) -> None:
    """Mirror ephemeral widget values into durable session state."""

    judgments = dict(st.session_state.get("judgments", {}))
    judgments[comparison_key(from_factor, to_factor)] = st.session_state.get(
        widget_key
    )
    st.session_state["judgments"] = judgments


def _factor_label(code: str, definition: str, row_count: str = "") -> str:
    suffix = f"<div class='row-progress'>{row_count}</div>" if row_count else ""
    return (
        f"<span class='factor-code' title='{escape(definition, quote=True)}'>"
        f"{escape(code)}</span>{suffix}"
    )


def render_scale_legend() -> None:
    """Render the exact five-level linguistic-to-TFN mapping."""

    chips = "".join(
        (
            f"<span class='scale-chip'><strong>{item.code}</strong> · "
            f"{item.label} · ({item.lower:.2f}, {item.modal:.2f}, "
            f"{item.upper:.2f})</span>"
        )
        for item in SCALE_ITEMS
    )
    st.markdown(chips, unsafe_allow_html=True)


def render_matrix_grid() -> None:
    """Render 306 dropdowns and 18 non-editable zero diagonal cells."""

    definitions = load_factor_definitions()
    judgments: dict[str, str | None] = st.session_state["judgments"]
    display_labels = {item.code: item.code for item in SCALE_ITEMS}

    with st.container(key="matrix_grid"):
        header_columns = st.columns([1.22] + [1.0] * len(FACTOR_CODES), gap="small")
        with header_columns[0]:
            st.markdown("**ROW ↓ / COLUMN →**")
        for column, to_factor in zip(
            header_columns[1:], FACTOR_CODES, strict=True
        ):
            with column:
                st.markdown(
                    _factor_label(to_factor, definitions[to_factor]),
                    unsafe_allow_html=True,
                )

        for from_factor in FACTOR_CODES:
            completed_in_row = sum(
                judgments.get(comparison_key(from_factor, to_factor))
                in SCALE_CODES
                for to_factor in FACTOR_CODES
                if to_factor != from_factor
            )
            row_columns = st.columns(
                [1.22] + [1.0] * len(FACTOR_CODES), gap="small"
            )
            with row_columns[0]:
                st.markdown(
                    _factor_label(
                        from_factor,
                        definitions[from_factor],
                        f"{completed_in_row}/17",
                    ),
                    unsafe_allow_html=True,
                )
            for column, to_factor in zip(
                row_columns[1:], FACTOR_CODES, strict=True
            ):
                with column:
                    accessible_label = (
                        f"How much does {from_factor} influence {to_factor}?"
                    )
                    if from_factor == to_factor:
                        st.text_input(
                            accessible_label,
                            value="N/A",
                            key=f"diagonal_{from_factor}",
                            disabled=True,
                            label_visibility="collapsed",
                            help="Diagonal comparisons are fixed at zero.",
                        )
                        continue

                    pair_key = comparison_key(from_factor, to_factor)
                    widget_key = _widget_key(from_factor, to_factor)
                    stored_value = judgments.get(pair_key)
                    selected_index = (
                        SCALE_CODES.index(stored_value)
                        if stored_value in SCALE_CODES
                        else None
                    )
                    st.selectbox(
                        accessible_label,
                        options=SCALE_CODES,
                        index=selected_index,
                        format_func=lambda code, labels=display_labels: labels[code],
                        placeholder="Select",
                        key=widget_key,
                        on_change=_store_judgment,
                        args=(from_factor, to_factor, widget_key),
                        label_visibility="collapsed",
                        help=" · ".join(
                            f"{item.code}: {item.label}" for item in SCALE_ITEMS
                        ),
                    )
