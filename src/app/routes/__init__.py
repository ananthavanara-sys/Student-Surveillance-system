"""Route modules for the FastAPI application."""
from . import analytics, enrollment, recognition, status, ui

__all__ = [
    "analytics",
    "enrollment",
    "recognition",
    "status",
    "ui",
]
