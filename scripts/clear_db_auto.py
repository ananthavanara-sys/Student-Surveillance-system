"""
Automatically clear PostgreSQL database tables without confirmation.
"""
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def clear_database():
    """Clear PostgreSQL database tables."""
    try:
        from src.db.database import test_connection, get_db
        from src.db.models import Student, Attendance, FaceEmbedding, ClassSection
        
        # Test connection
        logger.info("Testing database connection...")
        if not test_connection():
            logger.warning("Cannot connect to database.")
            logger.warning("Database may not be configured or PostgreSQL is not running.")
            logger.info("File-based data has already been cleared.")
            return False
        
        logger.info("Connected to database. Clearing tables...")
        
        # Get database session
        db = next(get_db())
        
        try:
            # Delete all records from tables
            attendance_count = db.query(Attendance).count()
            embedding_count = db.query(FaceEmbedding).count()
            student_count = db.query(Student).count()
            section_count = db.query(ClassSection).count()
            
            db.query(Attendance).delete()
            db.query(FaceEmbedding).delete()
            db.query(Student).delete()
            db.query(ClassSection).delete()
            
            db.commit()
            
            logger.info("✓ Database cleared successfully!")
            logger.info(f"  - Deleted {student_count} students")
            logger.info(f"  - Deleted {attendance_count} attendance records")
            logger.info(f"  - Deleted {embedding_count} face embeddings")
            logger.info(f"  - Deleted {section_count} class sections")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to clear database: {e}")
            return False
        finally:
            db.close()
            
    except ImportError as e:
        logger.warning(f"Database modules not available: {e}")
        logger.info("Skipping database cleanup.")
        return False
    except Exception as e:
        logger.error(f"Error during database cleanup: {e}")
        return False


def main():
    """Main function."""
    logger.info("=" * 60)
    logger.info("CLEARING DATABASE")
    logger.info("=" * 60)
    
    success = clear_database()
    
    logger.info("=" * 60)
    if success:
        logger.info("✓ DATABASE CLEARED SUCCESSFULLY")
    else:
        logger.info("Database clearing skipped or failed")
        logger.info("File-based data (CSV/JSON) has been cleared")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
