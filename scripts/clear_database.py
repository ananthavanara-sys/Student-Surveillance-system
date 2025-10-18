"""
Clear all database information including CSV files, JSON embeddings, and PostgreSQL data.
This script will:
1. Clear attendance.csv
2. Clear face_embeddings.json
3. Clear analytics reports
4. Clear PostgreSQL database tables (if connected)
"""
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def clear_csv_files():
    """Clear attendance CSV file."""
    try:
        attendance_file = Path("data/processed/attendance.csv")
        if attendance_file.exists():
            # Keep header, clear data
            with open(attendance_file, 'w') as f:
                f.write("Date,Time,Name,Confidence,Status\n")
            logger.info("✓ Cleared attendance.csv")
        else:
            logger.info("attendance.csv not found, skipping")
    except Exception as e:
        logger.error(f"Failed to clear attendance.csv: {e}")


def clear_json_files():
    """Clear JSON files (embeddings and reports)."""
    try:
        # Clear face embeddings
        embeddings_file = Path("data/processed/face_embeddings.json")
        if embeddings_file.exists():
            with open(embeddings_file, 'w') as f:
                f.write("{}")
            logger.info("✓ Cleared face_embeddings.json")
        
        # Clear analytics reports
        processed_dir = Path("data/processed")
        report_files = list(processed_dir.glob("analytics_report_*.json"))
        for report_file in report_files:
            report_file.unlink()
            logger.info(f"✓ Deleted {report_file.name}")
        
        if not report_files:
            logger.info("No analytics reports found, skipping")
            
    except Exception as e:
        logger.error(f"Failed to clear JSON files: {e}")


def clear_database():
    """Clear PostgreSQL database tables."""
    try:
        from src.db.database import test_connection, get_db
        from src.db.models import Student, Attendance, FaceEmbedding, ClassSection
        
        # Test connection
        if not test_connection():
            logger.warning("Cannot connect to database. Skipping database cleanup.")
            logger.warning("If you want to clear the database, ensure PostgreSQL is running and configured.")
            return
        
        logger.info("Connected to database. Clearing tables...")
        
        # Get database session
        db = next(get_db())
        
        try:
            # Delete all records from tables
            db.query(Attendance).delete()
            db.query(FaceEmbedding).delete()
            db.query(Student).delete()
            db.query(ClassSection).delete()
            
            db.commit()
            logger.info("✓ Cleared all database tables")
            logger.info("  - Students")
            logger.info("  - Attendance records")
            logger.info("  - Face embeddings")
            logger.info("  - Class sections")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to clear database: {e}")
        finally:
            db.close()
            
    except ImportError:
        logger.warning("Database modules not available. Skipping database cleanup.")
    except Exception as e:
        logger.error(f"Error during database cleanup: {e}")


def main():
    """Main function to clear all database information."""
    logger.info("=" * 60)
    logger.info("CLEARING ALL DATABASE INFORMATION")
    logger.info("=" * 60)
    logger.info("")
    
    # Confirm action
    print("⚠️  WARNING: This will delete ALL data including:")
    print("   - Attendance records (CSV)")
    print("   - Face embeddings (JSON)")
    print("   - Analytics reports (JSON)")
    print("   - Database records (PostgreSQL)")
    print("")
    response = input("Are you sure you want to continue? (yes/no): ")
    
    if response.lower() != 'yes':
        logger.info("Operation cancelled by user.")
        return
    
    logger.info("")
    logger.info("Starting cleanup...")
    logger.info("")
    
    # Clear CSV files
    logger.info("1. Clearing CSV files...")
    clear_csv_files()
    logger.info("")
    
    # Clear JSON files
    logger.info("2. Clearing JSON files...")
    clear_json_files()
    logger.info("")
    
    # Clear database
    logger.info("3. Clearing database...")
    clear_database()
    logger.info("")
    
    logger.info("=" * 60)
    logger.info("✓ DATABASE CLEANUP COMPLETE")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
