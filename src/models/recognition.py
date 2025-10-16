"""Face recognition using InsightFace ArcFace."""
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import numpy as np
from insightface.app import FaceAnalysis

from src.core.config import settings
from src.models.detection import DetectedFace

logger = logging.getLogger(__name__)


@dataclass
class StudentMatch:
    """Result of face recognition matching."""
    student_id: Optional[str]
    confidence: float
    embedding: np.ndarray
    is_match: bool

    def __repr__(self) -> str:
        if self.is_match:
            return f"Match(student_id={self.student_id}, confidence={self.confidence:.3f})"
        return f"NoMatch(confidence={self.confidence:.3f})"


class EmbeddingExtractor:
    """Extract face embeddings using ArcFace."""

    def __init__(self, use_gpu: bool = True):
        """Initialize embedding extractor.
        
        Args:
            use_gpu: Whether to use GPU acceleration
        """
        self.use_gpu = use_gpu
        self.model: Optional[FaceAnalysis] = None
        self._initialized = False
        self.embedding_dim = 512  # ArcFace produces 512-dim vectors

        logger.info(f"EmbeddingExtractor initialized (GPU: {use_gpu})")

    def _lazy_load(self) -> None:
        """Lazy load model on first use."""
        if self._initialized:
            return

        logger.info("Loading InsightFace model pack '%s'...", settings.recognition_model)

        providers = ["CUDAExecutionProvider"] if self.use_gpu else ["CPUExecutionProvider"]

        self.model = FaceAnalysis(
            name=settings.recognition_model,
            providers=providers,
            allowed_modules=['detection', 'recognition'],
            root=str(settings.model_cache_dir)
        )

        self.model.prepare(ctx_id=0 if self.use_gpu else -1)
        
        self._initialized = True
        logger.info("ArcFace model loaded successfully")

    def extract(self, face_image: np.ndarray) -> Optional[np.ndarray]:
        """Extract embedding from face image.
        
        Args:
            face_image: BGR face image as numpy array
            
        Returns:
            512-dim embedding vector or None if extraction fails
        """
        self._lazy_load()

        if face_image is None or face_image.size == 0:
            logger.warning("Empty face image provided")
            return None

        # Get embedding
        faces = self.model.get(face_image)
        
        if len(faces) == 0:
            logger.warning("No face found in provided image")
            return None

        # Return normalized embedding
        embedding = faces[0].normed_embedding
        return embedding.astype(np.float32)

    def extract_from_detected(self, detected_face: DetectedFace) -> Optional[np.ndarray]:
        """Extract embedding from DetectedFace object.
        
        Args:
            detected_face: DetectedFace object
            
        Returns:
            512-dim embedding vector or None
        """
        # Use pre-computed embedding if available
        if (hasattr(detected_face, 'insightface_face') and 
            detected_face.insightface_face is not None and
            hasattr(detected_face.insightface_face, 'normed_embedding')):
            return detected_face.insightface_face.normed_embedding.astype(np.float32)
        
        # Fallback to extracting from cropped image
        return self.extract(detected_face.image)

    def extract_batch(self, face_images: list[np.ndarray]) -> list[Optional[np.ndarray]]:
        """Extract embeddings from multiple faces.
        
        Args:
            face_images: List of face images
            
        Returns:
            List of embeddings (None for failed extractions)
        """
        return [self.extract(img) for img in face_images]


class FaceRecognizer:
    """Face recognition with similarity matching."""

    def __init__(self, similarity_threshold: float = 0.65):
        """Initialize recognizer.
        
        Args:
            similarity_threshold: Minimum cosine similarity for a match
        """
        self.extractor = EmbeddingExtractor(use_gpu=True)
        self.similarity_threshold = similarity_threshold
        self.enrolled_embeddings: dict[str, np.ndarray] = {}
        
        logger.info(f"FaceRecognizer initialized (threshold: {similarity_threshold})")

    def enroll(self, student_id: str, face_image: np.ndarray) -> bool:
        """Enroll a student by storing their face embedding.
        
        Args:
            student_id: Unique student identifier
            face_image: Face image to enroll
            
        Returns:
            True if enrollment successful, False otherwise
        """
        embedding = self.extractor.extract(face_image)
        
        if embedding is None:
            logger.error(f"Failed to extract embedding for student {student_id}")
            return False

        self.enrolled_embeddings[student_id] = embedding
        logger.info(f"Enrolled student {student_id}")
        return True

    def enroll_from_detected(self, student_id: str, detected_face: DetectedFace) -> bool:
        """Enroll from DetectedFace object.
        
        Args:
            student_id: Unique student identifier
            detected_face: DetectedFace object
            
        Returns:
            True if enrollment successful
        """
        embedding = self.extractor.extract_from_detected(detected_face)
        
        if embedding is None:
            logger.error(f"Failed to extract embedding for student {student_id}")
            return False

        self.enrolled_embeddings[student_id] = embedding
        logger.info(f"Enrolled student {student_id}")
        return True

    def recognize(self, face_image: np.ndarray) -> StudentMatch:
        """Recognize a face by matching against enrolled students.
        
        Args:
            face_image: Face image to recognize
            
        Returns:
            StudentMatch object with recognition result
        """
        # Extract embedding
        embedding = self.extractor.extract(face_image)
        
        if embedding is None:
            return StudentMatch(
                student_id=None,
                confidence=0.0,
                embedding=np.zeros(512, dtype=np.float32),
                is_match=False
            )

        # Find best match
        best_match_id = None
        best_similarity = 0.0

        for student_id, enrolled_emb in self.enrolled_embeddings.items():
            similarity = self._cosine_similarity(embedding, enrolled_emb)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match_id = student_id

        is_match = best_similarity >= self.similarity_threshold

        return StudentMatch(
            student_id=best_match_id if is_match else None,
            confidence=float(best_similarity),
            embedding=embedding,
            is_match=is_match
        )

    def recognize_from_detected(self, detected_face: DetectedFace) -> StudentMatch:
        """Recognize from DetectedFace object.
        
        Args:
            detected_face: DetectedFace object
            
        Returns:
            StudentMatch object
        """
        # Extract embedding
        embedding = self.extractor.extract_from_detected(detected_face)
        
        if embedding is None:
            return StudentMatch(
                student_id=None,
                confidence=0.0,
                embedding=np.zeros(512, dtype=np.float32),
                is_match=False
            )

        # Find best match
        best_match_id = None
        best_similarity = 0.0

        for student_id, enrolled_emb in self.enrolled_embeddings.items():
            similarity = self._cosine_similarity(embedding, enrolled_emb)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match_id = student_id

        is_match = best_similarity >= self.similarity_threshold

        return StudentMatch(
            student_id=best_match_id if is_match else None,
            confidence=float(best_similarity),
            embedding=embedding,
            is_match=is_match
        )

    @staticmethod
    def _cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings.
        
        Args:
            emb1: First embedding vector
            emb2: Second embedding vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        # Embeddings are already normalized, so dot product = cosine similarity
        return float(np.dot(emb1, emb2))

    def get_enrolled_count(self) -> int:
        """Get number of enrolled students."""
        return len(self.enrolled_embeddings)

    def clear_enrollments(self) -> None:
        """Clear all enrolled students."""
        self.enrolled_embeddings.clear()
        logger.info("Cleared all enrollments")
