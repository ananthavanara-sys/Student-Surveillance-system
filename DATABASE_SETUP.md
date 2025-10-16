# PostgreSQL Database Setup Guide

This guide explains how to set up and use PostgreSQL with the Face Recognition System.

---

## Overview

The system now uses **PostgreSQL** as the primary database for:
- **Person/Student records** - Name and metadata
- **Face embeddings** - 512-dimensional ArcFace vectors with quality scores
- **Attendance logs** - Timestamped attendance records with deduplication

**Benefits over file-based storage:**
- ✅ ACID compliance and data integrity
- ✅ Concurrent access from multiple clients
- ✅ Efficient querying and indexing
- ✅ Better scalability (10,000+ faces)
- ✅ Built-in backup and recovery tools

---

## Quick Start

### Option 1: Docker Compose (Recommended)

**Start all services including PostgreSQL:**

```bash
docker-compose up --build
```

This automatically:
- Starts PostgreSQL container
- Creates database `surveillance_db`
- Initializes tables on application startup
- Starts the face recognition API

**Access:**
- API: http://localhost:8000
- Database: `postgresql://surveillance:changeme_secure_password@localhost:5432/surveillance_db`

### Option 2: Local PostgreSQL Installation

**1. Install PostgreSQL**

**Windows:**
```bash
# Download from https://www.postgresql.org/download/windows/
# Or use chocolatey
choco install postgresql
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

**macOS:**
```bash
brew install postgresql@15
brew services start postgresql@15
```

**2. Create Database and User**

```bash
# Access PostgreSQL as superuser
psql -U postgres

# Create user and database
CREATE USER surveillance WITH PASSWORD 'changeme_secure_password';
CREATE DATABASE surveillance_db OWNER surveillance;
GRANT ALL PRIVILEGES ON DATABASE surveillance_db TO surveillance;

# Exit
\q
```

**3. Configure Environment**

Create `.env` file (copy from `.env.example`):

```env
DATABASE_URL=postgresql://surveillance:changeme_secure_password@localhost:5432/surveillance_db
```

**4. Initialize Database**

```bash
# Install dependencies (if not already done)
poetry install

# Initialize database tables
poetry run python scripts/init_database.py
```

**5. Start Application**

```bash
poetry run python scripts/run_system.py
```

---

## Database Schema

### Tables

#### **persons**
Stores person/student records.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key (auto-increment) |
| name | VARCHAR(255) | Unique person name |
| created_at | TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | Last update time |

**Indexes:**
- PRIMARY KEY on `id`
- UNIQUE INDEX on `name`

#### **face_embeddings**
Stores face embeddings with quality metrics.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key (auto-increment) |
| person_id | INTEGER | Foreign key to persons.id |
| embedding | FLOAT[] | 512-dimensional vector (PostgreSQL array) |
| quality_score | FLOAT | Face quality metric (0.0-1.0) |
| det_score | FLOAT | Detection confidence (0.0-1.0) |
| created_at | TIMESTAMP | Embedding creation time |

**Indexes:**
- PRIMARY KEY on `id`
- INDEX on `person_id`
- COMPOSITE INDEX on `(person_id, quality_score)`

**Constraints:**
- FOREIGN KEY: `person_id` → `persons.id` (CASCADE DELETE)

#### **attendance_log**
Stores attendance records with deduplication.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key (auto-increment) |
| person_id | INTEGER | Foreign key to persons.id |
| recognized_at | TIMESTAMP | Recognition timestamp |
| confidence | FLOAT | Recognition confidence score |
| status | VARCHAR(50) | Status (default: "Present") |

**Indexes:**
- PRIMARY KEY on `id`
- INDEX on `person_id`
- INDEX on `recognized_at`
- COMPOSITE INDEX on `(person_id, recognized_at)`

**Constraints:**
- FOREIGN KEY: `person_id` → `persons.id` (CASCADE DELETE)
- UNIQUE CONSTRAINT on `(person_id, recognized_at)` - prevents duplicates

---

## Data Migration

### Migrate from File-Based Storage

If you have existing data in JSON/CSV format, migrate it to PostgreSQL:

```bash
# 1. Initialize database first
poetry run python scripts/init_database.py

# 2. Migrate existing data
poetry run python scripts/migrate_file_to_db.py
```

**What gets migrated:**
- `data/processed/face_embeddings.json` → `persons` + `face_embeddings` tables
- `data/processed/attendance.csv` → `attendance_log` table

**Note:** Original files are preserved as backup.

---

## Database Management

### Using Alembic Migrations

**Create a new migration:**
```bash
# Auto-generate from model changes
poetry run alembic revision --autogenerate -m "add new column"

# Create empty migration
poetry run alembic revision -m "custom migration"
```

**Apply migrations:**
```bash
# Upgrade to latest
poetry run alembic upgrade head

# Upgrade to specific version
poetry run alembic upgrade <revision_id>

# Downgrade one version
poetry run alembic downgrade -1
```

**Check migration status:**
```bash
# Show current version
poetry run alembic current

# Show migration history
poetry run alembic history
```

### Direct Database Access

**Using psql:**
```bash
psql -U surveillance -d surveillance_db -h localhost
```

**Common queries:**
```sql
-- Count persons
SELECT COUNT(*) FROM persons;

-- Count embeddings per person
SELECT p.name, COUNT(e.id) as embedding_count
FROM persons p
LEFT JOIN face_embeddings e ON p.id = e.person_id
GROUP BY p.name;

-- Today's attendance
SELECT p.name, a.confidence, a.recognized_at
FROM attendance_log a
JOIN persons p ON a.person_id = p.id
WHERE DATE(a.recognized_at) = CURRENT_DATE
ORDER BY a.recognized_at DESC;

-- Average recognition confidence per person
SELECT p.name, 
       COUNT(a.id) as attendance_count,
       AVG(a.confidence) as avg_confidence
FROM persons p
JOIN attendance_log a ON p.id = a.person_id
GROUP BY p.name
ORDER BY avg_confidence DESC;
```

### Backup and Restore

**Backup database:**
```bash
pg_dump -U surveillance -d surveillance_db -h localhost -F c -f backup_$(date +%Y%m%d).dump
```

**Restore from backup:**
```bash
pg_restore -U surveillance -d surveillance_db -h localhost backup_20251016.dump
```

**Export to SQL:**
```bash
pg_dump -U surveillance -d surveillance_db -h localhost > backup.sql
```

---

## Configuration

### Environment Variables

**Required:**
```env
DATABASE_URL=postgresql://username:password@host:port/database
```

**Optional:**
```env
# Database pool settings
DATABASE_POOL_SIZE=20          # Connection pool size
DATABASE_MAX_OVERFLOW=10       # Max overflow connections
DATABASE_ECHO=false            # Log SQL queries (debug)
```

### Connection String Format

```
postgresql://[user]:[password]@[host]:[port]/[database]
```

**Examples:**

**Local:**
```
postgresql://surveillance:password@localhost:5432/surveillance_db
```

**Docker:**
```
postgresql://surveillance:password@postgres:5432/surveillance_db
```

**Remote:**
```
postgresql://user:pass@db.example.com:5432/surveillance_db
```

---

## Troubleshooting

### Connection Errors

**Error: "could not connect to server"**

**Solutions:**
1. Check PostgreSQL is running:
   ```bash
   # Linux/Mac
   sudo systemctl status postgresql
   
   # Docker
   docker ps | grep postgres
   ```

2. Verify connection details in `.env`
3. Test connection:
   ```bash
   psql -U surveillance -d surveillance_db -h localhost
   ```

**Error: "password authentication failed"**

**Solutions:**
1. Verify username/password in `.env`
2. Reset password:
   ```sql
   ALTER USER surveillance WITH PASSWORD 'new_password';
   ```

**Error: "database does not exist"**

**Solutions:**
1. Create database:
   ```sql
   CREATE DATABASE surveillance_db OWNER surveillance;
   ```

### Performance Issues

**Slow queries:**

1. **Analyze query performance:**
   ```sql
   EXPLAIN ANALYZE SELECT * FROM face_embeddings WHERE person_id = 1;
   ```

2. **Rebuild indexes:**
   ```sql
   REINDEX TABLE face_embeddings;
   ```

3. **Vacuum database:**
   ```sql
   VACUUM ANALYZE;
   ```

**Too many connections:**

1. Check active connections:
   ```sql
   SELECT count(*) FROM pg_stat_activity;
   ```

2. Adjust pool size in code or increase PostgreSQL limit:
   ```ini
   # postgresql.conf
   max_connections = 100
   ```

---

## Advanced Features

### Vector Search with pgvector (Optional)

For ultra-fast similarity search with 100,000+ faces, install pgvector extension:

**1. Install pgvector:**
```bash
# From source
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

**2. Enable extension:**
```sql
CREATE EXTENSION vector;
```

**3. Update embeddings table:**
```sql
ALTER TABLE face_embeddings 
ALTER COLUMN embedding TYPE vector(512);

-- Create similarity index
CREATE INDEX ON face_embeddings 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

**4. Query with similarity:**
```sql
-- Find top 5 similar faces
SELECT p.name, 
       1 - (e.embedding <=> '[0.1, 0.2, ...]'::vector) as similarity
FROM face_embeddings e
JOIN persons p ON e.person_id = p.id
ORDER BY e.embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 5;
```

### Monitoring and Metrics

**Install pg_stat_statements:**
```sql
CREATE EXTENSION pg_stat_statements;
```

**View slow queries:**
```sql
SELECT query, calls, mean_exec_time, total_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

---

## Production Recommendations

### Security

1. **Use strong passwords:**
   ```bash
   # Generate random password
   openssl rand -base64 32
   ```

2. **Restrict network access:**
   ```ini
   # pg_hba.conf
   host    surveillance_db    surveillance    10.0.0.0/8    md5
   ```

3. **Enable SSL:**
   ```env
   DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
   ```

### Performance

1. **Tune PostgreSQL settings:**
   ```ini
   # postgresql.conf
   shared_buffers = 256MB
   effective_cache_size = 1GB
   work_mem = 16MB
   maintenance_work_mem = 256MB
   ```

2. **Regular maintenance:**
   ```bash
   # Weekly vacuum
   vacuumdb -U surveillance -d surveillance_db --analyze
   ```

3. **Monitor table sizes:**
   ```sql
   SELECT 
       schemaname,
       tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
   FROM pg_tables
   WHERE schemaname = 'public'
   ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
   ```

### Backup Strategy

1. **Automated daily backups:**
   ```bash
   # Add to cron
   0 2 * * * pg_dump -U surveillance surveillance_db > /backups/daily_$(date +\%Y\%m\%d).sql
   ```

2. **Continuous archiving with WAL:**
   ```ini
   # postgresql.conf
   wal_level = replica
   archive_mode = on
   archive_command = 'cp %p /archive/%f'
   ```

---

## Support

For issues or questions:
- Check logs: `tail -f logs/app.log`
- PostgreSQL logs: `/var/log/postgresql/postgresql-15-main.log`
- GitHub Issues: [project repository]

---

**Last Updated:** October 16, 2025
