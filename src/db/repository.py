"""Database repository for face recognition operations."""
import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Tuple

import numpy as np
from sqlalchemy import func, and_, cast, Date
from sqlalchemy.orm import Session

from src.db.models import Person, FaceEmbedding, AttendanceLog

logger = logging.getLogger(__name__)


class FaceRepository:
    """Repository for face recognition database operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==================== Person Operations ====================
    
    def get_person_by_name(self, name: str) -> Optional[Person]:
        """Get person by name."""
        return self.db.query(Person).filter(Person.name == name).first()
    
    def get_person_by_id(self, person_id: int) -> Optional[Person]:
        """Get person by ID."""
        return self.db.query(Person).filter(Person.id == person_id).first()
    
    def get_all_persons(self) -> List[Person]:
        """Get all persons."""
        return self.db.query(Person).all()
    
    def create_person(self, name: str, class_name: Optional[str] = None, section_name: Optional[str] = None) -> Person:
        """Create a new person with optional class and section."""
        person = Person(name=name, class_name=class_name, section_name=section_name)
        self.db.add(person)
        self.db.commit()
        self.db.refresh(person)
        logger.info(f"Created person: {name} (ID: {person.id}, Class: {class_name}, Section: {section_name})")
        return person
    
    def delete_person(self, name: str) -> bool:
        """Delete person and all associated data."""
        person = self.get_person_by_name(name)
        if person:
            self.db.delete(person)
            self.db.commit()
            logger.info(f"Deleted person: {name}")
            return True
        return False
    
    def get_person_count(self) -> int:
        """Get total number of persons."""
        return self.db.query(Person).count()
    
    def get_persons_by_class_section(self, class_name: Optional[str] = None, section_name: Optional[str] = None) -> List[Person]:
        """Get persons filtered by class and/or section."""
        query = self.db.query(Person)
        
        if class_name:
            query = query.filter(Person.class_name == class_name)
        if section_name:
            query = query.filter(Person.section_name == section_name)
        
        return query.all()
    
    def get_available_classes(self) -> List[str]:
        """Get list of unique classes."""
        results = self.db.query(Person.class_name).filter(Person.class_name.isnot(None)).distinct().all()
        return sorted([cls for (cls,) in results if cls])
    
    def get_available_sections(self, class_name: Optional[str] = None) -> List[str]:
        """Get list of unique sections, optionally filtered by class."""
        query = self.db.query(Person.section_name).filter(Person.section_name.isnot(None))
        
        if class_name:
            query = query.filter(Person.class_name == class_name)
        
        results = query.distinct().all()
        return sorted([sec for (sec,) in results if sec])
    
    # ==================== Embedding Operations ====================
    
    def add_embedding(
        self,
        person_id: int,
        embedding: np.ndarray,
        quality_score: float,
        det_score: float
    ) -> FaceEmbedding:
        """Add a face embedding for a person."""
        # Convert numpy array to list for PostgreSQL ARRAY type
        embedding_list = embedding.tolist() if isinstance(embedding, np.ndarray) else embedding
        
        face_embedding = FaceEmbedding(
            person_id=person_id,
            embedding=embedding_list,
            quality_score=quality_score,
            det_score=det_score
        )
        self.db.add(face_embedding)
        self.db.commit()
        self.db.refresh(face_embedding)
        logger.debug(f"Added embedding for person_id={person_id}, quality={quality_score:.3f}")
        return face_embedding
    
    def get_embeddings_by_person(self, person_id: int, limit: int = 20) -> List[FaceEmbedding]:
        """Get embeddings for a person, sorted by quality."""
        return (
            self.db.query(FaceEmbedding)
            .filter(FaceEmbedding.person_id == person_id)
            .order_by(FaceEmbedding.quality_score.desc(), FaceEmbedding.det_score.desc())
            .limit(limit)
            .all()
        )
    
    def get_all_embeddings(self, class_name: Optional[str] = None, section_name: Optional[str] = None) -> Dict[str, List[Dict]]:
        """
        Get all embeddings organized by person name, optionally filtered by class/section.
        Returns dict: {person_name: [embedding_data, ...]}
        """
        if class_name or section_name:
            persons = self.get_persons_by_class_section(class_name, section_name)
        else:
            persons = self.get_all_persons()
        
        embeddings_db = {}
        
        for person in persons:
            embeddings = self.get_embeddings_by_person(person.id)
            embeddings_db[person.name] = []
            
            for emb in embeddings:
                embeddings_db[person.name].append({
                    'embedding': np.array(emb.embedding, dtype=np.float32),
                    'quality_score': emb.quality_score,
                    'det_score': emb.det_score
                })
        
        return embeddings_db
    
    def delete_old_embeddings(self, person_id: int, keep_count: int = 20) -> int:
        """Delete old embeddings, keeping only the top N by quality."""
        # Get embeddings sorted by quality
        all_embeddings = (
            self.db.query(FaceEmbedding)
            .filter(FaceEmbedding.person_id == person_id)
            .order_by(FaceEmbedding.quality_score.desc(), FaceEmbedding.det_score.desc())
            .all()
        )
        
        if len(all_embeddings) <= keep_count:
            return 0
        
        # Delete embeddings beyond the keep_count
        to_delete = all_embeddings[keep_count:]
        delete_count = 0
        for emb in to_delete:
            self.db.delete(emb)
            delete_count += 1
        
        self.db.commit()
        logger.debug(f"Deleted {delete_count} old embeddings for person_id={person_id}")
        return delete_count
    
    def get_embedding_count(self) -> int:
        """Get total number of embeddings."""
        return self.db.query(FaceEmbedding).count()
    
    # ==================== Attendance Operations ====================
    
    def log_attendance(
        self,
        person_id: int,
        confidence: float,
        status: str = "Present"
    ) -> Optional[AttendanceLog]:
        """
        Log attendance for a person.
        Returns None if person already has attendance today.
        """
        today = date.today()
        
        # Check if already logged today
        existing = (
            self.db.query(AttendanceLog)
            .filter(
                and_(
                    AttendanceLog.person_id == person_id,
                    cast(AttendanceLog.recognized_at, Date) == today
                )
            )
            .first()
        )
        
        if existing:
            logger.debug(f"Person {person_id} already has attendance for today")
            return None
        
        # Create new attendance log
        attendance = AttendanceLog(
            person_id=person_id,
            confidence=confidence,
            status=status
        )
        self.db.add(attendance)
        self.db.commit()
        self.db.refresh(attendance)
        logger.info(f"Logged attendance for person_id={person_id}, confidence={confidence:.3f}")
        return attendance
    
    def get_today_attendance(self) -> List[AttendanceLog]:
        """Get all attendance records for today."""
        today = date.today()
        return (
            self.db.query(AttendanceLog)
            .filter(cast(AttendanceLog.recognized_at, Date) == today)
            .all()
        )
    
    def get_today_attendance_names(self) -> List[str]:
        """Get names of people who attended today."""
        today = date.today()
        results = (
            self.db.query(Person.name)
            .join(AttendanceLog)
            .filter(cast(AttendanceLog.recognized_at, Date) == today)
            .all()
        )
        return [name for (name,) in results]
    
    def get_attendance_stats(self) -> Dict:
        """Get attendance statistics."""
        today = date.today()
        
        # Today's count
        today_count = (
            self.db.query(AttendanceLog)
            .filter(cast(AttendanceLog.recognized_at, Date) == today)
            .count()
        )
        
        # Total unique days
        total_days = (
            self.db.query(func.count(func.distinct(cast(AttendanceLog.recognized_at, Date))))
            .scalar()
        ) or 0
        
        # Total records
        total_records = self.db.query(AttendanceLog).count()
        
        return {
            'today_attendance': today_count,
            'today_names': self.get_today_attendance_names(),
            'total_days_recorded': total_days,
            'total_attendance_records': total_records
        }
    
    def get_person_attendance_history(self, person_id: int) -> List[AttendanceLog]:
        """Get attendance history for a person."""
        return (
            self.db.query(AttendanceLog)
            .filter(AttendanceLog.person_id == person_id)
            .order_by(AttendanceLog.recognized_at.desc())
            .all()
        )
    
    # ==================== Analytics Operations ====================
    
    def get_attendance_by_date_range(
        self,
        start_date: date,
        end_date: date
    ) -> List[AttendanceLog]:
        """Get attendance records within date range."""
        return (
            self.db.query(AttendanceLog)
            .filter(
                and_(
                    cast(AttendanceLog.recognized_at, Date) >= start_date,
                    cast(AttendanceLog.recognized_at, Date) <= end_date
                )
            )
            .order_by(AttendanceLog.recognized_at.desc())
            .all()
        )
    
    def get_person_stats(self, person_id: int) -> Dict:
        """Get statistics for a specific person."""
        embeddings = self.get_embeddings_by_person(person_id)
        
        if not embeddings:
            return {}
        
        qualities = [emb.quality_score for emb in embeddings]
        det_scores = [emb.det_score for emb in embeddings]
        
        return {
            'embedding_count': len(embeddings),
            'avg_quality': np.mean(qualities),
            'max_quality': np.max(qualities),
            'avg_det_score': np.mean(det_scores)
        }
