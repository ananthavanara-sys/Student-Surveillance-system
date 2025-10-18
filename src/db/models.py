"""SQLAlchemy database models for face recognition system."""
from datetime import datetime
from typing import List

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Person(Base):
    """Person/Student model."""
    __tablename__ = 'persons'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    embeddings = relationship(
        "FaceEmbedding",
        back_populates="person",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    attendance = relationship(
        "AttendanceLog",
        back_populates="person",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<Person(id={self.id}, name='{self.name}')>"


class FaceEmbedding(Base):
    """Face embedding storage model."""
    __tablename__ = 'face_embeddings'
    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey('persons.id', ondelete='CASCADE'), nullable=False, index=True)
    # Store 512-dimensional embedding as PostgreSQL array
    embedding = Column(ARRAY(Float), nullable=False)
    quality_score = Column(Float, nullable=False)
    det_score = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    person = relationship("Person", back_populates="embeddings")
    
    # Index for person lookups
    __table_args__ = (
        Index('idx_person_embeddings', 'person_id', 'quality_score'),
    )
    
    def __repr__(self) -> str:
        return f"<FaceEmbedding(id={self.id}, person_id={self.person_id}, quality={self.quality_score:.3f})>"


class AttendanceLog(Base):
    """Attendance log model."""
    __tablename__ = 'attendance_log'
    
    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey('persons.id', ondelete='CASCADE'), nullable=False, index=True)
    recognized_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    status = Column(String(50), default='Present', nullable=False)
    
    # Relationship
    person = relationship("Person", back_populates="attendance")
    
    # Ensure one entry per person per day
    __table_args__ = (
        Index('idx_person_date', 'person_id', 'recognized_at'),
        UniqueConstraint('person_id', 'recognized_at', name='uq_person_date'),
    )
    
    def __repr__(self) -> str:
        return f"<AttendanceLog(id={self.id}, person_id={self.person_id}, time={self.recognized_at})>"
