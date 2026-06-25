# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

## Project Overview

**BrainDump NextGen** is an Agentic Memory Operating System for GenAI Applications. It provides persistent memory, governance, learning capability, planning capability, auditability, and knowledge evolution for AI agents.

**Technology Stack:**
- Python 3.12 with FastAPI (async/await)
- Pydantic v2 for validation
- SQLAlchemy 2.0 (async) with SQLite (Phase 1) → PostgreSQL (Phase 2)
- FAISS (Phase 1) → Qdrant (Phase 2) for vector search
- NetworkX (Phase 1) → Neo4j (Phase 2) for graph operations

## Development Commands

```bash
# Setup (first time only)
chmod +x setup.sh && ./setup.sh
# Or: make install

# Development server with auto-reload
make dev
# Or: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests (80%+ coverage required)
make test
# Or: pytest tests/ -v --cov=app --cov-report=term-missing

# Code quality checks
make lint      # ruff + mypy
make format    # black + ruff --fix

# Cleanup
make clean     # Remove Python cache files
```

**Testing individual tests:**
```bash
# Single test file
pytest tests/test_events.py -v

# Single test function
pytest tests/test_events.py::test_create_event -v

# With coverage (specific module)
pytest tests/test_events.py -v --cov=app.services.event_service --cov-report=term-missing
```

## Architecture Overview

The system follows a **layered architecture** with clear separation:

```
FastAPI Application (app/main.py)
    ↓
API Routes Layer (app/api/) - 17+ route files
    ↓
Service Layer (app/services/) - Business logic
    ↓
Repository Layer (app/repositories/) - Data access
    ↓
Database Models (app/models/) → SQLite/PostgreSQL
```

**Key directories:**
- `app/api/` - FastAPI route handlers (auth, deps, dream, evaluation, events, evolution, frag, gatekeeper, governance, graph, memory, planning, rate_limit, swarm)
- `app/services/` - Business logic layer
- `app/repositories/` - Data access layer (SQLAlchemy)
- `app/models/` - Pydantic/SQLAlchemy models
- `app/swarm/` - Multi-agent orchestration components
- `tests/` - pytest test suite (80%+ coverage required)

**Core Systems (Sprint 1-4 Complete):**
1. **Event System** - Append-only truth layer with 10 event types
2. **Memory Card System** - Typed information storage with 8 memory types
3. **Evolution Memory** - Memory evolution through patches with fitness scoring
4. **Authentication** - JWT-based with role-based access
5. **Governance** - Executable memory rules and policies
6. **Memory Graph** - Knowledge relationship management
7. **fRAG Engine** - Fragment-aware retrieval generation
8. **Evaluation Layer** - Quality metrics and benchmarking
9. **Dream Engine** - Asynchronous consolidation (daydream, nightdream, deepdream)
10. **Memory Gatekeeper** - Critical validation component
11. **Planning System** - Multi-step agent task planning with dependency tracking
12. **Swarm System** - Multi-agent orchestration and coordination
13. **Rate Limiting** - Request throttling with configurable limits

## Key Conventions

**Async/Await:** The entire stack is async. Always use `async def` for route handlers, services, and repositories. Database operations use `async_session`.

**Repository Pattern:** Data access goes through repository classes in `app/repositories/`. Services should not access the database directly.

**Database Sessions:** Use `async def get_db_session()` dependency for database access. Sessions are automatically committed on success and rolled back on error.

**FastAPI Dependencies:** Use dependency injection via `app/api/deps.py` for authentication, database sessions, and services. Pattern: `async def foo(dep: SomeType = Depends(get_some_dep))`.

**Pydantic Models:** Separate request/response models from database models. Database models use SQLAlchemy, API models use Pydantic.

**Append-Only Design:** Events are never deleted or modified. Memory evolution uses patches instead of overwrites.

**Exception Hierarchy:** Use specific exceptions from `app/exceptions.py` instead of generic ones:
- `ValidationError` - Input validation failures
- `NotFoundError` - Resource not found
- `ConflictError` - Duplicate/conflicting resources
- `BusinessRuleError` - Business logic violations
- `AuthenticationError` / `AuthorizationError` - Auth failures
- `GovernanceViolationError` - Governance rule violations

**Authentication Pattern:** JWT-based with role-based access:
- Use `Depends(get_current_user)` for authenticated routes
- Use `Depends(require_admin)` for admin-only routes
- Use `Depends(require_role(UserRole.USER, ...))` for specific roles

**Type Hints:** All functions should have complete type hints. The project uses `mypy --strict` for type checking.

**Configuration:** Use `app/config.py` and `pydantic-settings`. Environment variables defined in `.env.example`.

**Code Style:** Line length 100 characters. Python 3.12+. Use `make format` to apply black and ruff.

## Testing Approach

- **Framework:** pytest with `pytest-asyncio` (auto mode)
- **Coverage:** Minimum 80% required (enforced by pytest.ini)
- **Test Database:** SQLite in-memory for isolation
- **Markers:** `@pytest.mark.asyncio`, `@pytest.mark.integration`, `@pytest.mark.unit`

**Test patterns:**
```python
# Async test
@pytest.mark.asyncio
async def test_something():
    result = await service.do_something()
    assert result is not None
```

## API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health check: `http://localhost:8000/health`

## Important Files

- `spec.md` - Complete technical specification (German)
- `IMPLEMENTATION_STATUS.md` - Sprint progress tracking
- `EXAMPLES.md` - Best practices and anti-patterns
- `sprint*.md` - Sprint planning documents (sprint2_plan.md, sprint3-4_plan.md, sprint5-6_plan.md)
- `app/config.py` - Application settings with Pydantic
- `app/database.py` - SQLAlchemy async session setup
- `app/api/deps.py` - FastAPI dependency injection (auth, services, db)
- `app/exceptions.py` - Application exception hierarchy
- `app/error_handlers.py` - Global exception handlers
- `app/logging_config.py` - Structured logging configuration
- `pytest.ini` - Test configuration with coverage settings
- `pyproject.toml` - Project metadata and tool configurations (black, ruff, mypy)
