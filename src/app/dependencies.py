"""Shared dependency utilities for FastAPI routers."""
from __future__ import annotations

from functools import lru_cache

from src.face_system_db import FaceRecognitionSystemDB


@lru_cache(maxsize=1)
def get_face_system() -> FaceRecognitionSystemDB:
    """Return a singleton instance of the face recognition system with database support."""
    return FaceRecognitionSystemDB(use_db=True)
