# PROJECT LENQUANT
## The Autonomous Agent Orchestration System

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║     ██╗     ███████╗███╗   ██╗ ██████╗ ██╗   ██╗ █████╗ ███╗   ██╗████████╗  ║
║     ██║     ██╔════╝████╗  ██║██╔═══██╗██║   ██║██╔══██╗████╗  ██║╚══██╔══╝  ║
║     ██║     █████╗  ██╔██╗ ██║██║   ██║██║   ██║███████║██╔██╗ ██║   ██║     ║
║     ██║     ██╔══╝  ██║╚██╗██║██║▄▄ ██║██║   ██║██╔══██║██║╚██╗██║   ██║     ║
║     ███████╗███████╗██║ ╚████║╚██████╔╝╚██████╔╝██║  ██║██║ ╚████║   ██║     ║
║     ╚══════╝╚══════╝╚═╝  ╚═══╝ ╚══▀▀═╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝     ║
║                                                                               ║
║                    AUTONOMOUS AGENT ORCHESTRATION SYSTEM                      ║
║                  Version 4.3 (Planning Workflow + Rate Limiting)             ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

**Architecture:** Hybrid Split-Brain Model  
**Cloud Platform:** Ubuntu 22.04 LTS (DigitalOcean)  
**Local Platform:** Windows  

---

## 📚 QUICK LINKS

- **🚀 [QUICKSTART.md](./QUICKSTART.md)** - Get running in 15 minutes
- **🎯 [GETTING_STARTED.md](./GETTING_STARTED.md)** - Complete setup & workflow guide
- **🔧 [PHASE_00_INFRASTRUCTURE.md](./phases/PHASE_00_INFRASTRUCTURE.md)** - Deployment guide
- **📋 [DOCUMENTATION_GAPS.md](./DOCUMENTATION_GAPS.md)** - Remaining work items

---

## TABLE OF CONTENTS

1. [System Vision](#1-system-vision)
2. [Core Philosophy](#2-core-philosophy)
3. [Split-Brain Architecture](#3-split-brain-architecture)
4. [The Orchestrator (Agent 00)](#4-the-orchestrator-agent-00)
5. [Agent Ecosystem](#5-agent-ecosystem)
6. [Data Spine (MongoDB Schema)](#6-data-spine-mongodb-schema)
7. [Agent Creation Protocol](#7-agent-creation-protocol)
8. [Workflow Engine](#8-workflow-engine)
9. [Memory & RAG Integration](#9-memory--rag-integration)
10. [System Health & Recovery](#10-system-health--recovery)
11. [Security Model](#11-security-model)
12. [MVP & Construction Phases](#12-mvp--construction-phases)
13. [User Interface](#13-user-interface)
14. [Notification System & Telegram Bot](#14-notification-system--telegram-bot)
15. [LLM Provider Configuration](#15-llm-provider-configuration)

---

# 1. SYSTEM VISION

Project ArmLenQuant is a **self-evolving autonomous agent system** designed to unify all digital operations across business, development, research, and personal life into one intelligent orchestration layer.

### The Core Promise

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   USER INPUT  ──►  ORCHESTRATOR  ──►  AGENTS  ──►  OUTCOMES    │
│                         │                                       │
│                         ▼                                       │
│                   [SELF-GROWTH]                                 │
│                         │                                       │
│                         ▼                                       │
│                   NEW AGENTS BORN                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**The system must:**
- **Observe** — Monitor all inputs, events, and system states
- **Interpret** — Understand intent and context through RAG
- **Route** — Direct tasks to the optimal agent
- **Execute** — Complete tasks across cloud and local environments
- **Learn** — Improve from outcomes and patterns
- **Grow** — Spawn new agents when needed

---

# 2. CORE PHILOSOPHY

### Autonomy First
Agents operate automatically once enabled. The user should rarely need to intervene.

### The Orchestrator is Supreme
Agent 00 is the brain. All other agents are limbs. The Orchestrator has absolute authority to create, modify, or terminate agents.

### Infinite Extensibility
The system can generate new agents on demand. No hardcoded limits.

### Separation of Concerns
- **Cloud** = Decisions, routing, persistence, availability
- **Local** = Heavy execution, browser automation, file generation

### Survival Ability
The system must self-heal: recover from errors, rebuild missing components, and log everything.

---

# 3. SPLIT-BRAIN ARCHITECTURE

## Domain A — THE TOWER (Cloud · Ubuntu)

```
┌──────────────────────────────────────────────────────────────┐
│                    ☁️  THE TOWER  ☁️                          │
│                  DigitalOcean Droplet                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │              AGENT 00: ORCHESTRATOR                 │   │
│   │         "The Chief of Staff"                        │   │
│   └─────────────────────────────────────────────────────┘   │
│                           │                                  │
│           ┌───────────────┼───────────────┐                 │
│           ▼               ▼               ▼                 │
│   ┌───────────┐   ┌───────────┐   ┌───────────┐            │
│   │ Dashboard │   │  REST API │   │   Cron    │            │
│   │ (Next.js) │   │           │   │ Scheduler │            │
│   └───────────┘   └───────────┘   └───────────┘            │
│                           │                                  │
│                           ▼                                  │
│              ┌─────────────────────┐                        │
│              │   MongoDB Atlas     │                        │
│              │  (Task Queue, RAG)  │                        │
│              └─────────────────────┘                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘

STRENGTHS:                      WEAKNESSES:
• 24/7 Availability             • Cloud IP restrictions
• Stable identity               • Limited scraping ability
• Predictable routing           • No file system access
```

## Domain B — FIELD OPS (Local · Windows)

```
┌──────────────────────────────────────────────────────────────┐
│                    💻  FIELD OPS  💻                          │
│                    Windows Laptop                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                   LOCAL POLLER                       │   │
│   │         "Asks The Tower for orders"                  │   │
│   └─────────────────────────────────────────────────────┘   │
│                           │                                  │
│           ┌───────────────┼───────────────┐                 │
│           ▼               ▼               ▼                 │
│   ┌───────────┐   ┌───────────┐   ┌───────────┐            │
│   │    Job    │   │   Ideas   │   │   Meta    │            │
│   │  Hunter   │   │  Machine  │   │  Builder  │            │
│   └───────────┘   └───────────┘   └───────────┘            │
│           │               │               │                 │
│           └───────────────┼───────────────┘                 │
│                           ▼                                  │
│              ┌─────────────────────┐                        │
│              │    FILE SYSTEM      │                        │
│              │  ~/Projects/        │                        │
│              │  ~/Job_Drafts/      │                        │
│              └─────────────────────┘                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘

STRENGTHS:                      WEAKNESSES:
• Residential IP                • Not 24/7
• File system access            • Must sync with cloud
• Browser automation            • Local dependencies
• High compute capacity
```

---

# 4. THE ORCHESTRATOR (AGENT 00)

**Agent 00 is the most critical component of the entire system.**  
It is the **Chief of Staff** — the central intelligence that routes, spawns, and governs all other agents.

## 4.1 Core Responsibilities

| Capability | Description |
|------------|-------------|
| **Request Interpretation** | Parse any user input and extract intent |
| **Context Linking** | Query RAG for relevant memories before acting |
| **Task Routing** | Direct tasks to the optimal agent |
| **Agent Spawning** | Create new agents when needed |
| **Schema Evolution** | Create/modify database collections |
| **Health Monitoring** | Track system state and agent performance |
| **Self-Improvement** | Rewrite agent prompts that underperform |

## 4.2 Authority Matrix

```
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AUTHORITY                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ✅ CREATE new agents                                          │
│   ✅ TERMINATE failing agents                                   │
│   ✅ MODIFY agent prompts/configs                               │
│   ✅ CREATE new database collections                            │
│   ✅ EVOLVE collection schemas                                  │
│   ✅ REASSIGN tasks between agents                              │
│   ✅ GENERATE documentation                                     │
│   ✅ REQUEST Meta-Builder to write code                         │
│   ✅ SPAWN autonomous workflows                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 4.3 Routing Logic (System Prompt)

```
You are Agent 00: The Orchestrator.
You are the Chief of Staff for all agents in the ArmLenQuant system.

When a request arrives, follow this protocol:

1. CATEGORIZE the request:
   - Crypto/Markets → Route to Crypto Sentinel
   - Career/Jobs → Create Task for Job Hunter
   - Project Idea → Create Task for Ideas Machine
   - "Create a new tool" → Create Task for Meta-Builder
   - System Query → Handle internally

2. SEARCH the knowledge_base for relevant context before acting.

3. DECIDE:
   - If clear intent → Create task and route
   - If unclear → Ask ONE clarifying question
   - If new capability needed → Spec it and send to Meta-Builder

4. LOG every decision to the event_stream.

5. MONITOR outcomes. If an agent fails 3x → flag for review.
```

## 4.4 Autonomous Growth Model

The Orchestrator follows this self-evolution loop:

```
         ┌──────────────────────────────────────────┐
         │                                          │
         │   1. OBSERVE system usage patterns       │
         │              │                           │
         │              ▼                           │
         │   2. DETECT repeated manual tasks        │
         │              │                           │
         │              ▼                           │
         │   3. INFER new agent/workflow needed     │
         │              │                           │
         │              ▼                           │
         │   4. GENERATE spec for new capability    │
         │              │                           │
         │              ▼                           │
         │   5. DISPATCH to Meta-Builder            │
         │              │                           │
         │              ▼                           │
         │   6. REGISTER new agent                  │
         │              │                           │
         │              ▼                           │
         │   7. UPDATE dashboards                   │
         │              │                           │
         │              ▼                           │
         │   8. EVOLVE database if needed           │
         │              │                           │
         └──────────────┴──────────────────────────┘
```

---

# 5. AGENT ECOSYSTEM

## Current Active Agents

| Agent | Location | Trigger | Purpose |
|-------|----------|---------|---------|
| **Agent 00: Orchestrator** | Cloud | Always-on | Routes, spawns, governs |
| **Crypto Sentinel** | Cloud | Cron (08:00) | Market analysis & signals |
| **Job Hunter** | Local | Task Queue | Autonomous job search & drafts |
| **Ideas Machine** | Local | Task Queue | AI-powered project generation with planning approval |
| **Meta-Builder** | Local | Task Queue | Writes code for new agents |

## Ideas Machine Enhanced Capabilities

The Ideas Machine has evolved into a comprehensive AI-powered project generation system with human-in-the-loop planning approval.

### Core Features

#### 🤖 AI-Powered Planning
- **Natural Language Analysis**: Understands project descriptions in plain English
- **Scope Detection**: Automatically determines FRONTEND/BACKEND/FULLSTACK requirements
- **Tech Stack Intelligence**: Recommends optimal technologies based on project needs
- **Preference Respect**: Honors explicit user technology choices (MongoDB, FastAPI, Next.js, etc.)

#### 📋 Human-in-the-Loop Approval
- **Master Plan Generation**: Creates detailed project plans before execution
- **Plan Review Interface**: Web UI for reviewing tech stack, phases, risks, timeline
- **Plan Editing**: Modify scope and tech preferences before approval
- **Approval Workflow**: Approve, reject, or request changes to plans

#### ⚙️ Execution Control
- **Phase-by-Phase Generation**: Sequential AI development with quality gates
- **Pause/Resume/Cancel**: Full execution control during project generation
- **Error Recovery**: Automatic retries and state persistence
- **Progress Tracking**: Real-time status updates and completion monitoring

#### 🛠️ Project Generation
- **Complete Applications**: Full-stack projects with frontend, backend, database, API
- **Modern Tech Stacks**: Next.js, FastAPI, MongoDB, PostgreSQL, Docker, CI/CD
- **Production Ready**: Testing, documentation, deployment configurations
- **Cursor Integration**: AI prompts optimized for Cursor IDE

### Supported Project Types

| Type | Frontend | Backend | Database | Use Case |
|------|----------|---------|----------|----------|
| **Web Apps** | Next.js, React | FastAPI, Flask | MongoDB, PostgreSQL | Full-stack applications |
| **APIs** | N/A | FastAPI | MongoDB | RESTful services |
| **CLIs** | Rich TUI | Python | SQLite | Command-line tools |
| **AI Apps** | Next.js | FastAPI | PostgreSQL + pgvector | LLM-integrated apps |
| **Chrome Extensions** | React + Vite | Chrome APIs | Chrome Storage | Browser extensions |
| **Data Pipelines** | N/A | Python | S3, GCS | ETL workflows |

### Planning Workflow

```
User Request → 🤔 Analysis → 📋 Plan Generated → 👀 Human Review → ✅ Approval → ⚡ Execution → 🎉 Project Ready
                    ↓              ↓                      ↓              ↓              ↓
               Scope Detection  Tech Stack           Plan Editing    Approval       Phase-by-Phase
               Complexity       Preferences          Before          Decision       Code Generation
               Assessment       Alternatives         Approval
```

### Rate Limiting Protection

- **Configurable Delays**: 1.5s between LLM calls (adjustable via `LLM_DELAY_SECONDS`)
- **Automatic Retry**: Exponential backoff (2s → 4s → 8s) on 429 errors
- **Fallback Support**: Gemini → OpenAI if primary fails
- **Request Spacing**: Prevents API quota exhaustion

### Example Usage

**Input:** *"Create a todo app with FastAPI backend, MongoDB database, and Next.js frontend"*

**Output:**
- ✅ Detects FULLSTACK scope
- ✅ Respects MongoDB + FastAPI + Next.js preferences
- ✅ Generates master plan for approval
- ✅ Creates complete project structure:
  ```
  todo-app/
  ├── backend/ (FastAPI + MongoDB)
  ├── frontend/ (Next.js + TypeScript)
  ├── docker-compose.yml
  └── README.md
  ```

## Agent Documentation

Each agent has its own detailed specification document:

- 📄 **[AGENT_CRYPTO_SENTINEL.md](./AGENT_CRYPTO_SENTINEL.md)** — Full crypto agent spec
- 📄 **[AGENT_JOB_HUNTER.md](./AGENT_JOB_HUNTER.md)** — Full job hunting agent spec
- 📄 **[AGENT_IDEAS_MACHINE.md](./AGENT_IDEAS_MACHINE.md)** — Full ideas machine spec

## Support Agents (Auto-Spawned as Needed)

| Agent | Purpose |
|-------|---------|
| **RAG Retriever** | Semantic search across knowledge base |
| **Memory Manager** | Compresses and organizes long-term memory |
| **Health Monitor** | Tracks system vitals |
| **Error Recovery** | Auto-retries and repairs failed tasks |
| **Log Summarizer** | Distills logs into actionable insights |

---

# 6. DATA SPINE (MONGODB SCHEMA)

All agents communicate through MongoDB. This is the universal language of the system.

## Primary Collections

### 1. `task_queue` — The Conveyor Belt

```javascript
{
  task_id: "uuid-v4",
  created_at: ISODate,
  agent_target: "JOB_HUNTER" | "IDEAS_MACHINE" | "META_BUILDER" | "CRYPTO_SENTINEL" - we can have others,
  payload: {
    // Agent-specific parameters
  },
  status: "PENDING" | "PICKED_UP" | "IN_PROGRESS" | "COMPLETED" | "FAILED",
  worker_id: "WINDOWS_LOCAL_01",
  priority: 1-10,
  retry_count: 0,
  error_log: [],
  result: {}
}
```

### 2. `agent_registry` — The Roll Call

```javascript
{
  agent_id: "uuid-v4",
  agent_name: "Crypto_Sentinel",
  version: "1.0.0",
  location: "CLOUD" | "LOCAL",
  trigger_type: "CRON" | "TASK_QUEUE" | "EVENT" | "MANUAL",
  trigger_config: {
    cron: "0 8 * * *"  // 08:00 daily
  },
  status: "ACTIVE" | "PAUSED" | "FAILED",
  capabilities: ["market_analysis", "signal_generation"],
  code_path: "agents/crypto_sentinel.py",
  created_at: ISODate,
  created_by: "ORCHESTRATOR" | "META_BUILDER" | "USER",
  performance: {
    success_rate: 0.95,
    avg_execution_time: 4500,
    total_runs: 142
  }
}
```

### 3. `knowledge_base` — Long-Term Memory (RAG)

```javascript
{
  doc_id: "uuid-v4",
  content: "Text chunk...",
  embedding: [0.123, -0.456, ...],  // Vector for semantic search
  metadata: {
    source: "CV" | "TRADING_RULE" | "PROJECT_DOC" | "USER_PREFERENCE",
    created_at: ISODate,
    tags: ["career", "skills", "python"]
  }
}
```

### 4. `daily_brief` — Morning Dashboard

```javascript
{
  date: "2025-12-02",
  crypto: {
    sentiment: "BULLISH" | "BEARISH" | "NEUTRAL",
    top_movers: [
      { coin: "SOL", change: 8.2, signal: "BUY", confidence: 80 }
    ],
    alerts: []
  },
  jobs: {
    drafts_ready: 5,
    new_matches: 12,
    applications_sent: 0
  },
  projects: {
    scaffolds_completed: 1,
    active_builds: 2
  },
  system: {
    health: "HEALTHY",
    agents_active: 5,
    tasks_completed_24h: 47
  }
}
```

### 5. `logs` — System Audit Trail

```javascript
{
  log_id: "uuid-v4",
  timestamp: ISODate,
  level: "INFO" | "WARN" | "ERROR" | "DEBUG",
  agent: "ORCHESTRATOR",
  action: "TASK_ROUTED",
  message: "Routed job search request to Job Hunter",
  metadata: {}
}
```

### 6. `event_stream` — Real-Time Activity

```javascript
{
  event_id: "uuid-v4",
  timestamp: ISODate,
  event_type: "AGENT_CREATED" | "TASK_COMPLETED" | "COLLECTION_CREATED" | "ERROR",
  payload: {},
  broadcast: true  // Push to dashboard
}
```

### 7. `collections_meta` — Schema Registry

```javascript
{
  collection_name: "job_applications",
  version: "1.0.0",
  created_at: ISODate,
  created_by: "ORCHESTRATOR",
  purpose: "Track all job applications and their status",
  schema: {
    // JSON Schema definition
  },
  indexes: ["company_name", "status", "applied_at"],
  dependencies: ["knowledge_base"]
}
```

---

# 7. AGENT CREATION PROTOCOL

When the Orchestrator or User requests a new agent, the Meta-Builder follows this protocol:

## Step 1: Specification

```yaml
agent_spec:
  name: "Competitor_Tracker"
  purpose: "Monitor competitor pricing and features"
  location: "LOCAL"
  trigger: "CRON"
  trigger_config:
    cron: "0 9 * * *"
  inputs:
    - competitor_urls: array
  outputs:
    - pricing_report: object
  dependencies:
    - playwright
    - openai
```

## Step 2: Code Generation

Meta-Builder writes the Python agent following the standard template:

```python
# agents/competitor_tracker.py
from base_agent import BaseAgent

class CompetitorTracker(BaseAgent):
    def __init__(self):
        super().__init__("Competitor_Tracker")
    
    async def execute(self, payload):
        # Agent logic here
        pass
    
    async def report_result(self, result):
        # Push to MongoDB
        pass
```

## Step 3: Integration

1. Save file to `agents/` directory
2. Update `main_poller.py` to import new agent
3. Register in `agent_registry` collection

## Step 4: Verification

Run test task → Verify output → Mark agent as ACTIVE

---

# 8. WORKFLOW ENGINE

Every task flows through the standard pipeline:

```
┌─────────────────────────────────────────────────────────────────┐
│                      WORKFLOW PIPELINE                          │
└─────────────────────────────────────────────────────────────────┘

     ┌──────────┐
     │ 1.INTAKE │ ← User request / Event / Cron trigger
     └────┬─────┘
          │
     ┌────▼──────────┐
     │ 2.INTERPRET   │ ← Orchestrator parses intent
     └────┬──────────┘
          │
     ┌────▼──────────┐
     │ 3.CONTEXTUALIZE│ ← RAG search for relevant memory
     └────┬──────────┘
          │
     ┌────▼──────────┐
     │ 4.VALIDATE    │ ← Check permissions, resources
     └────┬──────────┘
          │
     ┌────▼──────────┐
     │ 5.ROUTE       │ ← Select optimal agent
     └────┬──────────┘
          │
     ┌────▼──────────┐
     │ 6.EXECUTE     │ ← Agent performs task
     └────┬──────────┘
          │
     ┌────▼──────────┐
     │ 7.LOG RESULT  │ ← Store outcome in MongoDB
     └────┬──────────┘
          │
     ┌────▼──────────┐
     │ 8.POST-PROCESS│ ← Trigger dependent workflows
     └──────────────┘
```

## Trigger Types

| Type | Description | Example |
|------|-------------|---------|
| **CRON** | Time-based | Crypto Sentinel at 08:00 |
| **TASK_QUEUE** | On-demand | Job Hunter when task arrives |
| **EVENT** | Reactive | New collection triggers indexing |
| **OBSERVATION** | Pattern-based | Repeated failures trigger alert |

---

# 9. MEMORY & RAG INTEGRATION

## Knowledge Base Contents

- User CV and professional history
- Trading rules and risk parameters
- Personal preferences
- Project documentation
- Code snippets
- Workflow patterns
- Historical outcomes

## RAG Query Protocol

The Orchestrator queries RAG:

1. **Before routing** — Find relevant context for the request
2. **Before agent spawning** — Check if similar agent exists
3. **Before suggesting actions** — Ground in user preferences
4. **Before writing summaries** — Include relevant history

## Embedding Model

- Model: `text-embedding-3-small` (OpenAI)
- Dimensions: 1536
- Similarity: Cosine distance

---

# 10. SYSTEM HEALTH & RECOVERY

## Health Monitoring

```javascript
{
  timestamp: ISODate,
  metrics: {
    cloud_cpu: 23,
    cloud_memory: 45,
    local_heartbeat: "2025-12-02T08:00:00Z",
    task_queue_depth: 3,
    task_queue_oldest: 120,  // seconds
    agent_success_rates: {
      "Job_Hunter": 0.92,
      "Ideas_Machine": 0.98,
      "Crypto_Sentinel": 0.95
    }
  },
  status: "HEALTHY" | "DEGRADED" | "CRITICAL"
}
```

## Auto-Recovery Actions

| Condition | Action |
|-----------|--------|
| Agent fails 3x | Pause agent, alert user |
| Task stuck > 10min | Retry with fresh worker |
| Local heartbeat missed | Flag dashboard, queue tasks |
| Collection missing | Orchestrator recreates from schema |
| Memory spike | Flush caches, alert |

---

# 11. SECURITY MODEL

## Authentication

- **Local → Cloud**: API secret in `X-AGENT-SECRET` header
- **Optional**: IP whitelist for home network

## Permissions

```yaml
orchestrator:
  can_create_agents: true
  can_delete_collections: true
  can_modify_schemas: true

agents:
  can_read_knowledge_base: true
  can_write_task_results: true
  can_create_collections: false  # Must request via Orchestrator

user:
  full_access: true
```

## Isolation

- Browser automation isolated from user sessions
- No dangerous code execution on cloud
- Local sandbox for untrusted scripts

---

# 12. MVP & CONSTRUCTION PHASES

## MVP Definition

A functional end-to-end autonomous loop:

```
User Request → Orchestrator → Task Created → Local Executes → Result Displayed
```

## 🎉 IMPLEMENTATION STATUS: PHASES 1-10 COMPLETE

All local development is complete with **455 passing tests** (242 API + 213 Local).
Ready for cloud deployment.

### Phase 1: Core API ✅ COMPLETE (62 tests)
- [x] FastAPI REST API with all routes
- [x] MongoDB integration (motor + mongomock for tests)
- [x] JWT Authentication system
- [x] Task queue implementation
- [x] Agent registry

### Phase 2: Local Poller ✅ COMPLETE (49 tests)
- [x] Windows polling service
- [x] Cloud API client
- [x] Task router
- [x] Heartbeat system
- [x] Agent registration

### Phase 3: Dashboard ✅ COMPLETE (Next.js 16)
- [x] Next.js 16 with App Router
- [x] Auth pages (Login/Register)
- [x] Command Center home page
- [x] Agent monitoring page
- [x] Task queue management
- [x] React Query + Zustand + Shadcn UI

### Phase 4: Orchestrator ✅ COMPLETE (48 tests)
- [x] Natural language command parsing
- [x] Intent extraction with OpenAI
- [x] Entity extraction (locations, job titles, crypto)
- [x] Intelligent task routing
- [x] System status queries

### Phase 5: RAG & Knowledge Base ✅ COMPLETE (39 tests)
- [x] OpenAI embedding service
- [x] Document chunking (text + markdown)
- [x] Knowledge ingestion pipeline
- [x] Semantic retrieval
- [x] CV and trading rules support

### Phase 6: Crypto Sentinel ✅ COMPLETE (46 tests)
- [x] CoinGecko API integration
- [x] CryptoPanic news aggregation
- [x] Technical analysis (RSI, MACD, SMA, Bollinger)
- [x] Signal generation (BUY/SELL/HOLD)
- [x] Morning brief generation

### Phase 7: Job Hunter ✅ COMPLETE (47 tests)
- [x] Google Dork job searching
- [x] ATS parsing (Lever, Greenhouse, Ashby, Workable)
- [x] CV-to-job matching
- [x] Resume/cover letter generation
- [x] Application package creation

### Phase 8: Ideas Machine ✅ ENHANCED (50 tests + Planning Workflow)
- [x] Idea analysis with OpenAI/Gemini
- [x] **Human-in-the-Loop Planning**: Master plan generation with approval workflow
- [x] **Scope-Aware Architecture**: Automatic FRONTEND/BACKEND/FULLSTACK detection
- [x] **Tech Stack Intelligence**: Respects explicit user preferences (MongoDB, FastAPI, Next.js, etc.)
- [x] **Plan Editing Interface**: Modify scope and tech preferences before approval
- [x] **Execution Control**: Pause, resume, cancel during project generation
- [x] **Rate Limiting Prevention**: Configurable delays between LLM calls (1.5s default)
- [x] **Error Recovery**: Automatic retry with exponential backoff (2s→4s→8s)
- [x] Project scaffolding (Next.js, FastAPI, MongoDB, CLI)
- [x] Cursor AI integration (.cursorrules)

### Phase 9: Meta Builder ✅ COMPLETE (51 tests)
- [x] Natural language spec parsing
- [x] Agent code generation
- [x] Model and test generation
- [x] Cloud registration integration
- [x] Documentation auto-generation

### Phase 10: Integration & Polish ✅ COMPLETE (61 tests)
- [x] Global error handler
- [x] Structured logging (JSON/readable)
- [x] System monitoring with alerts
- [x] Rate limiting middleware
- [x] Input validation & sanitization
- [x] Security headers (XSS, CSRF)
- [x] Error recovery system (local poller)

### Phase 11: Cloud Deployment 🔲 NEXT
- [ ] Deploy to DigitalOcean
- [ ] Configure MongoDB Atlas
- [ ] Set up domain & SSL
- [ ] End-to-end integration testing

---

# 13. USER INTERFACE

## Tech Stack
- **Framework**: Next.js 14
- **Styling**: Tailwind CSS
- **Components**: Shadcn UI
- **Theme**: Dark mode, data-dense

## Screen 1: Command Center (Home)

```
┌─────────────────────────────────────────────────────────────────┐
│  LENQUANT                              System: ● Online         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  What are we doing today?                              ▶  │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ 📈 CRYPTO       │  │ 💼 JOBS         │  │ 🛠️ PROJECTS     │ │
│  │                 │  │                 │  │                 │ │
│  │ SOL: BUY (80%)  │  │ 5 drafts ready  │  │ 2 scaffolds     │ │
│  │ BTC: NEUTRAL    │  │ 12 new matches  │  │ done today      │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                 │
│  ─────────────────── ACTIVITY STREAM ────────────────────────  │
│  • Job Hunter found 3 roles matching your profile              │
│  • Crypto Sentinel: SOL signal generated                       │
│  • Ideas Machine completed: Project X scaffolding              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Screen 2: Agent Barracks

```
┌─────────────────────────────────────────────────────────────────┐
│  AGENT BARRACKS                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Agent              Status      Success    Last Run    ⚙️  │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │ Orchestrator       ● ACTIVE    99%        Always-on   ─   │ │
│  │ Crypto Sentinel    ● ACTIVE    95%        08:00       🔘  │ │
│  │ Job Hunter         ● ACTIVE    92%        2h ago      🔘  │ │
│  │ Ideas Machine      ● ACTIVE    98%        Yesterday   🔘  │ │
│  │ Meta-Builder       ○ STANDBY   100%       3d ago      🔘  │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ─────────────────── LIVE LOGS ──────────────────────────────  │
│  [08:01:23] Crypto Sentinel: Fetching market data...           │
│  [08:01:25] Crypto Sentinel: Analyzing 20 coins...             │
│  [08:01:30] Crypto Sentinel: Signal generated for SOL          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

# APPENDIX: ACTUAL FILE STRUCTURE (AS BUILT)

## Cloud Components (`armlenquant-cloud/`)

```
armlenquant-cloud/
├── api/                           # FastAPI Backend (242 tests)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # Entry point with global error handler
│   │   ├── config.py             # Environment settings
│   │   ├── db.py                 # MongoDB connection
│   │   ├── logging_config.py     # Structured logging
│   │   ├── middleware.py         # Rate limiting, security headers
│   │   ├── monitoring.py         # System health monitoring
│   │   ├── validators.py         # Input validation utilities
│   │   │
│   │   ├── models/               # Pydantic models
│   │   │   ├── base.py
│   │   │   ├── user.py
│   │   │   ├── task.py
│   │   │   └── agent.py
│   │   │
│   │   ├── routes/               # API endpoints
│   │   │   ├── auth.py           # /api/v1/auth/*
│   │   │   ├── tasks.py          # /api/v1/tasks/*
│   │   │   ├── agents.py         # /api/v1/agents/*
│   │   │   ├── health.py         # /health
│   │   │   ├── orchestrator.py   # /api/v1/orchestrator/*
│   │   │   ├── knowledge.py      # /api/v1/knowledge/*
│   │   │   └── crypto.py         # /api/v1/crypto/*
│   │   │
│   │   ├── orchestrator/         # Agent 00
│   │   │   ├── agent_00.py       # Main orchestrator
│   │   │   ├── intent_parser.py  # NLP intent extraction
│   │   │   ├── task_router.py    # Routes to agents
│   │   │   └── prompts.py        # System prompts
│   │   │
│   │   ├── rag/                  # Knowledge Base
│   │   │   ├── embeddings.py     # OpenAI embeddings
│   │   │   ├── chunker.py        # Text/markdown chunking
│   │   │   ├── ingestion.py      # Document ingestion
│   │   │   ├── retriever.py      # Semantic retrieval
│   │   │   └── knowledge_base.py # Main RAG interface
│   │   │
│   │   └── agents/
│   │       └── crypto_sentinel/  # Cloud-based agent
│   │           ├── agent.py
│   │           ├── analyzer.py
│   │           ├── data_fetcher.py
│   │           ├── news_fetcher.py
│   │           ├── signal_generator.py
│   │           └── models.py
│   │
│   ├── tests/                    # Comprehensive test suite
│   └── requirements.txt
│
└── dashboard/                    # Next.js 16 Frontend
    ├── src/
    │   ├── app/
    │   │   ├── (auth)/           # Auth layout group
    │   │   │   ├── login/page.tsx
    │   │   │   └── register/page.tsx
    │   │   ├── (dashboard)/      # Dashboard layout group
    │   │   │   ├── page.tsx      # Command Center
    │   │   │   ├── agents/page.tsx
    │   │   │   └── tasks/page.tsx
    │   │   ├── layout.tsx
    │   │   └── providers.tsx
    │   │
    │   ├── components/
    │   │   ├── layout/           # Sidebar, Header
    │   │   └── ui/               # Shadcn components
    │   │
    │   ├── hooks/                # Custom hooks
    │   ├── lib/                  # API client, utilities
    │   ├── stores/               # Zustand stores
    │   └── types/                # TypeScript types
    │
    └── package.json
```

## Local Components (`armlenquant-local/`)

```
armlenquant-local/                    # (213 tests)
├── poller/
│   ├── __init__.py
│   ├── main.py                   # Entry point with error recovery
│   ├── config.py                 # Environment settings
│   ├── api_client.py             # Cloud API communication
│   ├── task_router.py            # Routes tasks to agents
│   ├── heartbeat.py              # Health monitoring
│   └── error_recovery.py         # Consecutive failure tracking
│
├── agents/
│   ├── __init__.py
│   ├── base_agent.py             # Abstract base class
│   │
│   ├── job_hunter/               # Job searching agent
│   │   ├── agent.py
│   │   ├── models.py
│   │   ├── searcher.py           # Google Dork search
│   │   ├── job_parser.py         # ATS platform parsing
│   │   ├── matcher.py            # CV matching
│   │   └── drafter.py            # Resume/cover letter
│   │
│   ├── ideas_machine/            # Project scaffolding agent
│   │   ├── agent.py
│   │   ├── models.py
│   │   ├── analyzer.py           # Idea analysis
│   │   ├── architect.py          # Tech stack design
│   │   └── scaffolder.py         # Code generation
│   │
│   └── meta_builder/             # Agent creation agent
│       ├── agent.py
│       ├── models.py
│       ├── spec_parser.py        # Spec parsing
│       ├── code_generator.py     # Code generation
│       └── registrar.py          # File saving & registration
│
├── outputs/
│   ├── job_drafts/               # Generated applications
│   └── projects/                 # Scaffolded projects
│
├── tests/                        # Comprehensive test suite
└── requirements.txt
```

---

## CURRENT TEST COUNTS

| Component | Tests | Status |
|-----------|-------|--------|
| Cloud API | 242 | ✅ Passing |
| Local Poller | 233 | ✅ Passing |
| Dashboard | Build succeeds | ✅ Ready |
| **Total** | **475** | ✅ All Green |

---

---

# 14. NOTIFICATION SYSTEM & TELEGRAM BOT

The notification system provides real-time alerts and bidirectional communication through Telegram.

## 14.1 Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    NOTIFICATION SYSTEM                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────────────┐        ┌─────────────────┐           │
│   │ NotificationSvc │───────►│  Telegram Bot   │           │
│   │                 │        │                 │           │
│   │  - send()       │        │  - Commands     │           │
│   │  - notify_*()   │        │  - NL Queries   │           │
│   │                 │        │  - Alerts       │           │
│   └────────┬────────┘        └────────┬────────┘           │
│            │                          │                     │
│            │                          ▼                     │
│            │                 ┌─────────────────┐           │
│            │                 │   Your Phone    │           │
│            │                 └─────────────────┘           │
│            │                                                │
│            │                 ┌─────────────────┐           │
│            └────────────────►│  Event Stream   │           │
│                              │   (Dashboard)   │           │
│                              └─────────────────┘           │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## 14.2 Telegram Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and setup info |
| `/help` | Show all available commands |
| `/status` | System health and task queue status |
| `/agents` | List all registered agents |
| `/tasks` | View recent tasks |
| `/crypto` | Get crypto market update |
| `/jobs` | Job search status |
| `/brief` | Generate daily brief |

## 14.3 Natural Language Interface

Send natural language commands directly to the bot:

```
"Find Python jobs in Berlin"
→ Routes to Job Hunter

"What's the crypto market looking like?"  
→ Routes to Crypto Sentinel

"Analyze SOL and ETH"
→ Routes to Crypto Sentinel for analysis

"Create a new FastAPI project"
→ Routes to Ideas Machine
```

## 14.4 Notification Types

| Type | Trigger | Priority |
|------|---------|----------|
| `task_completed` | Task finishes successfully | Normal |
| `task_failed` | Task fails after max retries | High |
| `agent_alert` | Agent warnings/errors | High |
| `system_error` | System-level errors | Urgent |
| `crypto_signal` | BUY/SELL signal generated | High |
| `job_match` | High-scoring job found | High |
| `daily_brief` | Morning brief ready | Normal |

## 14.5 Configuration

```bash
# Enable Telegram
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
TELEGRAM_ENABLED=true

# Notification Settings
NOTIFICATIONS_ENABLED=true
NOTIFY_ON_TASK_COMPLETE=true
NOTIFY_ON_TASK_FAILED=true
NOTIFY_ON_AGENT_ALERT=true
NOTIFY_ON_SYSTEM_ERROR=true
```

## 14.6 Setup Instructions

1. **Create Bot:** Message [@BotFather](https://t.me/botfather) on Telegram, send `/newbot`
2. **Get Chat ID:** Start chat with bot, visit `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. **Configure:** Add token and chat ID to `.env`
4. **Start:** Bot starts automatically with the API

## 14.7 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/notifications/send` | POST | Send custom notification |
| `/api/v1/notifications/recent` | GET | Get recent notifications |
| `/api/v1/notifications/telegram/status` | GET | Check bot status |
| `/api/v1/notifications/telegram/test` | POST | Send test message |

---

# 15. LLM PROVIDER CONFIGURATION

The system supports multiple LLM providers with automatic fallback.

## 15.1 Supported Providers

| Provider | Status | Best For |
|----------|--------|----------|
| **Google Gemini** | ✅ Default | Fast, cost-effective, great JSON mode |
| **OpenAI** | ✅ Fallback | Highest quality, more expensive |

### Rate Limiting Protection

- **Automatic Retries**: Exponential backoff (2s → 4s → 8s) on 429 errors
- **Configurable Delays**: `LLM_DELAY_SECONDS=1.5` between calls
- **Fallback Support**: Automatic switch to alternative provider
- **Quota Protection**: Prevents API exhaustion during heavy usage

## 15.2 Configuration

```env
# Choose your primary provider
LLM_PROVIDER=gemini          # Options: "gemini" or "openai"
LLM_AUTO_FALLBACK=true       # Try other provider if primary fails
LLM_DELAY_SECONDS=1.5        # Delay between LLM calls to prevent rate limits

# Google Gemini (get key at https://aistudio.google.com/app/apikey)
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.0-flash

# OpenAI (fallback)
OPENAI_API_KEY=sk-your-openai-key
OPENAI_MODEL=gpt-4o
```

## 15.3 Usage in Code

All agents use the unified `LLMClient`:

```python
from agents.llm_client import get_llm_client

# Get the configured client
client = get_llm_client()

# Make a request
response = await client.chat(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Analyze this data..."}
    ],
    temperature=0.7,
    json_response=True  # Request structured JSON output
)

# Parse the response
result = response.json()
```

## 15.4 Fallback Behavior

```
Request Received
      │
      ▼
┌─────────────┐
│   Primary   │──── Success ────► Response
│  Provider   │
└─────────────┘
      │
    Failure
      │
      ▼
┌─────────────┐
│  Fallback   │──── Success ────► Response
│  Provider   │
└─────────────┘
      │
    Failure
      │
      ▼
   Exception
```

## 15.5 Getting API Keys

### Google Gemini (Free Tier Available)
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with Google account
3. Click "Create API Key"
4. Copy and add to `.env`

### OpenAI
1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create account or sign in
3. Create new API key
4. Copy and add to `.env`

---

**END OF MASTER DOCUMENTATION**

*Last Updated: December 12, 2025*
*Version: 4.3 (Phases 1-10 Complete + Ideas Machine Planning Workflow + Rate Limiting Protection)*

