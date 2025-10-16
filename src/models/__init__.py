"""Models module for face detection, recognition, and quality filtering."""

from .detection import FaceDetector, DetectedFace
from .recognition import EmbeddingExtractor, FaceRecognizer, StudentMatch
from .quality_filter import FaceQualityFilter, QualityMetrics

__all__ = [
    "FaceDetector",
    "DetectedFace", 
    "EmbeddingExtractor",
    "FaceRecognizer",
    "StudentMatch",
    "FaceQualityFilter",
    "QualityMetrics"
]
