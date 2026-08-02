"""Small reusable helpers without UI or persistence dependencies."""

from __future__ import annotations

import logging
import secrets
import string


def configure_logging() -> None:
    """Configure concise production-safe application logging once."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def generate_anonymous_code() -> str:
    """Generate a non-identifying expert code using secure randomness."""

    alphabet = string.ascii_uppercase + string.digits
    token = "".join(secrets.choice(alphabet) for _ in range(8))
    return f"EXP-{token}"

