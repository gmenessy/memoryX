# BrainDump NextGen - Demo Collection

This directory contains practical demonstrations of BrainDump NextGen's capabilities in real-world scenarios.

## Available Demos

### 🌟 One More Thing: "Darwin" - Self-Improving AI System

**File:** `ONE_MORE_THING.md` (Proposal)

**Purpose:** The ultimate demo - an AI system that evolves its own cognitive architecture through experience.

**"One More Thing" Factor:** Instead of just using BrainDump NextGen, the system actively modifies itself:
- Learns how it learns best (meta-learning)
- Restructures its own memory organization
- Evolves planning strategies based on success rates
- Recursively improves itself

**Impact:** A system that improves to the point where it can design better improvements

**See:** `demos/ONE_MORE_THING.md` for full proposal

---

### 1. Autonomous Code Review System 🔍

**File:** `code_review_demo.py`

**Purpose:** Demonstrates an intelligent code review system that learns from past reviews and evolves its criteria.

**Features Showcased:**
- Event ingestion from code activities (commits, PRs, builds)
- Pattern extraction and memory storage
- Knowledge graph construction for code relationships
- Evolution of review criteria based on experience
- Adaptive review planning with task decomposition
- Governance rules for code quality enforcement

**Running the Demo:**
```bash
# Activate virtual environment first
source venv/bin/activate

# Run the demo
python demos/code_review_demo.py
```

**What You'll See:**
1. Code events being ingested (commits, PRs, reviews, failures)
2. Patterns extracted and stored as memories
3. Knowledge graph showing relationships between concepts
4. Evolution of review criteria based on learnings
5. Automated review planning and execution
6. Governance rules evaluating code quality

### 2. Knowledge Worker Assistant (Coming Soon) 📚

**Purpose:** AI assistant for researchers that builds knowledge graphs and consolidates information.

### 3. Multi-Agent Research Swarm (Coming Soon) 🐝

**Purpose:** Multiple agents collaborating on complex research tasks with shared memory.

## Demo Architecture

Each demo follows this pattern:

```
1. Setup Phase
   └─ Initialize services and database

2. Data Ingestion Phase
   └─ Create events representing real-world activities

3. Pattern Extraction Phase
   └─ Transform events into structured memories

4. Knowledge Building Phase
   └─ Construct graphs showing relationships

5. Evolution Phase
   └─ Improve quality criteria based on experience

6. Action Phase
   └─ Execute plans using evolved knowledge

7. Governance Phase
   └─ Apply rules and validate outcomes
```

## Customizing Demos

To create your own demo:

1. Copy an existing demo as template
2. Modify the event types and data for your domain
3. Define relevant memory types and patterns
4. Set up appropriate graph relationships
5. Configure governance rules
6. Test and iterate

## Integration

Demos use the full BrainDump NextGen stack:
- **Event System**: Append-only activity tracking
- **Memory Cards**: Typed information storage
- **Evolution Memory**: Learning and adaptation
- **Memory Graph**: Relationship management
- **Planning System**: Goal decomposition
- **Governance**: Rule enforcement
- **Gatekeeper**: Validation and risk assessment

## Feedback

For issues or suggestions about demos, please refer to the main project documentation.
