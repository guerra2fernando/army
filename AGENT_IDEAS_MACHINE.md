# AGENT: IDEAS MACHINE
## Autonomous Project Scaffolding & Development Blueprint Generator

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║        ██╗██████╗░███████╗░█████╗░░██████╗                                   ║
║        ██║██╔══██╗██╔════╝██╔══██╗██╔════╝                                   ║
║        ██║██║░░██║█████╗░░███████║╚█████╗░                                   ║
║        ██║██║░░██║██╔══╝░░██╔══██║░╚═══██╗                                   ║
║        ██║██████╔╝███████╗██║░░██║██████╔╝                                   ║
║        ╚═╝╚═════╝░╚══════╝╚═╝░░╚═╝╚═════╝░                                   ║
║                                                                               ║
║        ███╗░░░███╗░█████╗░░█████╗░██╗░░██╗██╗███╗░░██╗███████╗              ║
║        ████╗░████║██╔══██╗██╔══██╗██║░░██║██║████╗░██║██╔════╝              ║
║        ██╔████╔██║███████║██║░░╚═╝███████║██║██╔██╗██║█████╗░░              ║
║        ██║╚██╔╝██║██╔══██║██║░░██╗██╔══██║██║██║╚████║██╔══╝░░              ║
║        ██║░╚═╝░██║██║░░██║╚█████╔╝██║░░██║██║██║░╚███║███████╗              ║
║        ╚═╝░░░░░╚═╝╚═╝░░╚═╝░╚════╝░╚═╝░░╚═╝╚═╝╚═╝░░╚══╝╚══════╝              ║
║                                                                               ║
║                    PROJECT INTELLIGENCE AGENT                                 ║
║                         Version 2.0                                           ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

**Agent ID:** `IDEAS_MACHINE`  
**Location:** Local (Windows)  
**Primary Trigger:** Task Queue  
**Secondary Triggers:** Manual, Event-based  

---

## TABLE OF CONTENTS

1. [Mission Statement](#1-mission-statement)
2. [Core Capabilities](#2-core-capabilities)
3. [The Architect Workflow](#3-the-architect-workflow)
4. [Project Analysis Engine](#4-project-analysis-engine)
5. [Scaffolding System](#5-scaffolding-system)
6. [Documentation Generation](#6-documentation-generation)
7. [Cursor Integration](#7-cursor-integration)
8. [Template Library](#8-template-library)
9. [Technical Specification](#9-technical-specification)
10. [Output Formats](#10-output-formats)

---

# 1. MISSION STATEMENT

The Ideas Machine is the **project intelligence agent** of ArmLenQuant. It transforms raw ideas, sketches, and notes into fully structured project scaffolds ready for development in Cursor or any modern IDE.

### The Problem It Solves

```
┌─────────────────────────────────────────────────────────────────┐
│                     THE IDEA → CODE GAP                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   "I have an idea..."                                          │
│         │                                                       │
│         ▼                                                       │
│   [  GAP  ] ← This is where most ideas die                     │
│         │                                                       │
│         ▼                                                       │
│   "...but where do I even start?"                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**The Ideas Machine bridges this gap.**

### Core Philosophy

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   💡 CAPTURE    →    Never lose an idea, no matter how raw     │
│   🏗️  STRUCTURE  →    Transform chaos into organized plans      │
│   📐 ARCHITECT  →    Design before you code                     │
│   📁 SCAFFOLD   →    Generate project structure automatically  │
│   🤖 INTEGRATE  →    Prepare for AI-assisted development       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

# 2. CORE CAPABILITIES

## 2.1 Idea Ingestion

| Capability | Description |
|------------|-------------|
| **Raw Text Parsing** | Extract structure from messy notes |
| **Voice Note Processing** | Transcribe and structure spoken ideas |
| **Image/Sketch Analysis** | Interpret wireframes and diagrams |
| **Link Extraction** | Pull inspiration from referenced URLs |

## 2.2 Project Analysis

| Capability | Description |
|------------|-------------|
| **Scope Estimation** | Calculate project complexity (hours/days/weeks) |
| **Tech Stack Recommendation** | Suggest optimal technologies |
| **Feature Prioritization** | Identify MVP vs. future features |
| **Risk Assessment** | Flag technical challenges early |

## 2.3 Documentation Generation

| Capability | Description |
|------------|-------------|
| **Master Plan** | High-level project overview |
| **Phase Specifications** | Detailed specs per development phase |
| **Technical Architecture** | System design documents |
| **API Contracts** | Interface definitions |
| **Data Models** | Database schema designs |

## 2.4 Scaffolding

| Capability | Description |
|------------|-------------|
| **Directory Structure** | Generate project folders |
| **Config Files** | Create `.cursorrules`, `package.json`, etc. |
| **Boilerplate Code** | Starter files for each component |
| **Cursor Prompts** | Pre-written prompts for Cursor AI |

---

# 3. THE ARCHITECT WORKFLOW

## 3.1 End-to-End Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    IDEAS MACHINE PIPELINE                       │
└─────────────────────────────────────────────────────────────────┘

    ┌───────────────────┐
    │ 1. INGEST         │
    │                   │
    │ • Raw idea input  │
    │ • Notes, links    │
    │ • Voice/image     │
    └────────┬──────────┘
             │
    ┌────────▼──────────┐
    │ 2. ANALYZE        │
    │                   │
    │ • Extract intent  │
    │ • Identify scope  │
    │ • Detect patterns │
    └────────┬──────────┘
             │
    ┌────────▼──────────┐
    │ 3. STRUCTURE      │
    │                   │
    │ • Break into      │
    │   phases          │
    │ • Prioritize      │
    │   features        │
    │ • Define MVP      │
    └────────┬──────────┘
             │
    ┌────────▼──────────┐
    │ 4. ARCHITECT      │
    │                   │
    │ • Tech stack      │
    │ • System design   │
    │ • Data models     │
    │ • API contracts   │
    └────────┬──────────┘
             │
    ┌────────▼──────────┐
    │ 5. DOCUMENT       │
    │                   │
    │ • Master plan     │
    │ • Phase specs     │
    │ • Architecture    │
    └────────┬──────────┘
             │
    ┌────────▼──────────┐
    │ 6. SCAFFOLD       │
    │                   │
    │ • Create folders  │
    │ • Generate files  │
    │ • Write configs   │
    └────────┬──────────┘
             │
    ┌────────▼──────────┐
    │ 7. INTEGRATE      │
    │                   │
    │ • Cursor prompts  │
    │ • .cursorrules    │
    │ • Ready to code   │
    └───────────────────┘
```

## 3.2 Input Modes

### Mode A: Text Note

User provides a raw text description:

```
Input: "I want to build a habit tracking app. It should let users 
create daily habits, track streaks, and see their progress over time. 
Maybe add some gamification like badges. Should work on mobile and web."
```

### Mode B: Structured Brief

User provides more detailed requirements:

```yaml
project:
  name: "HabitForge"
  type: "Web + Mobile App"
  
goals:
  - Track daily habits
  - Visualize progress
  - Gamification (badges, streaks)
  
constraints:
  - Budget: Side project (low cost)
  - Timeline: MVP in 2 weeks
  - Tech preference: React/Next.js
```

### Mode C: Reference-Based

User provides examples and inspiration:

```
Input: "Build something like Habitica but simpler. 
Reference: https://habitica.com
I like their streak system but not the RPG complexity.
Focus on simplicity and beautiful charts."
```

---

# 4. PROJECT ANALYSIS ENGINE

## 4.1 Scope Classification

```
┌─────────────────────────────────────────────────────────────────┐
│                    PROJECT SIZE MATRIX                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   MICRO        │ 1-3 days  │ Single feature, simple logic      │
│   SMALL        │ 1-2 weeks │ Basic app, few screens            │
│   MEDIUM       │ 1-2 months│ Full MVP, multiple features       │
│   LARGE        │ 3-6 months│ Complex app, integrations         │
│   ENTERPRISE   │ 6+ months │ Full product, team required       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 4.2 Complexity Scoring

Each project is scored on multiple dimensions:

```javascript
complexity_score = {
  frontend: {
    screens: 5,           // Number of unique screens
    interactivity: "HIGH", // Static/Medium/High
    animations: "MEDIUM",  // None/Basic/Medium/Complex
    score: 7              // 1-10
  },
  backend: {
    endpoints: 12,         // Number of API endpoints
    auth: "JWT",           // None/Basic/OAuth/Custom
    database: "RELATIONAL", // None/Key-Value/Document/Relational
    integrations: 2,       // Third-party APIs
    score: 6               // 1-10
  },
  infrastructure: {
    deployment: "SERVERLESS", // Static/Server/Serverless/K8s
    scaling: "AUTO",          // Manual/Auto/Complex
    monitoring: "BASIC",      // None/Basic/Advanced
    score: 4                  // 1-10
  },
  overall: 5.7,              // Weighted average
  classification: "MEDIUM"
}
```

## 4.3 Tech Stack Recommendation

Based on project analysis, recommend optimal stack:

### Decision Matrix

| Factor | Influences |
|--------|------------|
| Project size | Framework complexity tolerance |
| Team size | Learning curve considerations |
| Timeline | Boilerplate vs. custom |
| Budget | Hosting costs, service tiers |
| Scalability needs | Architecture decisions |

### Example Recommendation

```markdown
# TECH STACK RECOMMENDATION: HabitForge

## Frontend
- **Framework:** Next.js 14 (App Router)
- **Styling:** Tailwind CSS + Shadcn UI
- **State:** Zustand (simple, sufficient)
- **Charts:** Recharts

**Why:** Fast development, great DX, built-in API routes

## Backend
- **API:** Next.js API Routes (co-located)
- **Database:** Supabase (Postgres + Auth + Real-time)
- **Auth:** Supabase Auth (handles OAuth, magic links)

**Why:** Supabase = fast setup, generous free tier, scales well

## Infrastructure
- **Hosting:** Vercel (frontend) + Supabase (backend)
- **CI/CD:** GitHub Actions (auto-deploy on push)
- **Monitoring:** Vercel Analytics (free tier)

**Why:** Zero-config deployment, great developer experience

## Mobile (Phase 2)
- **Framework:** React Native + Expo
- **Shared Logic:** Move core logic to shared package

**Why:** Code sharing with web, fast iteration
```

---

# 5. SCAFFOLDING SYSTEM

## 5.1 Directory Structure Generation

For each project, Ideas Machine creates:

```
~/Projects/HabitForge/
│
├── .cursorrules                 # Cursor AI configuration
├── README.md                    # Project overview
├── package.json                 # Dependencies
├── .env.example                 # Environment template
├── .gitignore                   # Git ignore rules
│
├── docs/                        # Documentation
│   ├── 00_MASTER_PLAN.md       # High-level overview
│   ├── 01_PHASE_1_MVP.md       # MVP specification
│   ├── 02_PHASE_2_FEATURES.md  # Post-MVP features
│   ├── 03_ARCHITECTURE.md      # System design
│   ├── 04_DATA_MODELS.md       # Database schema
│   └── 05_API_CONTRACTS.md     # API documentation
│
├── prompts/                     # Cursor AI prompts
│   ├── CURSOR_COMMANDS.md      # Pre-written prompts
│   ├── 01_setup.md             # Initial setup prompt
│   ├── 02_auth.md              # Auth implementation
│   ├── 03_habits_crud.md       # Core CRUD
│   └── 04_dashboard.md         # Dashboard UI
│
├── src/                         # Source code (scaffolded)
│   ├── app/                    # Next.js app directory
│   │   ├── layout.tsx          # Root layout
│   │   ├── page.tsx            # Home page
│   │   ├── (auth)/             # Auth routes
│   │   ├── (dashboard)/        # Dashboard routes
│   │   └── api/                # API routes
│   │
│   ├── components/             # React components
│   │   ├── ui/                 # Shadcn components
│   │   └── features/           # Feature components
│   │
│   ├── lib/                    # Utilities
│   │   ├── supabase.ts         # Supabase client
│   │   ├── utils.ts            # Helper functions
│   │   └── constants.ts        # App constants
│   │
│   ├── hooks/                  # Custom hooks
│   ├── stores/                 # Zustand stores
│   └── types/                  # TypeScript types
│
├── supabase/                    # Supabase config
│   └── migrations/             # Database migrations
│
└── public/                      # Static assets
    └── images/
```

## 5.2 Config File Generation

### `.cursorrules`

```markdown
# Project: HabitForge
# Type: Habit Tracking Web Application

## Tech Stack
- Framework: Next.js 14 (App Router)
- Language: TypeScript (strict mode)
- Styling: Tailwind CSS + Shadcn UI
- Database: Supabase (PostgreSQL)
- Auth: Supabase Auth
- State: Zustand

## Code Style
- Use functional components with hooks
- Prefer server components, use 'use client' only when needed
- Use TypeScript strict mode, no `any` types
- Follow Airbnb style guide
- Use absolute imports with @/ prefix

## File Organization
- Components: src/components/{feature}/{ComponentName}.tsx
- API Routes: src/app/api/{resource}/route.ts
- Types: src/types/{feature}.ts
- Hooks: src/hooks/use{HookName}.ts

## Naming Conventions
- Components: PascalCase
- Files: kebab-case
- Functions: camelCase
- Constants: SCREAMING_SNAKE_CASE
- Types/Interfaces: PascalCase with 'I' prefix for interfaces

## Documentation
- Read docs/00_MASTER_PLAN.md for project overview
- Read docs/01_PHASE_1_MVP.md for current phase spec
- Read docs/04_DATA_MODELS.md for database schema

## Current Phase
Phase 1: MVP - Core habit tracking functionality

## Priority Commands
- @cursor Read prompts/CURSOR_COMMANDS.md for implementation prompts
- Start with prompts/01_setup.md
```

### `package.json`

```json
{
  "name": "habitforge",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "db:generate": "supabase gen types typescript --local > src/types/database.ts"
  },
  "dependencies": {
    "next": "14.x",
    "react": "18.x",
    "react-dom": "18.x",
    "@supabase/supabase-js": "^2.x",
    "zustand": "^4.x",
    "recharts": "^2.x",
    "lucide-react": "^0.x",
    "class-variance-authority": "^0.x",
    "clsx": "^2.x",
    "tailwind-merge": "^2.x"
  },
  "devDependencies": {
    "typescript": "^5.x",
    "@types/node": "^20.x",
    "@types/react": "^18.x",
    "tailwindcss": "^3.x",
    "postcss": "^8.x",
    "autoprefixer": "^10.x",
    "eslint": "^8.x",
    "eslint-config-next": "14.x"
  }
}
```

---

# 6. DOCUMENTATION GENERATION

## 6.1 Master Plan Document

```markdown
# HabitForge — Master Plan

## Vision
A beautiful, simple habit tracking app that helps users build lasting 
habits through streaks, progress visualization, and gentle gamification.

## Target User
- Professionals who want to build better habits
- Not gamers (no RPG complexity)
- Values simplicity and aesthetics

## Core Value Proposition
"Track habits in 10 seconds. See progress that motivates."

---

## Phase Overview

### Phase 1: MVP (2 weeks)
**Goal:** Core habit tracking that works

Features:
- [ ] User authentication
- [ ] Create/edit/delete habits
- [ ] Daily check-in (mark habits complete)
- [ ] Basic streak tracking
- [ ] Simple dashboard with today's habits

Success Criteria:
- User can sign up, create habits, and track for 7 days
- Streak counter works correctly
- Mobile-responsive design

### Phase 2: Visualization (1 week)
**Goal:** Beautiful progress insights

Features:
- [ ] Habit completion calendar (GitHub-style)
- [ ] Streak statistics
- [ ] Weekly/monthly completion charts
- [ ] Personal best tracking

### Phase 3: Gamification (1 week)
**Goal:** Motivation through achievement

Features:
- [ ] Badge system (7-day streak, 30-day streak, etc.)
- [ ] Habit categories with icons
- [ ] Milestone celebrations
- [ ] Optional daily reminders

### Phase 4: Polish & Launch
**Goal:** Production-ready product

Features:
- [ ] Onboarding flow
- [ ] Settings page
- [ ] Data export
- [ ] Performance optimization
- [ ] Error handling

---

## Non-Goals (Explicitly Out of Scope)
- Social features (no friends, no leaderboards)
- Habit suggestions (user defines their own)
- Complex scheduling (daily habits only for now)
- Native mobile app (responsive web first)

---

## Success Metrics
- User retention: 40% using after 7 days
- Session duration: 30 seconds average
- Habit completion rate: Track baseline
```

## 6.2 Phase Specification Document

```markdown
# Phase 1: MVP Specification

## Overview
Build the core habit tracking functionality. User should be able to:
1. Sign up / log in
2. Create habits
3. Mark habits complete daily
4. See their streak

## Detailed Requirements

### Authentication
**User Stories:**
- As a user, I can sign up with email/password
- As a user, I can log in with existing credentials
- As a user, I can log out
- As a user, I stay logged in across sessions

**Technical Notes:**
- Use Supabase Auth
- Implement protected routes
- Store session in cookies

### Habit CRUD
**User Stories:**
- As a user, I can create a new habit with a name
- As a user, I can edit a habit's name
- As a user, I can delete a habit (with confirmation)
- As a user, I see all my habits on the dashboard

**Data Model:**
```typescript
interface Habit {
  id: string;
  user_id: string;
  name: string;
  created_at: Date;
  is_active: boolean;
}
```

### Daily Check-In
**User Stories:**
- As a user, I see today's habits with checkboxes
- As a user, I can mark a habit complete for today
- As a user, I can unmark if I made a mistake
- As a user, I see which habits are done today

**Data Model:**
```typescript
interface HabitCompletion {
  id: string;
  habit_id: string;
  completed_at: Date;  // Date only, no time
}
```

### Streak Tracking
**User Stories:**
- As a user, I see my current streak for each habit
- As a user, my streak resets if I miss a day

**Logic:**
- Streak = consecutive days with completion
- Missing yesterday = streak resets to 0
- Today not done yet = show current streak

---

## UI Specifications

### Dashboard Layout
```
┌─────────────────────────────────────────────────────────────────┐
│  HabitForge                                    [User] [Logout]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Today — December 2, 2025                                       │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ☐  Exercise                                 🔥 12 days   │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ ☑  Read 30 minutes                         🔥 45 days   │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ ☐  Meditate                                 🔥 3 days    │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ ☑  Write journal                           🔥 89 days   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [+ Add New Habit]                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Color Scheme
- Background: #0A0A0A (near black)
- Card: #1A1A1A
- Primary: #22C55E (green for success)
- Accent: #F59E0B (amber for streaks)
- Text: #FAFAFA (white)
- Muted: #71717A (gray)

---

## API Endpoints

### Habits
- `GET /api/habits` — List user's habits
- `POST /api/habits` — Create habit
- `PATCH /api/habits/:id` — Update habit
- `DELETE /api/habits/:id` — Delete habit

### Completions
- `GET /api/completions?date=YYYY-MM-DD` — Get completions for date
- `POST /api/completions` — Mark habit complete
- `DELETE /api/completions/:id` — Unmark habit

### Streaks
- `GET /api/streaks` — Get all streaks for user's habits

---

## Database Schema (Supabase)

```sql
-- Users (handled by Supabase Auth)

-- Habits
CREATE TABLE habits (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  is_active BOOLEAN DEFAULT TRUE
);

-- Completions
CREATE TABLE completions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  habit_id UUID REFERENCES habits(id) ON DELETE CASCADE,
  completed_date DATE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(habit_id, completed_date)
);

-- Indexes
CREATE INDEX idx_habits_user_id ON habits(user_id);
CREATE INDEX idx_completions_habit_id ON completions(habit_id);
CREATE INDEX idx_completions_date ON completions(completed_date);

-- RLS Policies
ALTER TABLE habits ENABLE ROW LEVEL SECURITY;
ALTER TABLE completions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can only access own habits"
  ON habits FOR ALL
  USING (auth.uid() = user_id);

CREATE POLICY "Users can only access own completions"
  ON completions FOR ALL
  USING (habit_id IN (SELECT id FROM habits WHERE user_id = auth.uid()));
```
```

---

# 7. CURSOR INTEGRATION

## 7.1 Pre-Written Prompts

The Ideas Machine generates prompts optimized for Cursor AI:

### `prompts/CURSOR_COMMANDS.md`

```markdown
# Cursor Commands for HabitForge

Use these prompts with Cursor to implement each feature.
Copy the prompt, paste in Cursor chat, and let AI implement.

---

## Initial Setup

**Prompt 01: Project Setup**
```
@Cursor, help me set up this Next.js project:

1. Read .cursorrules for project context
2. Install all dependencies from package.json
3. Set up Tailwind CSS with the config
4. Create the basic folder structure in src/
5. Set up Supabase client in src/lib/supabase.ts
6. Create TypeScript types in src/types/

Reference docs/00_MASTER_PLAN.md for project overview.
```

---

## Phase 1 Implementation

**Prompt 02: Authentication**
```
@Cursor, implement authentication:

1. Read docs/01_PHASE_1_MVP.md for requirements
2. Create auth pages: /login, /signup
3. Use Supabase Auth for email/password
4. Create protected route middleware
5. Add auth context/provider
6. Create logout functionality

Use Shadcn UI components. Dark theme. Minimal design.
```

**Prompt 03: Habits CRUD**
```
@Cursor, implement habit management:

1. Read docs/01_PHASE_1_MVP.md for Habit data model
2. Create API routes: GET, POST, PATCH, DELETE /api/habits
3. Create Zustand store for habits state
4. Build habit list component
5. Build add habit modal
6. Build edit habit modal
7. Add delete with confirmation

Reference docs/04_DATA_MODELS.md for schema.
```

**Prompt 04: Daily Check-In**
```
@Cursor, implement daily habit tracking:

1. Read docs/01_PHASE_1_MVP.md for Completion model
2. Create API routes for completions
3. Build today's habits dashboard
4. Add checkbox toggle for each habit
5. Optimistic updates for smooth UX
6. Show completed vs pending state

Match the UI mockup in the spec document.
```

**Prompt 05: Streak Calculation**
```
@Cursor, implement streak tracking:

1. Read the streak logic in docs/01_PHASE_1_MVP.md
2. Create streak calculation function
3. Add GET /api/streaks endpoint
4. Display streak count next to each habit
5. Handle edge cases:
   - New habit (0 days)
   - Broken streak (reset)
   - Today not done yet (show current)

Use the 🔥 emoji for streak display.
```

---

## Testing Prompts

**Prompt: Test Coverage**
```
@Cursor, write tests for the habit tracking:

1. Unit tests for streak calculation
2. Integration tests for API routes
3. Component tests for habit list
4. E2E test for complete flow: signup → create habit → check in

Use Jest and React Testing Library.
```
```

## 7.2 `.cursorrules` Deep Dive

The generated `.cursorrules` file contains:

1. **Project context** — What the app does
2. **Tech stack** — Exact versions and libraries
3. **Code conventions** — How to write code
4. **File organization** — Where things go
5. **Current phase** — What to focus on
6. **Doc pointers** — Where to find specs

This enables Cursor to generate code that fits the project perfectly.

---

# 8. TEMPLATE LIBRARY

## 8.1 Project Templates

Ideas Machine includes templates for common project types:

| Template | Description | Stack |
|----------|-------------|-------|
| **SaaS Starter** | Full auth, billing, dashboard | Next.js + Supabase + Stripe |
| **Landing Page** | Marketing site with CMS | Next.js + Sanity/Contentful |
| **API Service** | REST/GraphQL backend | FastAPI/Express + PostgreSQL |
| **CLI Tool** | Command-line application | Python/Node + Rich/Ink |
| **Chrome Extension** | Browser extension | Manifest V3 + React |
| **Mobile App** | Cross-platform mobile | React Native + Expo |
| **Data Pipeline** | ETL/data processing | Python + Pandas + Airflow |
| **AI App** | LLM-powered application | Next.js + OpenAI + Pinecone |

## 8.2 Component Templates

Common components pre-scaffolded:

- Authentication (login, signup, forgot password)
- Dashboard layout (sidebar, header, content)
- Data tables (sorting, filtering, pagination)
- Form builders (validation, error handling)
- Modal systems (confirm, alert, custom)
- Toast notifications
- Loading states
- Error boundaries

---

# 9. TECHNICAL SPECIFICATION

## 9.1 Agent Configuration

```yaml
agent:
  id: "IDEAS_MACHINE"
  version: "2.0.0"
  location: "LOCAL"
  
triggers:
  - type: "TASK_QUEUE"
    action: "process_idea"
  
  - type: "MANUAL"
    action: "scaffold"
  
  - type: "EVENT"
    event: "VOICE_NOTE_UPLOADED"
    action: "process_voice_idea"

resources:
  file_system: true
  output_directory: "~/Projects/"
  template_directory: "~/.armlenquant/templates/"

dependencies:
  - openai
  - jinja2
  - pyyaml
  - markdown
```

## 9.2 Database Collections

### `project_ideas`

```javascript
{
  idea_id: "uuid",
  user_id: "user_ref",
  raw_input: "Original user input...",
  input_type: "TEXT" | "VOICE" | "IMAGE" | "STRUCTURED",
  processed_at: ISODate,
  analysis: {
    scope: "MEDIUM",
    complexity_score: 5.7,
    estimated_hours: 80,
    tech_stack_recommendation: {...}
  },
  status: "PROCESSING" | "SCAFFOLDED" | "IN_DEVELOPMENT" | "COMPLETED"
}
```

### `project_scaffolds`

```javascript
{
  scaffold_id: "uuid",
  idea_id: "ref:project_ideas",
  project_name: "HabitForge",
  project_path: "~/Projects/HabitForge",
  created_at: ISODate,
  structure: {
    directories: [...],
    files: [...],
    configs: [...],
    docs: [...]
  },
  cursor_integration: {
    cursorrules_path: "...",
    prompts_generated: 12
  }
}
```

### `project_templates`

```javascript
{
  template_id: "uuid",
  name: "SaaS Starter",
  description: "Full-featured SaaS boilerplate",
  stack: ["next.js", "supabase", "stripe"],
  structure: {...},
  variables: ["project_name", "description", "primary_color"],
  created_at: ISODate,
  usage_count: 47
}
```

## 9.3 System Prompt

```
You are the Ideas Machine, the project intelligence agent for Project ArmLenQuant.

Your mission: Transform raw ideas into structured, scaffolded projects ready for development.

CORE RULES:
1. CLARIFY before building — ask if intent is unclear
2. SCOPE realistically — don't over-promise
3. PHASE appropriately — MVP first, features later
4. DOCUMENT thoroughly — future you will thank you
5. INTEGRATE with Cursor — optimize for AI-assisted development

ANALYSIS PROCESS:
1. What is the user trying to build?
2. Who is it for?
3. What's the minimum viable version?
4. What tech stack fits best?
5. What are the risks/challenges?

OUTPUT STRUCTURE:
- Always create docs/ folder with specs
- Always create prompts/ folder for Cursor
- Always create .cursorrules
- Always scaffold src/ with basic structure

DOCUMENTATION STYLE:
- Clear, concise, actionable
- Use visual mockups (ASCII) where helpful
- Include code examples
- Reference other docs appropriately

PERSONALITY:
- Enthusiastic about ideas
- Pragmatic about scope
- Thorough in planning
- Efficient in execution
```

---

# 10. OUTPUT FORMATS

## 10.1 Scaffold Summary

```markdown
# PROJECT SCAFFOLDED: HabitForge

## Status: ✅ Complete

## Location
`~/Projects/HabitForge`

## Generated Structure

```
HabitForge/
├── docs/ (6 files)
│   ├── 00_MASTER_PLAN.md
│   ├── 01_PHASE_1_MVP.md
│   └── ...
├── prompts/ (5 files)
│   ├── CURSOR_COMMANDS.md
│   └── ...
├── src/ (scaffolded)
├── .cursorrules
├── package.json
└── README.md
```

## Project Analysis
- **Scope:** Medium (80 hours estimated)
- **Complexity:** 5.7/10
- **Tech Stack:** Next.js + Supabase + Tailwind

## Next Steps
1. Open in Cursor: `cursor ~/Projects/HabitForge`
2. Read: `docs/00_MASTER_PLAN.md`
3. Start with: `prompts/01_setup.md`

## Cursor Integration
- `.cursorrules` configured ✅
- 5 implementation prompts generated ✅
- Documentation linked ✅

[Open in Cursor] [View Docs] [View in Dashboard]
```

## 10.2 Dashboard Card

```json
{
  "type": "PROJECT_CARD",
  "priority": "MEDIUM",
  "project_name": "HabitForge",
  "status": "SCAFFOLDED",
  "scaffolded_at": "2025-12-02T14:30:00Z",
  "scope": "MEDIUM",
  "estimated_hours": 80,
  "tech_stack": ["Next.js", "Supabase", "Tailwind"],
  "path": "~/Projects/HabitForge",
  "docs_count": 6,
  "prompts_count": 5,
  "actions": ["OPEN_CURSOR", "VIEW_DOCS", "ARCHIVE"]
}
```

## 10.3 Activity Stream Event

```
🛠️ IDEAS MACHINE COMPLETE

Project "HabitForge" scaffolded successfully

• 6 documentation files generated
• 5 Cursor prompts ready
• Estimated scope: 80 hours

Ready to start development →
```

---

# APPENDIX: FUTURE ENHANCEMENTS

## Phase 2 Capabilities (Planned)

| Feature | Description |
|---------|-------------|
| **Voice Note Processing** | Transcribe and structure spoken ideas |
| **Wireframe Analysis** | Extract structure from sketched wireframes |
| **GitHub Integration** | Auto-create repo, push initial commit |
| **Dependency Updates** | Keep scaffolds current with latest versions |

## Phase 3 Capabilities (Future)

| Feature | Description |
|---------|-------------|
| **Multi-Project** | Manage related projects as a suite |
| **Template Marketplace** | Share and discover community templates |
| **Live Collab** | Real-time idea refinement with user |
| **Auto-Implementation** | Ideas Machine triggers Meta-Builder for code |

---

**END OF IDEAS MACHINE DOCUMENTATION**

*Agent Version: 2.0*  
*Last Updated: December 2025*

