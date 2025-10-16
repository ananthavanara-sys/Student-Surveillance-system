# Face Recognition System - PostgreSQL Integration

## What's New

The face recognition system now supports **PostgreSQL database** as the primary storage backend, replacing the file-based JSON/CSV approach.

### Key Changes

✅ **Database Models** - SQLAlchemy ORM models for persons, embeddings, and attendance  
✅ **Migration Support** - Alembic for schema versioning  
✅ **Backward Compatible** - Still works with file-based storage if needed  
✅ **Docker Integration** - PostgreSQL container included in docker-compose  
✅ **Data Migration Tools** - Scripts to migrate existing data from files to database

---

## Quick Start

### 1. Start with Docker (Easiest)

```bash
# Start everything (PostgreSQL + API)
docker-compose up --build

# Access API at http://localhost:8000
# Database at postgresql://surveillance:changeme_secure_password@localhost:5432/surveillance_db
```

### 2. Local Development Setup

**Step 1: Install PostgreSQL**
```bash
# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib

# macOS
brew install postgresql@15

# Windows - Download from https://www.postgresql.org/download/
```

**Step 2: Create Database**
```bash
psql -U postgres
CREATE DATABASE surveillance_db;
CREATE USER surveillance WITH PASSWORD 'changeme_secure_password';
GRANT ALL PRIVILEGES ON DATABASE surveillance_db TO surveillance;
\q
```

**Step 3: Configure Environment**
```bash
# Copy example env file
cp .env.example .env

# Edit .env and set
DATABASE_URL=postgresql://surveillance:changeme_secure_password@localhost:5432/surveillance_db
```

**Step 4: Initialize Database**
```bash
poetry install
poetry run python scripts/init_database.py
```

**Step 5: Migrate Existing Data (Optional)**
```bash
# If you have existing face_embeddings.json or attendance.csv
poetry run python scripts/migrate_file_to_db.py
```

**Step 6: Run Application**
```bash
poetry run python scripts/run_system.py
# or
poetry run uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Architecture Changes

### Old Architecture (File-Based)
```
Face System → JSON Files (embeddings) + CSV (attendance)
```

### New Architecture (Database)
```
Face System → PostgreSQL Database
├── persons table (names, metadata)
├── face_embeddings table (512-dim vectors)
└── attendance_log table (timestamped records)
```

### Database Schema

**persons**
- Stores person/student information
- Unique constraint on name

**face_embeddings**
- Stores 512-dimensional ArcFace embeddings
- Links to persons via foreign key
- Up to 20 embeddings per person for accuracy

**attendance_log**
- Timestamped attendance records
- Automatic deduplication (one entry per person per day)
- Links to persons via foreign key

---

## New Files Added

```
src/db/
├── __init__.py           # Database package
├── models.py             # SQLAlchemy ORM models
├── database.py           # Database connection and session management
└── repository.py         # Data access layer (CRUD operations)

src/face_system_db.py     # Database-powered face recognition system

alembic/                  # Database migrations
├── env.py                # Alembic environment
├── versions/             # Migration scripts
│   └── 001_initial_schema.py
└── README                # Migration usage guide

scripts/
├── init_database.py      # Database initialization script
└── migrate_file_to_db.py # Data migration from files to DB

alembic.ini               # Alembic configuration
DATABASE_SETUP.md         # Comprehensive database guide
```

---

## Modified Files

**Updated to use database:**
- `src/app/main.py` - Added database initialization on startup
- `src/app/dependencies.py` - Uses `FaceRecognitionSystemDB` instead of `FaceRecognitionSystem`
- `src/app/routes/enrollment.py` - Updated type hints
- `src/app/routes/recognition.py` - Updated type hints
- `docker-compose.yml` - Enabled PostgreSQL service

**Configuration:**
- `.env.example` - Added database configuration examples

---

## Usage Examples

### Python API

```python
from src.db.database import get_db_context
from src.db.repository import FaceRepository
from src.db.models import Person

# Get all persons
with get_db_context() as db:
    repo = FaceRepository(db)
    persons = repo.get_all_persons()
    for person in persons:
        print(f"{person.name}: {person.id}")

# Add embedding
with get_db_context() as db:
    repo = FaceRepository(db)
    person = repo.get_person_by_name("John Doe")
    repo.add_embedding(
        person_id=person.id,
        embedding=embedding_vector,  # 512-dim numpy array
        quality_score=0.85,
        det_score=0.92
    )

# Log attendance
with get_db_context() as db:
    repo = FaceRepository(db)
    person = repo.get_person_by_name("Jane Smith")
    repo.log_attendance(person.id, confidence=0.87)
```

### REST API (Same as before)

```bash
# Enroll person
curl -X POST http://localhost:8000/api/enroll \
  -F "name=John Doe" \
  -F "files=@photo1.jpg" \
  -F "files=@photo2.jpg"

# Recognize face
curl -X POST http://localhost:8000/api/recognize \
  -F "file=@test.jpg"

# Get attendance stats
curl http://localhost:8000/api/attendance
```

---

## Database Operations

### Manual Queries

```sql
-- Connect to database
psql -U surveillance -d surveillance_db

-- View all persons
SELECT * FROM persons;

-- Count embeddings per person
SELECT p.name, COUNT(e.id) as embedding_count
FROM persons p
LEFT JOIN face_embeddings e ON p.id = e.person_id
GROUP BY p.name;

-- Today's attendance
SELECT p.name, a.confidence, a.recognized_at
FROM attendance_log a
JOIN persons p ON a.person_id = p.id
WHERE DATE(a.recognized_at) = CURRENT_DATE;
```

### Backup and Restore

```bash
# Backup
pg_dump -U surveillance surveillance_db > backup.sql

# Restore
psql -U surveillance surveillance_db < backup.sql
```

---

## Migration from File-Based Storage

If you're upgrading from the old file-based system:

1. **Keep old files as backup** - Don't delete `face_embeddings.json` or `attendance.csv`

2. **Initialize database:**
   ```bash
   poetry run python scripts/init_database.py
   ```

3. **Migrate data:**
   ```bash
   poetry run python scripts/migrate_file_to_db.py
   ```

4. **Verify migration:**
   ```bash
   psql -U surveillance -d surveillance_db
   SELECT COUNT(*) FROM persons;
   SELECT COUNT(*) FROM face_embeddings;
   SELECT COUNT(*) FROM attendance_log;
   ```

5. **Start using the database version** - The system automatically uses database if configured

---

## Configuration

### Environment Variables

```env
# Database (Required)
DATABASE_URL=postgresql://user:password@host:port/database

# Redis (Optional - not yet implemented)
REDIS_URL=redis://localhost:6379/0

# RabbitMQ (Optional - not yet implemented)
RABBITMQ_URL=amqp://user:password@localhost:5672/
```

### Connection Pool Settings

Default settings in `src/db/database.py`:
```python
pool_size=20          # Number of persistent connections
max_overflow=10       # Additional connections when pool exhausted
pool_recycle=3600     # Recycle connections after 1 hour
pool_pre_ping=True    # Verify connection before use
```

---

## Performance Considerations

### Scalability
- **File-based:** Good for 10-100 faces
- **PostgreSQL:** Good for 1,000-10,000 faces
- **PostgreSQL + pgvector:** Good for 100,000+ faces

### Query Optimization
- Indexed on person lookups
- Composite index on (person_id, quality_score) for fast embedding retrieval
- Unique constraint on attendance for automatic deduplication

### Caching
- Embeddings loaded into memory on startup
- Cache refreshed after enrollment operations
- Future: Redis caching for frequently accessed data

---

## Troubleshooting

### "Could not connect to database"
**Solution:**
1. Check PostgreSQL is running: `sudo systemctl status postgresql`
2. Verify credentials in `.env`
3. Test connection: `psql -U surveillance -d surveillance_db`

### "relation does not exist"
**Solution:**
```bash
# Tables not created - run initialization
poetry run python scripts/init_database.py
```

### "duplicate key value violates unique constraint"
**Solution:**
- This is expected for attendance (one entry per person per day)
- For persons: person name already exists

### Database is slow
**Solution:**
1. Run vacuum: `VACUUM ANALYZE;`
2. Rebuild indexes: `REINDEX DATABASE surveillance_db;`
3. Check query performance: `EXPLAIN ANALYZE <query>;`

---

## Future Enhancements

### Planned Features
- [ ] Redis caching layer for embeddings
- [ ] RabbitMQ for async face processing
- [ ] pgvector extension for ultra-fast similarity search
- [ ] Multi-tenancy support
- [ ] Advanced analytics dashboards
- [ ] Real-time notifications via WebSocket

### Database Extensions
- **pgvector** - Vector similarity search
- **TimescaleDB** - Time-series optimization for attendance data
- **PostGIS** - Geographic data (for multi-location deployments)

---

## Development

### Running Tests
```bash
# Run all tests
poetry run pytest

# Run with database
DATABASE_URL=postgresql://test:test@localhost:5432/test_db poetry run pytest
```

### Creating Migrations
```bash
# Auto-generate migration
poetry run alembic revision --autogenerate -m "add new column"

# Apply migration
poetry run alembic upgrade head
```

### Rollback Migration
```bash
poetry run alembic downgrade -1
```

---

## Contributing

When adding database features:
1. Update models in `src/db/models.py`
2. Create migration: `alembic revision --autogenerate -m "description"`
3. Update repository methods in `src/db/repository.py`
4. Add tests
5. Update documentation

---

## Support

For detailed documentation, see:
- **DATABASE_SETUP.md** - Complete setup and configuration guide
- **alembic/README** - Migration usage guide
- **API Documentation** - http://localhost:8000/docs (when running)

---

**Version:** 2.0.0 (Database Integration)  
**Last Updated:** October 16, 2025
