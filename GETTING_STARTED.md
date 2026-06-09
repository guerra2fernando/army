# 🎯 Getting Started with ArmLenQuant

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    COMPLETE SETUP & WORKFLOW GUIDE                            ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Explained](#architecture-explained)
3. [Environment Setup](#environment-setup)
4. [Running Locally](#running-locally)
5. [Expected Workflows](#expected-workflows)
6. [Dashboard Walkthrough](#dashboard-walkthrough)
7. [Production Deployment Options](#production-deployment-options)
8. [FAQ](#faq)

---

## System Overview

ArmLenQuant is a **split-brain autonomous agent system**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           YOUR WORKFLOW                                      │
└─────────────────────────────────────────────────────────────────────────────┘

   YOU                    DASHBOARD                    LOCAL PC
    │                        │                            │
    │  "Find Python jobs"    │                            │
    ├───────────────────────►│                            │
    │                        │                            │
    │                        │  Task Created              │
    │                        │  ──────────────────────►   │
    │                        │                            │
    │                        │                     JOB HUNTER
    │                        │                     executes
    │                        │                            │
    │                        │  Results returned          │
    │                        │  ◄──────────────────────   │
    │                        │                            │
    │  View results          │                            │
    │◄───────────────────────│                            │
    │                        │                            │
```

### Three Components

| Component | Where It Runs | What It Does |
|-----------|---------------|--------------|
| **Cloud API** | Cloud server (or local for dev) | Central task queue, authentication, database |
| **Dashboard** | Cloud server (or local for dev) | Web interface for control and monitoring |
| **Local Poller** | Your Windows PC | Executes tasks using local agents |

---

## Architecture Explained

### Why This Design?

**Cloud (The Tower):**
- ✅ Always available 24/7
- ✅ Central point of coordination
- ✅ Database and authentication
- ❌ Can't do browser automation (blocked IPs)
- ❌ No access to local files

**Local (Field Ops):**
- ✅ Your residential IP (not blocked)
- ✅ Access to local file system
- ✅ Browser automation (Playwright)
- ✅ High compute power
- ❌ Only runs when PC is on

### The Polling Model

The Local Poller **pulls** tasks from the cloud (instead of cloud pushing):

```
EVERY 30 SECONDS:
┌──────────────┐        "Any tasks for me?"         ┌──────────────┐
│              │ ──────────────────────────────────►│              │
│  LOCAL       │                                    │  CLOUD API   │
│  POLLER      │◄────────────────────────────────── │              │
│              │        Task payload or "none"      │              │
└──────────────┘                                    └──────────────┘
       │
       │ If task received:
       ▼
┌──────────────┐
│    AGENT     │  Execute task (Job Hunter, Ideas Machine, etc.)
│   EXECUTES   │
└──────────────┘
       │
       ▼
┌──────────────┐
│   RESULTS    │  Upload results back to cloud
│   UPLOADED   │
└──────────────┘
```

---

## Environment Setup

### Required API Keys

| Service | Required? | Where to Get | Purpose |
|---------|-----------|--------------|---------|
| **Gemini API** | ✅ Yes (default) | [Google AI Studio](https://aistudio.google.com/app/apikey) | LLM for agents |
| **OpenAI API** | Optional | [OpenAI Platform](https://platform.openai.com/api-keys) | Fallback LLM |
| **MongoDB** | ✅ Yes | Local install or [MongoDB Atlas](https://cloud.mongodb.com) (free) | Database |
| **CoinGecko** | Optional | Free tier works | Crypto data |
| **CryptoPanic** | Optional | [CryptoPanic](https://cryptopanic.com/developers/api/) | Crypto news |
| **Telegram** | Optional | [@BotFather](https://t.me/botfather) | Notifications |

### Configuration Files

#### 1. Cloud API `.env` (Full)

```env
# =============================================================================
# ARMLENQUANT CLOUD API CONFIGURATION
# =============================================================================

# -----------------------------------------------------------------------------
# Application
# -----------------------------------------------------------------------------
APP_NAME=ArmLenQuant API
APP_VERSION=1.0.0
DEBUG=true

# -----------------------------------------------------------------------------
# Server
# -----------------------------------------------------------------------------
API_HOST=0.0.0.0
API_PORT=8000

# -----------------------------------------------------------------------------
# Database (MongoDB)
# -----------------------------------------------------------------------------
# Local MongoDB:
MONGODB_URI=mongodb://localhost:27017
# OR MongoDB Atlas:
# MONGODB_URI=mongodb+srv://user:password@cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB_NAME=armlenquant

# -----------------------------------------------------------------------------
# Authentication (GENERATE SECURE RANDOM STRINGS!)
# Use: python -c "import secrets; print(secrets.token_hex(32))"
# -----------------------------------------------------------------------------
JWT_SECRET=your-super-secret-jwt-key-at-least-32-characters-long-here
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=168

# Agent communication (same as in local poller)
AGENT_SECRET=your-agent-communication-secret-key-shared-with-poller

# -----------------------------------------------------------------------------
# LLM Configuration
# -----------------------------------------------------------------------------
LLM_PROVIDER=gemini
LLM_AUTO_FALLBACK=true

# Google Gemini (DEFAULT)
GEMINI_API_KEY=your-gemini-api-key-from-google-ai-studio
GEMINI_MODEL=gemini-2.0-flash

# OpenAI (Fallback)
OPENAI_API_KEY=sk-optional-openai-key
OPENAI_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# -----------------------------------------------------------------------------
# Crypto APIs (Optional - for Crypto Sentinel)
# -----------------------------------------------------------------------------
COINGECKO_API_KEY=
CRYPTOPANIC_API_KEY=your-cryptopanic-key

# -----------------------------------------------------------------------------
# Telegram Notifications (Optional)
# -----------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
TELEGRAM_ENABLED=false

# -----------------------------------------------------------------------------
# Notification Settings
# -----------------------------------------------------------------------------
NOTIFICATIONS_ENABLED=true
NOTIFY_ON_TASK_COMPLETE=true
NOTIFY_ON_TASK_FAILED=true
NOTIFY_ON_AGENT_ALERT=true
NOTIFY_ON_SYSTEM_ERROR=true

# -----------------------------------------------------------------------------
# Rate Limiting
# -----------------------------------------------------------------------------
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

#### 2. Dashboard `.env.local`

```env
# API URL (must match where your API is running)
NEXT_PUBLIC_API_URL=http://localhost:8000

# For production:
# NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

#### 3. Local Poller `.env`

```env
# =============================================================================
# ARMLENQUANT LOCAL POLLER CONFIGURATION
# =============================================================================

# -----------------------------------------------------------------------------
# API Connection
# -----------------------------------------------------------------------------
API_URL=http://localhost:8000
# For production: API_URL=https://api.yourdomain.com

# Must match AGENT_SECRET in cloud API
AGENT_SECRET=your-agent-communication-secret-key-shared-with-poller

# -----------------------------------------------------------------------------
# Worker Identity
# -----------------------------------------------------------------------------
WORKER_ID=WINDOWS_LOCAL_01

# -----------------------------------------------------------------------------
# Polling Configuration
# -----------------------------------------------------------------------------
POLL_INTERVAL_SECONDS=30
TASK_TIMEOUT_SECONDS=300
HEARTBEAT_INTERVAL_SECONDS=60

# -----------------------------------------------------------------------------
# LLM Configuration
# -----------------------------------------------------------------------------
LLM_PROVIDER=gemini
LLM_AUTO_FALLBACK=true

# Google Gemini (DEFAULT)
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.0-flash

# OpenAI (Fallback)
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o

# -----------------------------------------------------------------------------
# Paths (where outputs are saved)
# -----------------------------------------------------------------------------
JOB_DRAFTS_PATH=~/Job_Drafts
PROJECTS_PATH=~/Projects
CV_PATH=~/Documents/CV/master_cv.md

# -----------------------------------------------------------------------------
# Browser Automation
# -----------------------------------------------------------------------------
HEADLESS_MODE=true
BROWSER_TIMEOUT=30000

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
LOG_LEVEL=INFO
```

---

## Running Locally

### Option A: Three Separate Terminals (Recommended for Dev)

**Terminal 1 - Cloud API:**
```powershell
cd C:\Users\smikl\Desktop\Work\Army\armlenquant-cloud\api
.\venv\Scripts\Activate.ps1
python -m app.main
```

**Terminal 2 - Dashboard:**
```powershell
cd C:\Users\smikl\Desktop\Work\Army\armlenquant-cloud\dashboard
npm run dev
```

**Terminal 3 - Local Poller:**
```powershell
cd C:\Users\smikl\Desktop\Work\Army\armlenquant-local
.\venv\Scripts\Activate.ps1
python -m poller.main
```

### Option B: Background Running (Windows)

You can minimize terminals, but they need to stay open. For production, see Docker deployment below.

---

## Expected Workflows

### 1. Job Search Workflow

```
Dashboard                          Local Poller                    Output
─────────────────────────────────────────────────────────────────────────────
1. Create Task                     
   Agent: JOB_HUNTER              
   Payload:                        
   {                               
     "action": "search",           
     "roles": ["Python Dev"],      2. Poller picks up task
     "locations": ["Remote"]          │
   }                                  ▼
                                   3. Job Hunter Agent:
                                      - Searches Google
                                      - Parses job listings
                                      - Matches against CV
                                      - Generates materials
                                         │
                                         ▼
4. Results appear in                   ~/Job_Drafts/
   Dashboard Tasks page                2024-12-04_company_role/
                                       ├── resume_tailored.md
                                       ├── cover_letter.md
                                       └── match_analysis.json
```

### 2. Project Scaffolding Workflow

```
Dashboard                          Local Poller                    Output
─────────────────────────────────────────────────────────────────────────────
1. Create Task
   Agent: IDEAS_MACHINE
   Payload:
   {
     "action": "scaffold",         2. Poller picks up task
     "description": "A SaaS          │
       for tracking habits"          ▼
   }                               3. Ideas Machine Agent:
                                      - Analyzes idea
                                      - Recommends tech stack
                                      - Designs architecture
                                      - Generates project files
                                         │
                                         ▼
4. Results appear in                   ~/Projects/
   Dashboard Tasks page                habit_tracker/
                                       ├── package.json
                                       ├── src/
                                       ├── docs/
                                       └── .cursorrules
```

### 3. Agent Creation Workflow

```
Dashboard                          Local Poller                    Output
─────────────────────────────────────────────────────────────────────────────
1. Create Task
   Agent: META_BUILDER
   Payload:
   {
     "action": "build",            2. Poller picks up task
     "description": "Agent that       │
       monitors stock prices"         ▼
   }                               3. Meta Builder Agent:
                                      - Parses spec
                                      - Generates code
                                      - Creates tests
                                      - Saves files
                                         │
                                         ▼
4. New agent code created              armlenquant-local/
   Ready to register                   agents/
                                       stock_monitor/
                                       ├── agent.py
                                       ├── models.py
                                       └── tests/
```

---

## Dashboard Walkthrough

### Login Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                       http://localhost:3000                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                        🔐 LOGIN                                 │
│                                                                 │
│            ┌─────────────────────────────────┐                 │
│            │  Email:    you@email.com        │                 │
│            └─────────────────────────────────┘                 │
│            ┌─────────────────────────────────┐                 │
│            │  Password: ••••••••             │                 │
│            └─────────────────────────────────┘                 │
│                                                                 │
│                    [ Login ] [ Register ]                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Command Center (Home)

```
┌─────────────────────────────────────────────────────────────────┐
│  LENQUANT                              System: ● Online         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ 📋 TASKS        │  │ 🤖 AGENTS       │  │ ⚡ SYSTEM       │ │
│  │                 │  │                 │  │                 │ │
│  │ Pending: 2      │  │ Active: 4       │  │ Status: Healthy │ │
│  │ Running: 1      │  │ Paused: 0       │  │ Uptime: 99.9%   │ │
│  │ Completed: 47   │  │                 │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                 │
│  ─────────────────── RECENT ACTIVITY ────────────────────────  │
│  • Job Hunter completed: 5 jobs found, 3 high matches          │
│  • Ideas Machine: Project "habit_tracker" scaffolded           │
│  • Local Poller: Heartbeat received                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Tasks Page

```
┌─────────────────────────────────────────────────────────────────┐
│  TASKS                                        [ + Create Task ] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Filter: [All ▼] [All Agents ▼]                                │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ ID          Agent           Status      Created           │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │ abc-123     IDEAS_MACHINE   ● Complete  5 min ago        │ │
│  │ def-456     JOB_HUNTER      ○ Running   10 min ago       │ │
│  │ ghi-789     META_BUILDER    ◌ Pending   15 min ago       │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Click task to view details and results                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Agents Page

```
┌─────────────────────────────────────────────────────────────────┐
│  AGENTS                                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Agent              Location   Status    Success   Actions │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │ JOB_HUNTER         Local      ● Active  92%       [⏸]    │ │
│  │ IDEAS_MACHINE      Local      ● Active  98%       [⏸]    │ │
│  │ META_BUILDER       Local      ● Active  100%      [⏸]    │ │
│  │ CRYPTO_SENTINEL    Cloud      ● Active  95%       [⏸]    │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Local Poller Status: ● Connected (last heartbeat: 10s ago)    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Production Deployment Options

### Option 1: Traditional (PM2 + Nginx)

See `PHASE_00_INFRASTRUCTURE.md` for full details.

**Pros:** Simple, low resource usage
**Cons:** Manual setup, no containerization

### Option 2: Docker (Recommended for Cloud)

See the Docker section in `PHASE_00_INFRASTRUCTURE.md`.

**Pros:** Reproducible, easy scaling, automatic restarts
**Cons:** Slightly more resource usage

### Local Poller Always Runs on Windows

⚠️ The Local Poller **always** runs on your Windows PC, not in Docker. This is by design:
- Needs residential IP for web scraping
- Needs local file system access
- Needs browser automation

---

## FAQ

### Q: Do I need to keep terminals open?

**Local Development:** Yes, all three terminals need to stay open.

**Production (Cloud):** No. Use Docker or PM2 to run services in background.

**Local Poller:** Always needs to run on your PC when you want tasks executed. You can minimize the terminal.

### Q: Can I use only Gemini without OpenAI?

Yes! Gemini is the default. Set `LLM_PROVIDER=gemini` and leave `OPENAI_API_KEY` empty.

### Q: What if the Local Poller disconnects?

Tasks remain in "PENDING" state. When Poller reconnects, it picks them up. No data is lost.

### Q: How do I add my CV for job matching?

1. Save your CV as markdown at the path in `CV_PATH`
2. Default: `~/Documents/CV/master_cv.md`
3. Job Hunter will automatically use it

### Q: Where are generated files saved?

| Agent | Output Location |
|-------|-----------------|
| Job Hunter | `~/Job_Drafts/` |
| Ideas Machine | `~/Projects/` |
| Meta Builder | `armlenquant-local/agents/` |

---

*Getting Started Guide - ArmLenQuant v1.0*
*Last Updated: December 4, 2025*

