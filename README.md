# ArmLenQuant: Autonomous Agent Orchestration System

![ArmLenQuant Banner](https://via.placeholder.com/800x200/1a1a1a/ffffff?text=ARMLENQUANT+-+AUTONOMOUS+AGENT+ORCHESTRATION+SYSTEM)

[![Version](https://img.shields.io/badge/version-4.3-blue.svg)](https://github.com/armlenquant-cloud/armlenquant)
[![Status](https://img.shields.io/badge/status-phases_1--10_complete-green.svg)](https://github.com/armlenquant-cloud/armlenquant)
[![Architecture](https://img.shields.io/badge/architecture-split--brain-orange.svg)](https://github.com/armlenquant-cloud/armlenquant)

> **A self-evolving autonomous agent system that unifies all digital operations across business, development, research, and personal life into one intelligent orchestration layer.**

## 🚀 What ArmLenQuant Does

ArmLenQuant is an intelligent automation platform that orchestrates multiple AI agents to handle complex workflows autonomously. Think of it as your personal digital workforce that operates 24/7, learning from patterns and continuously improving.

### Core Capabilities

- **🤖 Autonomous Agent Management**: Self-evolving ecosystem of specialized AI agents
- **🎯 Intelligent Task Routing**: Natural language commands automatically routed to optimal agents
- **💼 Career Automation**: Job searching, CV tailoring, and application generation
- **🚀 Project Scaffolding**: AI-powered full-stack project generation with tech stack intelligence
- **📈 Crypto Market Intelligence**: Automated trading signals and market analysis
- **🔧 Agent Self-Creation**: Meta agents that can spawn new capabilities on demand
- **📱 Real-time Notifications**: Telegram bot integration for instant updates
- **🧠 Memory & Learning**: RAG-powered knowledge base for contextual intelligence

## 📋 What It Doesn't Do

- **Not a single-purpose tool**: ArmLenQuant orchestrates multiple specialized agents
- **Not cloud-only**: Requires local Windows machine for execution capabilities
- **Not a generic chatbot**: Focused on autonomous task completion, not conversation
- **Not instant deployment**: Currently requires local setup (cloud deployment in Phase 11)

## 🏗️ Architecture

### Split-Brain Design

```
┌─────────────────────────────────────┐
│         ☁️  THE TOWER  ☁️           │ ← Cloud (Decisions & Persistence)
│  (DigitalOcean + MongoDB Atlas)     │
│                                     │
│  ┌─────────────┐ ┌─────────────┐    │
│  │ Agent 00    │ │   Dashboard │    │
│  │ Orchestrator│ │   (Next.js) │    │
│  └─────────────┘ └─────────────┘    │
│           │           │             │
└───────────┼───────────┼─────────────┘
            │           │
            │           │
┌───────────┼───────────┼─────────────┐
│           ▼           ▼             │
│     💻  FIELD OPS  💻              │ ← Local (Execution & Files)
│     (Your Windows PC)              │
│                                    │
│  ┌─────────────┐ ┌─────────────┐    │
│  │ Job Hunter  │ │Ideas Machine│    │
│  │             │ │             │    │
│  └─────────────┘ └─────────────┘    │
│                                    │
└────────────────────────────────────┘
```

**Why this design?**
- **Cloud**: 24/7 availability, blocked IP access, data persistence
- **Local**: Residential IP, file system access, browser automation, compute power

## 📊 Current Status: MVP Complete

### ✅ **IMPLEMENTATION COMPLETE** (Phases 1-10)

All local development is finished with **475 passing tests** across all components:

| Phase | Component | Status | Tests |
|-------|-----------|---------|-------|
| 1-2 | Core API + Local Poller | ✅ Complete | 455 |
| 3 | Dashboard (Next.js) | ✅ Complete | Build Success |
| 4-6 | Orchestrator + RAG + Crypto Sentinel | ✅ Complete | 48 + 39 + 46 |
| 7-8 | Job Hunter + Ideas Machine | ✅ Complete | 47 + 50 |
| 9-10 | Meta Builder + Integration | ✅ Complete | 51 + 61 |

**Ready for:** End-to-end integration testing and cloud deployment.

## 🔮 Next Phases

### 🚀 **Phase 11: Cloud Deployment** (Next)
- Deploy to DigitalOcean Droplet
- Configure MongoDB Atlas production cluster
- Set up domain, SSL, and reverse proxy
- End-to-end integration testing

### 🔮 **Future Phases** (Planned)
- **Phase 12**: Multi-user support and agent marketplaces
- **Phase 13**: Advanced analytics and performance optimization
- **Phase 14**: Mobile app companion
- **Phase 15**: Enterprise features and team collaboration

## 🎯 Key Features

### 🤖 Agent Ecosystem

| Agent | Purpose | Location | Trigger |
|-------|---------|----------|---------|
| **Agent 00: Orchestrator** | Routes tasks, spawns agents, governs system | Cloud | Always-on |
| **Crypto Sentinel** | Market analysis & trading signals | Cloud | Daily (08:00) |
| **Job Hunter** | Autonomous job search & applications | Local | On-demand |
| **Ideas Machine** | AI project generation with planning approval | Local | On-demand |
| **Meta-Builder** | Creates new agents automatically | Local | On-demand |

### 🧠 Smart Capabilities

- **Natural Language Commands**: "Find Python jobs in Berlin" → Job Hunter
- **Context-Aware Routing**: Uses RAG to understand intent and provide relevant context
- **Human-in-the-Loop Planning**: Ideas Machine generates plans for your approval
- **Rate Limiting Protection**: Automatic fallback between LLM providers
- **Self-Healing**: Auto-recovery from failures, agent respawning

### 🔧 Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend API** | FastAPI + Python | REST API, task orchestration |
| **Database** | MongoDB Atlas | Document storage, vector search |
| **Frontend** | Next.js 16 + TypeScript | Dashboard UI |
| **AI/ML** | Gemini + OpenAI (fallback) | LLM for agent intelligence |
| **Local Execution** | Python + Playwright | Browser automation, file ops |
| **Deployment** | Docker + PM2 | Containerization, process management |

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+** (for API and local agents)
- **Node.js 18+** (for dashboard)
- **MongoDB** (local or Atlas free tier)
- **Gemini API Key** (free tier available)

### 1. Clone & Setup

```bash
git clone https://github.com/armlenquant-cloud/armlenquant.git
cd armlenquant
```

### 2. Configure Environment

**IMPORTANT:** Never commit `.env` files to version control! Use the provided `.env.example` files as templates.

```bash
# Copy example files to create your .env files
cp armlenquant-cloud/api/.env.example armlenquant-cloud/api/.env
cp armlenquant-cloud/dashboard/.env.example armlenquant-cloud/dashboard/.env.local
cp armlenquant-local/.env.example armlenquant-local/.env

# Edit each .env file with your actual configuration:
# - API keys (Gemini, OpenAI, etc.)
# - Database credentials
# - JWT secrets (generate with: python -c "import secrets; print(secrets.token_hex(32))")
# - Agent communication secrets
```

**Security Note:** Always generate secure random strings for secrets. Never use the example values in production!

### 3. Run Locally

**Terminal 1 - Cloud API:**
```bash
cd armlenquant-cloud/api
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python -m app.main
```

**Terminal 2 - Dashboard:**
```bash
cd armlenquant-cloud/dashboard
npm install
npm run dev
```

**Terminal 3 - Local Poller:**
```bash
cd armlenquant-local
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python -m poller.main
```

### 4. Access Dashboard

Open [http://localhost:3000](http://localhost:3000) and start commanding your agents!

## 💡 Example Workflows

### Job Search Automation
```
Input: "Find senior Python developer roles in European remote positions"

Output:
├── ~/Job_Drafts/2024-01-15_company_a_senior_python_dev/
│   ├── resume_tailored.md (85% match score)
│   ├── cover_letter.md
│   └── application_strategy.md
└── ~/Job_Drafts/2024-01-15_company_b_senior_python_dev/
    ├── resume_tailored.md (92% match score)
    ├── cover_letter.md
    └── application_strategy.md
```

### Project Scaffolding
```
Input: "Create a habit tracking SaaS with Next.js frontend, FastAPI backend, and MongoDB"

Output:
├── ~/Projects/habit_tracker_saas/
│   ├── frontend/ (Next.js + TypeScript)
│   ├── backend/ (FastAPI + MongoDB)
│   ├── docker-compose.yml
│   ├── .cursorrules
│   └── README.md (with deployment instructions)
```

### Agent Creation
```
Input: "Create an agent that monitors competitor pricing"

Output:
├── armlenquant-local/agents/competitor_tracker/
│   ├── agent.py (full implementation)
│   ├── models.py (data structures)
│   ├── tests/ (comprehensive test suite)
│   └── config.json
```

## 🔐 Security & Permissions

- **API Authentication**: JWT-based user authentication
- **Agent Communication**: Shared secret keys for cloud-local communication
- **IP Restrictions**: Optional IP whitelisting for home network
- **Isolated Execution**: Local agents run in sandboxed environment
- **No Dangerous Code**: Cloud prevents execution of untrusted scripts

## 📈 Performance & Reliability

- **Rate Limiting**: Configurable delays between LLM calls (prevents API exhaustion)
- **Auto-Fallback**: Gemini → OpenAI automatic provider switching
- **Health Monitoring**: Real-time system vitals and agent performance tracking
- **Error Recovery**: Automatic retry with exponential backoff
- **Self-Healing**: System detects and recovers from agent failures

## 🤝 Contributing

This is a solo project currently in active development. Future contributions welcome after Phase 11 completion.

## 📄 Documentation

- **[MASTER_DOCUMENTATION.md](./MASTER_DOCUMENTATION.md)** - Complete technical specification
- **[GETTING_STARTED.md](./GETTING_STARTED.md)** - Step-by-step setup guide
- **[PHASE_00_INFRASTRUCTURE.md](./phases/PHASE_00_INFRASTRUCTURE.md)** - Deployment guide
- **[Agent Specs](./)** - Individual agent documentation

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/armlenquant-cloud/armlenquant/issues)
- **Documentation**: See `DOCUMENTATION_GAPS.md` for known gaps
- **Status**: All phases 1-10 complete, Phase 11 (cloud deployment) in progress

---

## 🎯 Mission Statement

**To create a self-evolving autonomous agent system that acts as your digital workforce, continuously learning and improving to handle increasingly complex tasks across all domains of digital life.**

*Built with ❤️ by a solo developer in pursuit of autonomous computing.*

---

**Ready to command your digital workforce?** 🚀

[Get Started →](./GETTING_STARTED.md)