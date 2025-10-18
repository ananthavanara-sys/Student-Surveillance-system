"""
Face recognition system using InsightFace ArcFace with PostgreSQL database.
Database-powered version of the face recognition system.
"""
import logging
import numpy as np
from typing import Dict, List, Optional
import cv2
from insightface.app import FaceAnalysis

from src.db.database import get_db_context
from src.db.repository import FaceRepository
from src.db.models import Person

logger = logging.getLogger(__name__)


class FaceRecognitionSystemDB:
    """Face recognition system with PostgreSQL backend."""
    
    def __init__(self, use_db: bool = True, class_name: Optional[str] = None, section_name: Optional[str] = None):
        """
        Initialize face recognition system.
        
        Args:
            use_db: Whether to use database (True) or file-based storage (False)
            class_name: Optional class filter for cache loading
            section_name: Optional section filter for cache loading
        """
        # Initialize InsightFace with high-quality settings
        self.app = FaceAnalysis(
            providers=['CPUExecutionProvider'],
            allowed_modules=['detection', 'recognition']
        )
        # Higher detection size for better accuracy
        self.app.prepare(ctx_id=0, det_size=(640, 640), det_thresh=0.6)
        
        # Database mode flag
        self.use_db = use_db
        
        # Class/Section filters
        self.current_class_filter = class_name
        self.current_section_filter = section_name
        
        # In-memory cache for embeddings (loaded from DB)
        self.embeddings_cache: Dict[str, List[Dict]] = {}
        
        # Enhanced matching parameters
        self.min_embedding_quality = 0.2
        self.max_embeddings_per_person = 20
        
        # Load embeddings from database into cache
        if self.use_db:
            self._load_embeddings_from_db(class_name, section_name)
        
        logger.info(f"FaceRecognitionSystemDB initialized (database_mode={use_db}, class={class_name}, section={section_name})")
    
    def _load_embeddings_from_db(self, class_name: Optional[str] = None, section_name: Optional[str] = None):
        """Load embeddings from database into memory cache with optional class/section filtering."""
        try:
            with get_db_context() as db:
                repo = FaceRepository(db)
                self.embeddings_cache = repo.get_all_embeddings(class_name, section_name)
            
            filter_desc = []
            if class_name:
                filter_desc.append(f"class={class_name}")
            if section_name:
                filter_desc.append(f"section={section_name}")
            filter_str = " " + ", ".join(filter_desc) if filter_desc else ""
            
            logger.info(f"Loaded {len(self.embeddings_cache)} persons from database{filter_str}")
        except Exception as e:
            logger.error(f"Failed to load embeddings from database: {e}")
            self.embeddings_cache = {}
    
    def set_class_section_filter(self, class_name: Optional[str] = None, section_name: Optional[str] = None):
        """Update class/section filter and reload cache accordingly."""
        self.current_class_filter = class_name
        self.current_section_filter = section_name
        
        if self.use_db:
            self._load_embeddings_from_db(class_name, section_name)
            logger.info(f"Cache reloaded with filter: class={class_name}, section={section_name}")
    
    def get_available_classes(self) -> List[str]:
        """Get list of available classes from database."""
        if self.use_db:
            try:
                with get_db_context() as db:
                    repo = FaceRepository(db)
                    return repo.get_available_classes()
            except Exception as e:
                logger.error(f"Failed to get available classes: {e}")
                return []
        return []
    
    def get_available_sections(self, class_name: Optional[str] = None) -> List[str]:
        """Get list of available sections, optionally filtered by class."""
        if self.use_db:
            try:
                with get_db_context() as db:
                    repo = FaceRepository(db)
                    return repo.get_available_sections(class_name)
            except Exception as e:
                logger.error(f"Failed to get available sections: {e}")
                return []
        return []
    
    def _refresh_person_cache(self, person_name: str):
        """Refresh cache for a specific person."""
        try:
            with get_db_context() as db:
                repo = FaceRepository(db)
                person = repo.get_person_by_name(person_name)
                if person:
                    embeddings = repo.get_embeddings_by_person(person.id)
                    self.embeddings_cache[person_name] = []
                    for emb in embeddings:
                        self.embeddings_cache[person_name].append({
                            'embedding': np.array(emb.embedding, dtype=np.float32),
                            'quality_score': emb.quality_score,
                            'det_score': emb.det_score
                        })
        except Exception as e:
            logger.error(f"Failed to refresh cache for {person_name}: {e}")
    
    def detect_and_extract(self, image: np.ndarray) -> List[Dict]:
        """
        Detect faces and extract embeddings with quality assessment.
        Returns list of face data with bbox, embedding, quality score, etc.
        """
        faces = self.app.get(image)
        results = []
        
        for face in faces:
            # Get bounding box
            bbox = face.bbox.astype(int)
            
            # Get normalized embedding (512-d vector)
            embedding = face.normed_embedding
            
            # Calculate face quality based on multiple factors
            quality_score = self._calculate_face_quality(face, image)
            
            # Get detection confidence
            det_score = face.det_score
            
            results.append({
                'bbox': bbox.tolist(),  # [x1, y1, x2, y2]
                'embedding': embedding,
                'det_score': float(det_score),
                'quality_score': quality_score,
                'landmarks': face.kps.tolist() if hasattr(face, 'kps') else None
            })
        
        return results
    
    def _calculate_face_quality(self, face, image: np.ndarray) -> float:
        """Calculate face quality score based on size, pose, and sharpness."""
        # Face size quality (larger faces are better)
        bbox = face.bbox
        face_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        image_area = image.shape[0] * image.shape[1]
        size_ratio = face_area / image_area
        size_score = min(size_ratio * 20, 1.0)
        
        # Detection confidence
        det_score = face.det_score
        
        # Pose quality (frontal faces are better)
        if hasattr(face, 'pose') and face.pose is not None:
            pose_score = 1.0 - (abs(face.pose[0]) + abs(face.pose[1]) + abs(face.pose[2])) / 180.0
        else:
            # Estimate pose from landmarks if available
            if hasattr(face, 'kps') and face.kps is not None and len(face.kps) >= 5:
                left_eye = face.kps[0]
                right_eye = face.kps[1]
                nose = face.kps[2]
                
                eye_diff = abs(left_eye[1] - right_eye[1])
                eye_distance = abs(left_eye[0] - right_eye[0])
                
                if eye_distance > 0:
                    symmetry = 1.0 - min(eye_diff / eye_distance, 1.0)
                    pose_score = symmetry * 0.9
                else:
                    pose_score = 0.7
            else:
                pose_score = 0.7
        
        # Face sharpness
        x1, y1, x2, y2 = bbox.astype(int)
        face_crop = image[y1:y2, x1:x2]
        if face_crop.size > 0:
            gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            sharpness_score = min(laplacian_var / 500.0, 1.0)
        else:
            sharpness_score = 0.0
        
        # Combined quality score
        quality = (size_score * 0.3 + det_score * 0.3 + pose_score * 0.2 + sharpness_score * 0.2)
        return float(quality)
    
    def enroll_person(self, name: str, image: np.ndarray, class_name: Optional[str] = None, section_name: Optional[str] = None) -> bool:
        """
        Enroll a person by extracting their face embedding with quality filtering.
        Stores in database if use_db=True.
        
        Args:
            name: Person's name
            image: Face image
            class_name: Optional class (e.g., "1st", "2nd", "12th")
            section_name: Optional section (e.g., "A", "B", "C")
        """
        faces = self.detect_and_extract(image)
        
        if not faces:
            return False
        
        # Filter faces by quality and use the best one
        quality_faces = [f for f in faces if f['quality_score'] >= self.min_embedding_quality]
        if not quality_faces:
            return False
        
        # Use the face with highest combined quality and detection score
        best_face = max(quality_faces, key=lambda x: x['quality_score'] * x['det_score'])
        
        if self.use_db:
            # Store in database
            try:
                with get_db_context() as db:
                    repo = FaceRepository(db)
                    
                    # Get or create person
                    person = repo.get_person_by_name(name)
                    if not person:
                        person = repo.create_person(name, class_name, section_name)
                    
                    # Add embedding
                    repo.add_embedding(
                        person_id=person.id,
                        embedding=best_face['embedding'],
                        quality_score=best_face['quality_score'],
                        det_score=best_face['det_score']
                    )
                    
                    # Clean up old embeddings
                    repo.delete_old_embeddings(person.id, self.max_embeddings_per_person)
                
                # Refresh cache for this person
                self._refresh_person_cache(name)
                logger.info(f"Enrolled {name} in database")
                return True
                
            except Exception as e:
                logger.error(f"Failed to enroll {name}: {e}")
                return False
        else:
            # Fallback to file-based storage (old behavior)
            embedding_data = {
                'embedding': best_face['embedding'],
                'quality_score': best_face['quality_score'],
                'det_score': best_face['det_score']
            }
            
            if name not in self.embeddings_cache:
                self.embeddings_cache[name] = []
            
            self.embeddings_cache[name].append(embedding_data)
            self.embeddings_cache[name].sort(key=lambda x: x['quality_score'] * x['det_score'], reverse=True)
            self.embeddings_cache[name] = self.embeddings_cache[name][:self.max_embeddings_per_person]
            return True
    
    def enroll_multiple_images(self, name: str, images: List[np.ndarray], class_name: Optional[str] = None, section_name: Optional[str] = None) -> Dict:
        """Enroll person from multiple images for better accuracy."""
        successful_enrollments = 0
        total_quality = 0.0
        
        for image in images:
            if self.enroll_person(name, image, class_name, section_name):
                successful_enrollments += 1
                # Get the quality of the last enrolled embedding
                if name in self.embeddings_cache and self.embeddings_cache[name]:
                    total_quality += self.embeddings_cache[name][-1]['quality_score']
        
        avg_quality = total_quality / successful_enrollments if successful_enrollments > 0 else 0.0
        
        return {
            'success': successful_enrollments > 0,
            'enrolled_count': successful_enrollments,
            'total_embeddings': len(self.embeddings_cache.get(name, [])),
            'avg_quality': avg_quality
        }
    
    def recognize_face(self, image: np.ndarray, threshold: float = 0.4) -> List[Dict]:
        """
        Enhanced face recognition with multiple embedding matching.
        Returns list with recognition results.
        """
        faces = self.detect_and_extract(image)
        results = []
        
        for face_data in faces:
            query_embedding = face_data['embedding']
            
            # Find best match using multiple embeddings per person
            best_match = None
            best_similarity = 0.0
            match_scores = []
            
            for name, stored_embeddings in self.embeddings_cache.items():
                # Calculate similarities with all stored embeddings for this person
                similarities = []
                for emb_data in stored_embeddings:
                    stored_emb = emb_data['embedding']
                    # Cosine similarity (both embeddings are normalized)
                    similarity = float(np.dot(query_embedding, stored_emb))
                    # Weight by embedding quality
                    weighted_similarity = similarity * (0.7 + 0.3 * emb_data['quality_score'])
                    similarities.append(weighted_similarity)
                
                if similarities:
                    # Use average of top 3 similarities for more robust matching
                    top_similarities = sorted(similarities, reverse=True)[:3]
                    avg_similarity = np.mean(top_similarities)
                    
                    if avg_similarity > best_similarity:
                        best_similarity = avg_similarity
                        best_match = name
                        match_scores = similarities
            
            # Enhanced threshold with quality consideration
            quality_adjusted_threshold = threshold * (0.8 + 0.2 * face_data['quality_score'])
            is_match = best_similarity >= quality_adjusted_threshold
            
            results.append({
                'bbox': face_data['bbox'],
                'matched': is_match,
                'name': best_match if is_match else None,
                'confidence': best_similarity,
                'det_score': face_data['det_score'],
                'quality_score': face_data['quality_score']
            })
        
        return results
    
    def log_attendance(self, name: str, confidence: float) -> bool:
        """Log attendance if person hasn't been recorded today."""
        if self.use_db:
            try:
                with get_db_context() as db:
                    repo = FaceRepository(db)
                    person = repo.get_person_by_name(name)
                    
                    if not person:
                        logger.warning(f"Person {name} not found in database")
                        return False
                    
                    attendance = repo.log_attendance(person.id, confidence)
                    if attendance:
                        logger.info(f"Logged attendance for {name}")
                        return True
                    else:
                        logger.debug(f"{name} already has attendance for today")
                        return False
            except Exception as e:
                logger.error(f"Failed to log attendance for {name}: {e}")
                return False
        else:
            # Fallback to file-based (not implemented here)
            return False
    
    def get_enrolled_count(self) -> int:
        """Get total number of enrolled embeddings."""
        if self.use_db:
            try:
                with get_db_context() as db:
                    repo = FaceRepository(db)
                    return repo.get_embedding_count()
            except Exception as e:
                logger.error(f"Failed to get enrollment count: {e}")
                return 0
        else:
            return sum(len(embeddings) for embeddings in self.embeddings_cache.values())
    
    def get_enrolled_names(self) -> List[str]:
        """Get list of enrolled person names."""
        if self.use_db:
            try:
                with get_db_context() as db:
                    repo = FaceRepository(db)
                    persons = repo.get_all_persons()
                    return [p.name for p in persons]
            except Exception as e:
                logger.error(f"Failed to get enrolled names: {e}")
                return []
        else:
            return list(self.embeddings_cache.keys())
    
    def get_person_stats(self, name: str) -> Dict:
        """Get statistics for a specific person."""
        if self.use_db:
            try:
                with get_db_context() as db:
                    repo = FaceRepository(db)
                    person = repo.get_person_by_name(name)
                    if person:
                        return repo.get_person_stats(person.id)
                    return {}
            except Exception as e:
                logger.error(f"Failed to get person stats for {name}: {e}")
                return {}
        else:
            if name not in self.embeddings_cache:
                return {}
            
            embeddings = self.embeddings_cache[name]
            qualities = [emb['quality_score'] for emb in embeddings]
            det_scores = [emb['det_score'] for emb in embeddings]
            
            return {
                'embedding_count': len(embeddings),
                'avg_quality': np.mean(qualities),
                'max_quality': np.max(qualities),
                'avg_det_score': np.mean(det_scores)
            }
    
    def delete_person(self, name: str) -> bool:
        """Delete all embeddings for a specific person."""
        if self.use_db:
            try:
                with get_db_context() as db:
                    repo = FaceRepository(db)
                    success = repo.delete_person(name)
                    if success and name in self.embeddings_cache:
                        del self.embeddings_cache[name]
                    return success
            except Exception as e:
                logger.error(f"Failed to delete person {name}: {e}")
                return False
        else:
            if name in self.embeddings_cache:
                del self.embeddings_cache[name]
                return True
            return False
    
    def clear_all_data(self) -> bool:
        """Clear all enrolled data."""
        if self.use_db:
            try:
                with get_db_context() as db:
                    persons = db.query(Person).all()
                    for person in persons:
                        db.delete(person)
                    db.commit()
                self.embeddings_cache.clear()
                logger.info("Cleared all enrollment data from database")
                return True
            except Exception as e:
                logger.error(f"Failed to clear all data: {e}")
                return False
        else:
            self.embeddings_cache.clear()
            return True
    
    def get_today_attendance(self) -> List[str]:
        """Get list of people who attended today."""
        if self.use_db:
            try:
                with get_db_context() as db:
                    repo = FaceRepository(db)
                    return repo.get_today_attendance_names()
            except Exception as e:
                logger.error(f"Failed to get today's attendance: {e}")
                return []
        else:
            return []
    
    def get_attendance_stats(self) -> Dict:
        """Get attendance statistics."""
        if self.use_db:
            try:
                with get_db_context() as db:
                    repo = FaceRepository(db)
                    return repo.get_attendance_stats()
            except Exception as e:
                logger.error(f"Failed to get attendance stats: {e}")
                return {}
        else:
            return {}
