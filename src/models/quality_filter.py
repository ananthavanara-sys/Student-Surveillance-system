"""Quality filtering for detected faces."""
import logging
from dataclasses import dataclass
from typing import List

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class QualityMetrics:
    """Quality assessment metrics for a detected face."""
    
    size_ok: bool
    blur_score: float
    brightness_ok: bool
    pose_ok: bool
    is_acceptable: bool
    
    def __repr__(self) -> str:
        status = "PASS" if self.is_acceptable else "FAIL"
        return f"Quality({status}, blur={self.blur_score:.1f}, size={self.size_ok})"


class FaceQualityFilter:
    """Filter faces based on quality metrics."""
    
    def __init__(
        self,
        min_face_size: int = 60,
        blur_threshold: float = 100.0,
        max_yaw: float = 45.0,
        max_pitch: float = 30.0,
        min_brightness: int = 40,
        max_brightness: int = 220
    ):
        """Initialize quality filter.
        
        Args:
            min_face_size: Minimum face width/height in pixels
            blur_threshold: Minimum blur score (higher = sharper)
            max_yaw: Maximum head rotation left/right (degrees)
            max_pitch: Maximum head rotation up/down (degrees)
            min_brightness: Minimum average brightness
            max_brightness: Maximum average brightness
        """
        self.min_face_size = min_face_size
        self.blur_threshold = blur_threshold
        self.max_yaw = max_yaw
        self.max_pitch = max_pitch
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        
        logger.info(f"QualityFilter initialized (min_size={min_face_size}, "
                   f"blur_thresh={blur_threshold}, max_yaw={max_yaw})")
    
    def assess(self, detected_face) -> QualityMetrics:
        """Assess quality of a detected face.
        
        Args:
            detected_face: DetectedFace object
            
        Returns:
            QualityMetrics with assessment results
        """
        # Size check
        size_ok = (detected_face.width >= self.min_face_size and 
                  detected_face.height >= self.min_face_size)
        
        # Blur assessment
        blur_score = self._compute_blur_score(detected_face.image)
        
        # Brightness check
        brightness_ok = self._check_brightness(detected_face.image)
        
        # Pose check (using landmarks if available)
        pose_ok = self._check_pose(detected_face)
        
        # Overall acceptance
        is_acceptable = (size_ok and 
                        blur_score >= self.blur_threshold and
                        brightness_ok and 
                        pose_ok)
        
        return QualityMetrics(
            size_ok=size_ok,
            blur_score=blur_score,
            brightness_ok=brightness_ok,
            pose_ok=pose_ok,
            is_acceptable=is_acceptable
        )
    
    def filter(self, faces: List) -> List:
        """Filter list of faces, keeping only acceptable quality.
        
        Args:
            faces: List of DetectedFace objects
            
        Returns:
            Filtered list of DetectedFace objects
        """
        if not faces:
            return []
        
        accepted = []
        for face in faces:
            metrics = self.assess(face)
            if metrics.is_acceptable:
                accepted.append(face)
            else:
                logger.debug(f"Rejected face: {metrics}")
        
        logger.debug(f"Quality filter: {len(accepted)}/{len(faces)} faces accepted")
        return accepted
    
    def _compute_blur_score(self, image: np.ndarray) -> float:
        """Compute blur score using Laplacian variance.
        
        Args:
            image: Face image (BGR)
            
        Returns:
            Blur score (higher = sharper)
        """
        if image is None or image.size == 0:
            return 0.0
        
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Compute Laplacian variance
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()
        
        return float(variance)
    
    def _check_brightness(self, image: np.ndarray) -> bool:
        """Check if image brightness is acceptable.
        
        Args:
            image: Face image (BGR)
            
        Returns:
            True if brightness is acceptable
        """
        if image is None or image.size == 0:
            return False
        
        # Convert to grayscale and compute mean brightness
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        mean_brightness = np.mean(gray)
        
        return self.min_brightness <= mean_brightness <= self.max_brightness
    
    def _check_pose(self, detected_face) -> bool:
        """Check if face pose is acceptable (frontal).
        
        Args:
            detected_face: DetectedFace object
            
        Returns:
            True if pose is acceptable
        """
        # If no landmarks available, assume pose is OK
        if not hasattr(detected_face, 'landmarks') or detected_face.landmarks is None:
            return True
        
        landmarks = detected_face.landmarks
        if len(landmarks) < 5:
            return True
        
        # Use eye positions to estimate yaw
        left_eye = landmarks[0]
        right_eye = landmarks[1]
        nose = landmarks[2]
        
        # Calculate eye distance and nose position relative to eyes
        eye_distance = np.linalg.norm(right_eye - left_eye)
        eye_center = (left_eye + right_eye) / 2
        
        # Estimate yaw from nose position relative to eye center
        nose_offset = nose[0] - eye_center[0]
        yaw_estimate = abs(nose_offset / eye_distance) * 90  # Rough estimate
        
        # Estimate pitch from eye-nose vertical alignment
        nose_vertical_offset = abs(nose[1] - eye_center[1])
        pitch_estimate = (nose_vertical_offset / eye_distance) * 60  # Rough estimate
        
        pose_ok = (yaw_estimate <= self.max_yaw and 
                  pitch_estimate <= self.max_pitch)
        
        return pose_ok
    
    def get_stats(self) -> dict:
        """Get filter configuration stats."""
        return {
            'min_face_size': self.min_face_size,
            'blur_threshold': self.blur_threshold,
            'max_yaw': self.max_yaw,
            'max_pitch': self.max_pitch,
            'brightness_range': (self.min_brightness, self.max_brightness)
        }
