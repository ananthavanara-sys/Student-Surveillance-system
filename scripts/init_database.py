"""
Initialize PostgreSQL database and run migrations.
Run this script after setting up PostgreSQL to create tables and schema.
"""
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.database import test_connection, init_db
from src.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Initialize database."""
    logger.info("Starting database initialization...")
    logger.info(f"Database URL: {settings.database_url.split('@')[1]}")  # Hide password
    
    # Test connection
    logger.info("Testing database connection...")
    if not test_connection():
        logger.error("Failed to connect to database. Please check:")
        logger.error("1. PostgreSQL is running")
        logger.error("2. Database credentials are correct in .env file")
        logger.error("3. Database 'surveillance_db' exists")
        sys.exit(1)
    
    logger.info("Database connection successful!")
    
    # Create tables
    logger.info("Creating database tables...")
    try:
        init_db()
        logger.info("✓ Database tables created successfully!")
        logger.info("")
        logger.info("Database initialization complete!")
        logger.info("You can now start the application with: poetry run python scripts/run_system.py")
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
