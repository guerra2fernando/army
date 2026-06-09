# ArmLenQuant: Autonomous Agent Orchestration System

[![Version](https://img.shields.io/badge/version-4.3-blue.svg)](https://github.com/guerra2fernando/army)
[![Status](https://img.shields.io/badge/status-production_ready-green.svg)](https://github.com/guerra2fernando/army)
[![Architecture](https://img.shields.io/badge/architecture-split--brain-orange.svg)](https://github.com/guerra2fernando/army)

> **A self-evolving autonomous agent system that unifies all digital operations across business, development, research, and personal life into one intelligent orchestration layer.**

## 🚀 What ArmLenQuant Does

ArmLenQuant is an intelligent automation platform that orchestrates multiple AI agents to handle complex workflows autonomously. Think of it as your personal digital workforce that operates 24/7, learning from patterns and continuously improving.

### Real-World Example
Imagine you need to:
1. Find job opportunities matching your skills
2. Generate tailored resumes and cover letters
3. Create a new SaaS project with full-stack code
4. Monitor cryptocurrency markets for trading opportunities
5. Automate outreach to potential clients

Instead of doing each task manually, you simply tell ArmLenQuant: "Find me Python developer jobs, create a habit tracker SaaS, and monitor Bitcoin trends." The system automatically:
- Routes each task to specialized agents
- Executes the workflows in parallel
- Learns from your preferences over time
- Delivers completed results to you

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
- **Not instant deployment**: Currently requires local setup (cloud deployment planned)

## 🏗️ Architecture

### Split-Brain Design

```
┌─────────────────────────────────────┐
│         ☁️  THE TOWER  ☁️           │ ← Cloud (Decisions & Persistence)
│  (Any Cloud + MongoDB Atlas)        │
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

## 📊 Current Status

### ✅ **Production Ready**

All development is complete with **475 passing tests** across all components:

| Component | Status | Tests |
|-----------|---------|-------|
| Core API + Local Poller | ✅ Complete | 455 |
| Dashboard (Next.js) | ✅ Complete | Build Success |
| Orchestrator + RAG + Crypto Sentinel | ✅ Complete | 48 + 39 + 46 |
| Job Hunter + Ideas Machine | ✅ Complete | 47 + 50 |
| Meta Builder + Integration | ✅ Complete | 51 + 61 |

**Ready for:** End-to-end integration testing and cloud deployment.

## 🔮 Roadmap

### 🚀 **Next: Cloud Deployment**
- Deploy to cloud provider (AWS, Azure, GCP, DigitalOcean, etc.)
- Configure MongoDB Atlas production cluster
- Set up domain, SSL, and reverse proxy
- End-to-end integration testing

### 🔮 **Future Enhancements**
- Multi-user support and agent marketplaces
- Advanced analytics and performance optimization
- Mobile app companion
- Enterprise features and team collaboration

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
git clone https://github.com/guerra2fernando/army.git
cd army
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

This is a solo project currently in active development. Future contributions welcome after cloud deployment completion. See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## 📄 Documentation

- **[MASTER_DOCUMENTATION.md](./MASTER_DOCUMENTATION.md)** - Complete technical specification
- **[GETTING_STARTED.md](./GETTING_STARTED.md)** - Step-by-step setup guide
- **[Agent Specs](./)** - Individual agent documentation

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/guerra2fernando/army/issues)
- **Documentation**: See `DOCUMENTATION_GAPS.md` for known gaps
- **Status**: Production ready, cloud deployment planned

---

## 🎯 Mission Statement

**To create a self-evolving autonomous agent system that acts as your digital workforce, continuously learning and improving to handle increasingly complex tasks across all domains of digital life.**

*Built with ❤️ by a solo developer in pursuit of autonomous computing.*

---

**Ready to command your digital workforce?** 🚀

[Get Started →](./GETTING_STARTED.md)