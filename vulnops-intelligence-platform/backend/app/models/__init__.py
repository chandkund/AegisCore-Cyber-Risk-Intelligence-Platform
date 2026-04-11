"""ORM models: import side effects register metadata with Base."""

from app.models import (
    oltp,  # noqa: F401
    reporting,  # noqa: F401
)

__all__ = ["oltp", "reporting"]
