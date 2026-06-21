# 🚀 BrainDump NextGen - Quick Start Guide

**Version:** 0.0.1
**Status:** Sprint 1-2 Complete

---

## ⚡ Schnellstart

### 1. Installation & Setup

```bash
# Repository klonen
git clone <repository-url>
cd memoryX

# Setup Script ausführen
chmod +x setup.sh
./setup.sh

# oder manuell:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Entwicklung Server starten

```bash
# Entwicklung Server mit Auto-Reload
make dev

# oder manuell:
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**API verfügbar unter:** `http://localhost:8000`

### 3. Tests ausführen

```bash
# Alle Tests mit Coverage
make test

# oder manuell:
pytest tests/ -v --cov=app --cov-report=term-missing
```

### 4. API Documentation

**Interactive Swagger UI:** `http://localhost:8000/docs`
**ReDoc:** `http://localhost:8000/redoc`

---

## 🎯 Erste Schritte mit der API

### Event erstellen

```bash
curl -X POST http://localhost:8000/api/events/ \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "user_input",
    "actor": "user_123",
    "scope": "session_ai",
    "payload": {
      "message": "Was ist Machine Learning?"
    },
    "metadata": {
      "source": "web_interface"
    }
  }'
```

### Memory aus Event erstellen

```bash
curl -X POST http://localhost:8000/api/memory/ \
  -H "Content-Type: application/json" \
  -d '{
    "memory_type": "semantic",
    "title": "Machine Learning Definition",
    "content": "Machine Learning ist ein Teilgebiet der Künstlichen Intelligenz...",
    "confidence": 0.95,
    "scope": "session_ai",
    "source_events": ["<event_id_from_above>"]
  }'
```

### Memories suchen

```bash
curl -X GET "http://localhost:8000/api/memory/search?query=machine+learning"
```

### Memory Evolution (Patch erstellen)

```bash
curl -X POST http://localhost:8000/api/evolution/patch \
  -H "Content-Type: application/json" \
  -d '{
    "target_memory": "<memory_id>",
    "patch_type": "update",
    "old_value": {"confidence": 0.8},
    "new_value": {"confidence": 0.95},
    "reason": "Verifiziert durch mehrere Quellen",
    "confidence": 0.9
  }'
```

### Evolution History abrufen

```bash
curl -X GET "http://localhost:8000/api/evolution/memory/<memory_id>/history"
```

---

## 📊 API Überblick

### Event API (8 Endpoints)
- `POST /api/events/` - Event erstellen
- `GET /api/events/` - Events auflisten
- `GET /api/events/{id}` - Event by ID
- `GET /api/events/types` - Event Types
- `GET /api/events/statistics` - Statistiken
- `GET /api/events/count` - Events zählen

### Memory API (11 Endpoints)
- `POST /api/memory/` - Memory erstellen
- `GET /api/memory/` - Memories auflisten
- `GET /api/memory/{id}` - Memory by ID
- `PUT /api/memory/{id}` - Memory aktualisieren
- `GET /api/memory/search` - Memories suchen
- `GET /api/memory/types` - Memory Types
- `GET /api/memory/statistics` - Statistiken
- `GET /api/memory/event/{id}` - Memories by Event
- `GET /api/memory/count` - Memories zählen

### Evolution API (12 Endpoints)
- `POST /api/evolution/patch` - Patch erstellen
- `GET /api/evolution/patch/{id}` - Patch by ID
- `GET /api/evolution/patches` - Patches auflisten
- `GET /api/evolution/memory/{id}/history` - Evolution History
- `POST /api/evolution/memory/{id}/promote` - Memory promoten
- `POST /api/evolution/memory/{id}/deprecate` - Memory deprecieren
- `POST /api/evolution/memories/merge` - Memories mergen
- `GET /api/evolution/statistics` - Statistiken
- `GET /api/evolution/count` - Patches zählen

---

## 🔧 Development Commands

```bash
# Help
make help

# Dependencies installieren
make install

# Development Server
make dev

# Tests ausführen
make test

# Code Linting
make lint

# Code Formatting
make format

# Cleanup
make clean
```

---

## 🏗️ Architecture Overview

```
┌──────────────────────────┐
│   FastAPI Application     │
│   (app/main.py)           │
└─────────────┬────────────┘
              │
    ┌─────────┼──────────┐
    ▼         ▼          ▼

┌─────────┐ ┌─────────┐ ┌─────────────┐
│ Events  │ │ Memory  │ │  Evolution  │
│   API   │ │   API   │ │     API     │
└─────────┘ └─────────┘ └─────────────┘
    │         │             │
    ▼         ▼             ▼

┌─────────┐ ┌─────────┐ ┌─────────────┐
│  Event  │ │ Memory  │ │  Evolution  │
│ Service │ │ Service │ │   Service   │
└─────────┘ └─────────┘ └─────────────┘
    │         │             │
    ▼         ▼             ▼

┌─────────┐ ┌─────────┐ ┌─────────────┐
│  Event  │ │ Memory  │ │  Evolution  │
│   Repo  │ │   Repo  │ │     Repo    │
└─────────┘ └─────────┘ └─────────────┘
    │         │             │
    └─────────┴─────────────┘
              ▼
        ┌──────────┐
        │ SQLite   │
        │ Database │
        └──────────┘
```

---

## 📈 Aktuelle Features

### ✅ Sprint 1-2 Complete

**Core Systems:**
- ✅ Event System (Append-only Truth Layer)
- ✅ Memory Card System (Typed Information Storage)
- ✅ Evolution Memory (Memory Evolution & Fitness Scoring)
- ✅ Comprehensive Test Suite (80%+ Coverage)

**API Features:**
- ✅ 31+ RESTful Endpoints
- ✅ OpenAPI Documentation
- ✅ Request/Response Validation
- ✅ Error Handling
- ✅ Pagination Support

**Data Features:**
- ✅ 10 Event Types
- ✅ 8 Memory Types
- ✅ 6 Patch Types
- ✅ Fitness Scoring
- ✅ Source Event References

---

## 🔮 Next Steps

### Sprint 3 (Geplant)
- Memory Gatekeeper (Governance)
- Governance Rules Engine
- Dream Engine (Daydream)

### Sprint 4-6 (Geplant)
- Memory Graph (Relationships)
- fRAG Engine (Retrieval)
- Planning Engine (Decision Making)
- Evaluation Layer (Quality)

---

## 📚 Documentation

- **API Documentation:** `API_DOCUMENTATION.md`
- **Implementation Status:** `IMPLEMENTATION_STATUS.md`
- **Sprint Planning:** `sprint_planning_review.md`
- **Main README:** `README.md`
- **Spec:** `spec.md`

---

## 🧪 Testing

```bash
# Alle Tests
pytest tests/ -v

# Mit Coverage
pytest tests/ -v --cov=app --cov-report=term-missing

# Spezifische Tests
pytest tests/test_events.py -v
pytest tests/test_memory.py -v
pytest tests/test_integration.py -v

# HTML Coverage Report
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html
```

---

## 🐛 Troubleshooting

### Database Issues
```bash
# Database neu erstellen
rm braindump.db
make dev  # Erstellt automatisch neue DB
```

### Port bereits in Verwendung
```bash
# Anderen Port verwenden
uvicorn app.main:app --port 8001
```

### Dependencies Probleme
```bash
# Virtual Environment neu erstellen
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 🚀 Production Deployment

### Environment Variables
```bash
export DEBUG=false
export DATABASE_URL=postgresql+asyncpg://user:pass@host/db
export LOG_LEVEL=INFO
```

### Running with Gunicorn
```bash
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

---

## 📞 Support & Community

- **Issues:** GitHub Issues
- **Documentation:** `docs/` folder
- **Examples:** `EXAMPLES.md`

---

**Version:** 0.0.1 (Sprint 1-2 Complete)
**Next Release:** Sprint 3 (Memory Gatekeeper & Governance)

*Quick Start Guide - 2025-06-20*