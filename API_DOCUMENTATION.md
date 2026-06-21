# BrainDump NextGen - API Documentation

**Version:** 0.0.1
**Base URL:** `http://localhost:8000`
**API Prefix:** `/api`

---

## Overview

BrainDump NextGen provides a RESTful API for managing events and memory cards in an agentic memory operating system. All endpoints return JSON responses and follow HTTP status conventions.

---

## Authentication

Currently in development - no authentication required for Phase 1.

---

## Response Format

All endpoints return JSON with consistent structure:

**Success Response:**
```json
{
  "data": { ... },
  "status": "success"
}
```

**Error Response:**
```json
{
  "error": "Error Type",
  "message": "Detailed error message",
  "status": "error"
}
```

---

## Core Endpoints

### Health & Info

#### `GET /health`
Health check endpoint for monitoring.

**Response:**
```json
{
  "status": "ok",
  "application": "BrainDump NextGen",
  "version": "0.0.1"
}
```

#### `GET /api/info`
System information and configuration.

**Response:**
```json
{
  "application": "BrainDump NextGen",
  "version": "0.0.1",
  "debug": true,
  "database": "sqlite",
  "log_level": "INFO"
}
```

---

## Event API

### Events represent the append-only truth layer of the system.

#### `POST /api/events/`
Create a new event.

**Request Body:**
```json
{
  "event_type": "user_input",
  "actor": "user_123",
  "scope": "session_456",
  "payload": {
    "message": "Hello, world!"
  },
  "metadata": {
    "source": "web"
  }
}
```

**Event Types:**
- `user_input` - User input events
- `agent_action` - Agent actions
- `tool_call` - Tool/function calls
- `decision` - Decision events
- `memory_update` - Memory update events
- `correction` - Correction events
- `failure` - Failure events
- `success` - Success events
- `policy_violation` - Policy violations
- `risk_event` - Risk events

**Response:** `201 Created`
```json
{
  "event_id": "uuid-v4",
  "timestamp": "2025-01-15T10:30:00Z",
  "event_type": "user_input",
  "actor": "user_123",
  "scope": "session_456",
  "payload": { ... },
  "metadata": { ... }
}
```

#### `GET /api/events/`
List events with filtering and pagination.

**Query Parameters:**
- `event_type` (optional) - Filter by event type
- `actor` (optional) - Filter by actor
- `scope` (optional) - Filter by scope
- `limit` (default: 100, max: 1000) - Results per page
- `offset` (default: 0) - Pagination offset

**Response:** `200 OK`
```json
[
  {
    "event_id": "uuid-v4",
    "timestamp": "2025-01-15T10:30:00Z",
    "event_type": "user_input",
    "actor": "user_123",
    "scope": "session_456",
    "payload": { ... },
    "metadata": { ... }
  }
]
```

#### `GET /api/events/{event_id}`
Get specific event by ID.

**Response:** `200 OK`
```json
{
  "event_id": "uuid-v4",
  "timestamp": "2025-01-15T10:30:00Z",
  "event_type": "user_input",
  "actor": "user_123",
  "scope": "session_456",
  "payload": { ... },
  "metadata": { ... }
}
```

#### `GET /api/events/types`
Get available event types.

**Response:** `200 OK`
```json
["user_input", "agent_action", "tool_call", ...]
```

#### `GET /api/events/statistics`
Get event statistics.

**Query Parameters:**
- `scope` (optional) - Filter by scope

**Response:** `200 OK`
```json
{
  "total_events": 150,
  "by_event_type": {
    "user_input": 45,
    "agent_action": 38,
    "tool_call": 22,
    ...
  },
  "scope": "all"
}
```

#### `GET /api/events/count`
Count events matching filters.

**Query Parameters:**
- `event_type` (optional) - Filter by event type
- `actor` (optional) - Filter by actor
- `scope` (optional) - Filter by scope

**Response:** `200 OK`
```json
{
  "count": 150
}
```

---

## Memory API

### Memory cards store typed information in the system.

#### `POST /api/memory/`
Create a new memory card.

**Request Body:**
```json
{
  "memory_type": "semantic",
  "title": "Python Programming",
  "content": "Python is a high-level programming language...",
  "confidence": 0.9,
  "scope": "global",
  "source_events": ["event-uuid-v4"]
}
```

**Memory Types:**
- `episodic` - Specific experiences and events
- `semantic` - General knowledge and facts
- `procedural` - How-to knowledge and skills
- `preference` - User preferences and settings
- `governance` - Rules and policies
- `risk` - Risk assessments and warnings
- `skill` - Learned skills and capabilities
- `decision` - Decisions made with reasoning

**Response:** `201 Created`
```json
{
  "memory_id": "uuid-v4",
  "memory_type": "semantic",
  "title": "Python Programming",
  "content": "Python is a high-level programming language...",
  "confidence": 0.9,
  "scope": "global",
  "source_events": ["event-uuid-v4"],
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

#### `GET /api/memory/`
List memory cards with filtering and pagination.

**Query Parameters:**
- `memory_type` (optional) - Filter by memory type
- `scope` (optional) - Filter by scope
- `min_confidence` (optional) - Minimum confidence score (0-1)
- `limit` (default: 100, max: 1000) - Results per page
- `offset` (default: 0) - Pagination offset

**Response:** `200 OK`
```json
[
  {
    "memory_id": "uuid-v4",
    "memory_type": "semantic",
    "title": "Python Programming",
    "content": "Python is a high-level programming language...",
    "confidence": 0.9,
    "scope": "global",
    "source_events": [...],
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
  }
]
```

#### `GET /api/memory/search`
Search memory cards by title and content.

**Query Parameters:**
- `query` (required) - Search query string
- `memory_type` (optional) - Filter by memory type
- `scope` (optional) - Filter by scope
- `limit` (default: 100, max: 1000) - Maximum results

**Response:** `200 OK`
```json
[
  {
    "memory_id": "uuid-v4",
    "memory_type": "semantic",
    "title": "Python Programming",
    "content": "...",
    "confidence": 0.9,
    ...
  }
]
```

#### `GET /api/memory/{memory_id}`
Get specific memory card by ID.

**Response:** `200 OK`
```json
{
  "memory_id": "uuid-v4",
  "memory_type": "semantic",
  "title": "Python Programming",
  "content": "Python is a high-level programming language...",
  "confidence": 0.9,
  "scope": "global",
  "source_events": [...],
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

#### `PUT /api/memory/{memory_id}`
Update a memory card (partial update).

**Request Body:**
```json
{
  "title": "Updated Title",
  "confidence": 0.95
}
```

**Response:** `200 OK`
```json
{
  "memory_id": "uuid-v4",
  "memory_type": "semantic",
  "title": "Updated Title",
  "content": "Python is a high-level programming language...",
  "confidence": 0.95,
  "scope": "global",
  "source_events": [...],
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T11:00:00Z"
}
```

#### `GET /api/memory/types`
Get available memory types.

**Response:** `200 OK`
```json
["episodic", "semantic", "procedural", ...]
```

#### `GET /api/memory/statistics`
Get memory card statistics.

**Query Parameters:**
- `scope` (optional) - Filter by scope

**Response:** `200 OK`
```json
{
  "total_memories": 250,
  "by_memory_type": {
    "semantic": 85,
    "episodic": 62,
    "procedural": 48,
    ...
  },
  "scope": "all"
}
```

#### `GET /api/memory/event/{event_id}`
Get all memory cards derived from a specific event.

**Response:** `200 OK`
```json
[
  {
    "memory_id": "uuid-v4",
    "memory_type": "semantic",
    "title": "Knowledge from Event",
    "source_events": ["event-uuid-v4"],
    ...
  }
]
```

#### `GET /api/memory/count`
Count memory cards matching filters.

**Query Parameters:**
- `memory_type` (optional) - Filter by memory type
- `scope` (optional) - Filter by scope

**Response:** `200 OK`
```json
{
  "count": 250
}
```

---

## Error Responses

### 400 Bad Request
Invalid request data or parameters.

```json
{
  "detail": "Invalid event type: invalid_type. Must be one of: user_input, agent_action, ..."
}
```

### 404 Not Found
Resource not found.

```json
{
  "detail": "Event 123e4567-e89b-12d3-a456-426614174000 not found"
}
```

### 422 Validation Error
Request validation failed.

```json
{
  "detail": [
    {
      "loc": ["body", "confidence"],
      "msg": "ensure this value is greater than or equal to 0.0",
      "type": "value_error.number.not_ge"
    }
  ]
}
```

### 500 Internal Server Error
Unexpected server error.

```json
{
  "error": "Internal Server Error",
  "message": "An unexpected error occurred"
}
```

---

## Pagination

All list endpoints support pagination:

**Request:**
```
GET /api/events/?limit=10&offset=0
```

**Response:**
```json
[
  ... 10 items ...
]
```

To get the next page:
```
GET /api/events/?limit=10&offset=10
```

**Response:**
```json
[
  ... next 10 items ...
]
```

---

## Rate Limiting

Currently not implemented (planned for Phase 2).

---

## CORS

Enabled for frontend development origins:
- `http://localhost:3000`
- `http://localhost:5173`

---

## OpenAPI Documentation

Interactive API documentation available at:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## Examples

### Complete Workflow: Event → Memory → Retrieval

```bash
# 1. Create a user input event
curl -X POST http://localhost:8000/api/events/ \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "user_input",
    "actor": "user_123",
    "scope": "session_ai",
    "payload": {"message": "What is machine learning?"}
  }'

# 2. Create semantic memory from the event
curl -X POST http://localhost:8000/api/memory/ \
  -H "Content-Type: application/json" \
  -d '{
    "memory_type": "semantic",
    "title": "Machine Learning Definition",
    "content": "Machine learning is a subset of AI that enables systems to learn from data.",
    "confidence": 0.95,
    "scope": "session_ai",
    "source_events": ["event-id-from-step-1"]
  }'

# 3. Search for memories
curl -X GET "http://localhost:8000/api/memory/search?query=machine+learning"

# 4. Get statistics
curl -X GET "http://localhost:8000/api/memory/statistics?scope=session_ai"
```

---

## Testing

Run the test suite:

```bash
make test
```

Or with pytest directly:

```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## Development

Start development server:

```bash
make dev
```

The API will be available at `http://localhost:8000`

---

*Documentation Version: 0.0.1*
*Last Updated: 2025-06-20*