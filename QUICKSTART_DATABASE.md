# PostgreSQL Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Option 1: Docker (Easiest - Recommended)

```bash
# 1. Start everything (PostgreSQL + API)
docker-compose up --build

# 2. Access the application
# API: http://localhost:8000
# Swagger Docs: http://localhost:8000/docs
# Web UI: http://localhost:8000/ui
```

**That's it! PostgreSQL is running and the database is initialized automatically.**

---

### Option 2: Local PostgreSQL

**Step 1: Install PostgreSQL**

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# macOS
brew install postgresql@15
brew services start postgresql@15

# Windows
# Download from: https://www.postgresql.org/download/windows/
```

**Step 2: Create Database**

```bash
# Open PostgreSQL prompt
sudo -u postgres psql

# Run these commands
CREATE DATABASE surveillance_db;
CREATE USER surveillance WITH PASSWORD 'changeme_secure_password';
GRANT ALL PRIVILEGES ON DATABASE surveillance_db TO surveillance;
\q
```

**Step 3: Configure Environment**

```bash
# Copy example file
cp .env.example .env

# Edit .env and update this line:
DATABASE_URL=postgresql://surveillance:changeme_secure_password@localhost:5432/surveillance_db
```

**Step 4: Initialize Database**

```bash
poetry install
poetry run python scripts/init_database.py
```

**Step 5: Start Application**

```bash
poetry run python scripts/run_system.py
```

**Access:** http://localhost:8000

---

## 📦 Migrate Existing Data

If you have existing `face_embeddings.json` or `attendance.csv`:

```bash
# After initializing database, run migration
poetry run python scripts/migrate_file_to_db.py
```

This will import all your existing data into PostgreSQL.

---

## ✅ Verify Everything Works

```bash
# Test database connection
poetry run python -c "from src.db.database import test_connection; print('✓ Database connected!' if test_connection() else '✗ Connection failed')"

# Check tables exist
psql -U surveillance -d surveillance_db -c "\dt"

# Start API and visit
curl http://localhost:8000/
```

---

## 🎯 Test the API

**Enroll a person:**
```bash
curl -X POST http://localhost:8000/api/enroll \
  -F "name=John Doe" \
  -F "files=@photo.jpg"
```

**Recognize a face:**
```bash
curl -X POST http://localhost:8000/api/recognize \
  -F "file=@test.jpg"
```

**Get attendance:**
```bash
curl http://localhost:8000/api/attendance
```

---

## 📊 View Database

```bash
# Connect to database
psql -U surveillance -d surveillance_db

# View all persons
SELECT * FROM persons;

# View attendance
SELECT p.name, a.confidence, a.recognized_at
FROM attendance_log a
JOIN persons p ON a.person_id = p.id
ORDER BY a.recognized_at DESC
LIMIT 10;
```

---

## 🔧 Troubleshooting

**Issue: "Could not connect to database"**

```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql  # Linux
brew services list  # macOS

# Test connection manually
psql -U surveillance -d surveillance_db -h localhost
```

**Issue: "relation does not exist"**

```bash
# Tables weren't created - run initialization
poetry run python scripts/init_database.py
```

**Issue: Port 5432 already in use**

```bash
# Check what's using port 5432
sudo lsof -i :5432  # Linux/Mac
netstat -ano | findstr :5432  # Windows

# Stop existing PostgreSQL or change port in .env
```

---

## 📚 Next Steps

- Read `DATABASE_SETUP.md` for complete setup guide
- Read `README_DATABASE.md` for architecture details
- Read `IMPLEMENTATION_SUMMARY.md` for technical details

---

## 🎉 Success!

You now have a production-ready face recognition system with PostgreSQL backend!

**Features enabled:**
- ✅ Persistent data storage
- ✅ ACID compliance
- ✅ Automatic deduplication
- ✅ Efficient querying
- ✅ Scalable to 10,000+ faces
- ✅ Docker deployment ready

**Start using the system:**
- Web UI: http://localhost:8000/ui
- API Docs: http://localhost:8000/docs
