# Student Surveillance System — Codebase Report (v1)

## 1. Snapshot
- **Purpose** Production-ready face recognition plus attendance tracking built on FastAPI and InsightFace.
- **Primary entry points** REST/UI server in `src/api.py`; CLI launcher in `scripts/run_system.py` (runs `uvicorn src.api:app`).
- **Deployment profile** Docker-ready via `Dockerfile`/`docker-compose.yml`, optional PostgreSQL & Redis sidecars.

## 2. Architecture Overview
### 2.1 Core runtime
- **FaceRecognitionSystem** (`src/face_system.py`) centralizes detection, embedding storage, recognition, and attendance logging.
- **FastAPI layer** (`src/api.py`) exposes enrollment/recognition/analytics endpoints and serves a rich HTML/JS UI.
- **Analytics pipeline** (`src/analytics.py`) converts attendance CSV data into reports, health metrics, and exports.

### 2.2 Data artifacts
- **Embeddings store** `data/processed/face_embeddings.json` (JSON per-person embeddings + quality metadata).
- **Attendance log** `data/processed/attendance.csv` with daily deduplication.
- **Optional FAISS index** `data/processed/faiss_index.bin` and `faiss_metadata.json` when high-performance matcher is used.

### 2.3 Prepared integrations
- **Database** PostgreSQL URL scaffolded in `src/core/config.py` (not yet consumed in code).
- **Messaging/cache** RabbitMQ and Redis URLs pre-configured for future expansion.

## 3. Configuration & Environment
- **Runtime management** Poetry (`pyproject.toml`) with Python 3.11; core deps include `fastapi`, `insightface`, `opencv-python`, `numpy`; enhanced features rely on `pandas`, `plotly`, `faiss-cpu`.
- **Settings** `src/core/config.py` (`Settings` via `pydantic_settings`) covers detection/recognition thresholds, quality guardrails, file locations, and service URLs. Constructor auto-creates `data/models/` and `logs/` directories.
- **Environment overrides** `.env` / `.env.example` hold runtime configuration (existing `.env` at 716 bytes).

## 4. Application Modules
### 4.1 API layer — `src/api.py`
- **Initialization** FastAPI app titled "Face Recognition API" (v2.0.0) with singleton `FaceRecognitionSystem` instance.
- **Endpoint groups**
  - **System** `/`, `/status`, `/system/health` surface enrollment counts, model info, and analytics health (fallback guidance if analytics deps missing).
  - **Enrollment** `/enroll`, `/delete/{name}`, `/clear` manage biometric enrollment lifecycle with quality feedback.
  - **Recognition** `/recognize` accepts image uploads, returns `RecognitionResponse`, and logs attendance via `log_attendance()`.
  - **Attendance** `/attendance`, `/attendance/today` expose summary metrics and daily presence list.
  - **Analytics** `/analytics/dashboard`, `/analytics/trends`, `/analytics/export` delegate heavy lifting to `AttendanceAnalytics`.
  - **Web UI** `/ui` delivers comprehensive HTML/JS client: webcam capture, guided 15-shot enrollment workflow, live recognition overlays, analytics modal, and export actions.
- **Utilities** `decode_image()` for upload decoding; Pydantic models `FaceResult`/`RecognitionResponse` define response schema.

### 4.2 Recognition engine — `src/face_system.py`
- **Detector setup** InsightFace `FaceAnalysis` initialized for CPU (`ctx_id=0`, `det_size=(640, 640)`, `det_thresh=0.6`).
- **Enrollment pipeline** `detect_and_extract()` scores faces (size, pose, sharpness), persists best embeddings with metadata, `enroll_multiple_images()` aggregates stats; per-user cap of 20 embeddings.
- **Recognition pipeline** `recognize_face()` calculates quality-weighted cosine similarities, averages top-3 per identity, adjusts threshold by face quality.
- **Attendance logging** `log_attendance()` writes deduplicated entries to CSV and maintains in-memory cache via `_load_today_attendance()`.
- **Maintenance** `save_embeddings()`, `load_embeddings()` (backward compatible), `clear_all_data()`, `get_attendance_stats()` for reporting.

### 4.3 Configuration core — `src/core/config.py`
- **Settings model** Extends `BaseSettings` with `.env` reading, `extra="ignore"`.
- **Key parameters** Detection model pack, recognition thresholds, batch size, quality filter limits, database/messaging URLs, logging paths.
- **Filesystem bootstrap** Ensures `model_cache_dir` and log directory exist at instantiation.

### 4.4 Analytics suite — `src/analytics.py`
- **Data ingestion** `load_attendance_data()` returns pandas DataFrame with `DateTime` field and numeric confidence.
- **Reporting APIs**
  - `get_daily_stats()`, `get_person_stats()`, `get_time_patterns()` for aggregated attendance insights.
  - `get_confidence_analysis()` highlights distribution and low-confidence alerts.
  - `get_system_health()` inspects embeddings volume, recent activity, and data quality.
  - `generate_report()` produces consolidated dict; `export_report()` saves JSON/CSV with timestamped filenames.
  - `get_attendance_trends()` calculates weekly slopes (increasing/decreasing/stable labels).

### 4.5 Models package — `src/models/`
- **`detection.py`** `FaceDetector` lazily loads InsightFace RetinaFace with optional GPU and returns `DetectedFace` containers (bbox, landmarks, score, crop, original object).
- **`recognition.py`** `EmbeddingExtractor` acquires 512-dim ArcFace embeddings; `FaceRecognizer` manages minimal enrollment/matching with cosine similarity; `StudentMatch` dataclass encapsulates match status.
- **`quality_filter.py`** `FaceQualityFilter` checks size, Laplacian blur, brightness, pose geometry; `QualityMetrics` dataclass summarizes pass/fail state.
- **`faiss_matcher.py`** Optional FAISS-backed matcher supporting `IndexFlatIP` / `IndexIVFFlat`, optional GPU, persistence, rebuild-on-delete, and statistics (graceful warning if `faiss` missing).

### 4.6 Test suite — `src/tests/`
- **`test_detection.py`** Asserts detector initialization and `DetectedFace` properties.
- **`test_quality_filter.py`** Covers quality thresholds, blur/brightness checks, and filter acceptance logic.
- **`test_recognition.py`** Validates extractor/recognizer setup, enrollment lifecycle, cosine similarity, `StudentMatch` repr.

## 5. Tooling & Operations
- **Scripts** `scripts/run_system.py` (port checks, `uvicorn --reload` launch) and `scripts/install_enhanced.py` (pip installs, optional `poetry add`, smoke tests, FAISS/analytics validation, directory scaffolding).
- **Docker & orchestration** `docker-compose.yml` maps `/dev/video0` for webcam, mounts `data/` & `logs/`, sets healthcheck on `/`, documents optional PostgreSQL/Redis services and volume wiring.
- **Logging** Default sink `./logs/app.log` with `INFO` level from `Settings`.

## 6. Data & Storage Layout
- **`data/models/`** InsightFace model cache directory ensured by configuration.
- **`data/processed/`** Holds runtime artifacts: attendance CSV, embeddings JSON, exported analytics reports, FAISS index/metadata.
- **Auxiliary directories** `data/analytics/`, `data/exports/`, `data/faiss/`, `logs/analytics/` pre-created by enhanced install script.

## 7. Testing & Quality Metrics
- **Pytest configuration** Defined in `pyproject.toml` (asyncio auto mode, coverage reports via `--cov=src`).
- **Coverage baseline** README cites ~47% coverage; additional tests needed for API and analytics layers.

## 8. Future Enhancements & Notes
- **Project log** `project_log.md` captures historical change notes.
- **Roadmap signals** README highlights multi-camera support, database integration, FAISS scaling, analytics tooling already scaffolded for expansion.
- **Dependency reminders** Analytics endpoints require `pandas`; FAISS matcher requires `faiss-cpu` (warnings emitted if unavailable).
