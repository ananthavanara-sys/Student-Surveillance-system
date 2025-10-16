"""
Migrate data from file-based storage (JSON/CSV) to PostgreSQL database.
Run this after database initialization if you have existing data.
"""
import sys
import json
import csv
import logging
from pathlib import Path
from datetime import datetime

import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.database import get_db_context
from src.db.repository import FaceRepository
from src.db.models import Person, FaceEmbedding, AttendanceLog

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def migrate_embeddings(embeddings_file: Path):
    """Migrate face embeddings from JSON to database."""
    if not embeddings_file.exists():
        logger.warning(f"Embeddings file not found: {embeddings_file}")
        return 0
    
    logger.info(f"Loading embeddings from {embeddings_file}...")
    with open(embeddings_file, 'r') as f:
        data = json.load(f)
    
    total_persons = 0
    total_embeddings = 0
    
    with get_db_context() as db:
        repo = FaceRepository(db)
        
        for name, embeddings in data.items():
            # Create person
            person = repo.get_person_by_name(name)
            if not person:
                person = repo.create_person(name)
                total_persons += 1
            
            # Add embeddings
            for emb_data in embeddings:
                if isinstance(emb_data, dict):
                    # New format with metadata
                    embedding = np.array(emb_data['embedding'], dtype=np.float32)
                    quality_score = emb_data.get('quality_score', 0.5)
                    det_score = emb_data.get('det_score', 0.5)
                else:
                    # Old format - just embedding array
                    embedding = np.array(emb_data, dtype=np.float32)
                    quality_score = 0.5
                    det_score = 0.5
                
                repo.add_embedding(
                    person_id=person.id,
                    embedding=embedding,
                    quality_score=quality_score,
                    det_score=det_score
                )
                total_embeddings += 1
            
            logger.info(f"  Migrated {name}: {len(embeddings)} embeddings")
    
    logger.info(f"✓ Migrated {total_persons} persons with {total_embeddings} embeddings")
    return total_persons


def migrate_attendance(attendance_file: Path):
    """Migrate attendance records from CSV to database."""
    if not attendance_file.exists():
        logger.warning(f"Attendance file not found: {attendance_file}")
        return 0
    
    logger.info(f"Loading attendance from {attendance_file}...")
    
    total_records = 0
    skipped_records = 0
    
    with get_db_context() as db:
        repo = FaceRepository(db)
        
        with open(attendance_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    # Get person
                    person = repo.get_person_by_name(row['Name'])
                    if not person:
                        logger.warning(f"  Person not found: {row['Name']} - skipping attendance record")
                        skipped_records += 1
                        continue
                    
                    # Parse datetime
                    recognized_at = datetime.strptime(
                        f"{row['Date']} {row['Time']}",
                        "%Y-%m-%d %H:%M:%S"
                    )
                    
                    # Create attendance log (might fail if duplicate)
                    try:
                        attendance = AttendanceLog(
                            person_id=person.id,
                            recognized_at=recognized_at,
                            confidence=float(row['Confidence']),
                            status=row.get('Status', 'Present')
                        )
                        db.add(attendance)
                        db.flush()  # Try to insert
                        total_records += 1
                    except Exception as e:
                        # Likely duplicate - skip
                        skipped_records += 1
                        continue
                        
                except Exception as e:
                    logger.warning(f"  Error processing row: {e}")
                    skipped_records += 1
                    continue
        
        db.commit()
    
    logger.info(f"✓ Migrated {total_records} attendance records (skipped {skipped_records} duplicates/errors)")
    return total_records


def main():
    """Run migration from files to database."""
    logger.info("=" * 60)
    logger.info("MIGRATING FILE-BASED DATA TO POSTGRESQL")
    logger.info("=" * 60)
    
    # Define file paths
    embeddings_file = Path("data/processed/face_embeddings.json")
    attendance_file = Path("data/processed/attendance.csv")
    
    # Migrate embeddings
    logger.info("\n[1/2] Migrating Face Embeddings...")
    persons_count = migrate_embeddings(embeddings_file)
    
    # Migrate attendance
    logger.info("\n[2/2] Migrating Attendance Records...")
    attendance_count = migrate_attendance(attendance_file)
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("MIGRATION COMPLETE!")
    logger.info("=" * 60)
    logger.info(f"Persons migrated: {persons_count}")
    logger.info(f"Attendance records migrated: {attendance_count}")
    logger.info("\nYour data is now in PostgreSQL!")
    logger.info("The original files are preserved as backup.")


if __name__ == "__main__":
    main()
