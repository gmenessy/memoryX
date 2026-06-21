# BrainDump NextGen

> An Agentic Memory Operating System for GenAI Applications

## Vision

BrainDump NextGen provides persistent memory, governance, learning capability, planning capability, auditability, and knowledge evolution for AI agents.

## Status

🚧 **Specification Phase** - This project is currently in architectural planning. Implementation is scheduled to begin with Sprint 1.

## Architecture Overview

```
┌──────────────────────────┐
│ Frontend                 │
│ Aktenschrank UI          │
└─────────────┬────────────┘
              │
              ▼
┌──────────────────────────┐
│ FastAPI Gateway          │
└─────────────┬────────────┘
              │
              ▼
┌──────────────────────────┐
│ Agent Runtime            │
└─────────────┬────────────┘
              │
    ┌─────────┼──────────┐
    ▼         ▼          ▼

Event     Memory      Planning
System    Kernel      Engine

    ▼         ▼          ▼

Evolution  fRAG     Gatekeeper

    ▼         ▼          ▼

Memory Graph   Evaluation

              ▼

             VFS
```

## Technology Stack

### Backend
- **Language**: Python 3.12
- **Framework**: FastAPI
- **Async**: asyncio
- **Validation**: Pydantic v2
- **DI**: FastAPI Depends

### Storage (Phase 1 → Phase 2)
- **Database**: SQLite → PostgreSQL
- **Vector Search**: FAISS → Qdrant
- **Graph**: NetworkX → Neo4j

### Frontend
- **Framework**: React + TypeScript + Vite
- **State**: Zustand
- **Visualization**: React Flow

## Core Components

- **VFS**: Virtual File System with namespaces for events, memory, wiki, skills, cases, policies, rules, graph, evaluation, archive
- **Event System**: Append-only truth layer
- **Memory Cards**: Typed information storage
- **Evolution Memory**: Memory evolution through patches
- **Memory Gatekeeper**: Critical validation component
- **Dream Engine**: Async consolidation (daydream, nightdream, deepdream)

## Sprint Plan

- **Sprint 1**: Event System, Memory Cards, Tests
- **Sprint 2**: Evolution Memory, Fitness Engine, Patch Resolver
- **Sprint 3**: Memory Gatekeeper, Governance Rules
- **Sprint 4**: Memory Graph, Graph Traversal
- **Sprint 5**: fRAG, Retrieval Optimizer
- **Sprint 6**: Evaluation Layer, Benchmark Suite

## Documentation

- [Technical Specification](spec.md) - Comprehensive technical architecture and implementation details
- [Project Guidelines](CLAUDE.md) - Behavioral guidelines for development
- [Examples](EXAMPLES.md) - Best practices and anti-patterns

## License

TBD