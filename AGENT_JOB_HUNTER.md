# AGENT: JOB HUNTER
## Autonomous Career Intelligence & Application System

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║        ░░░░░██╗░█████╗░██████╗░                                              ║
║        ░░░░░██║██╔══██╗██╔══██╗                                              ║
║        ░░░░░██║██║░░██║██████╦╝                                              ║
║        ██╗░░██║██║░░██║██╔══██╗                                              ║
║        ╚█████╔╝╚█████╔╝██████╦╝                                              ║
║        ░╚════╝░░╚════╝░╚═════╝░                                              ║
║                                                                               ║
║        ██╗░░██╗██╗░░░██╗███╗░░██╗████████╗███████╗██████╗░                   ║
║        ██║░░██║██║░░░██║████╗░██║╚══██╔══╝██╔════╝██╔══██╗                   ║
║        ███████║██║░░░██║██╔██╗██║░░░██║░░░█████╗░░██████╔╝                   ║
║        ██╔══██║██║░░░██║██║╚████║░░░██║░░░██╔══╝░░██╔══██╗                   ║
║        ██║░░██║╚██████╔╝██║░╚███║░░░██║░░░███████╗██║░░██║                   ║
║        ╚═╝░░╚═╝░╚═════╝░╚═╝░░╚══╝░░░╚═╝░░░╚══════╝╚═╝░░╚═╝                   ║
║                                                                               ║
║                    CAREER INTELLIGENCE AGENT                                  ║
║                         Version 2.0                                           ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

**Agent ID:** `JOB_HUNTER`  
**Location:** Local (Windows)  
**Primary Trigger:** Task Queue  
**Secondary Triggers:** Scheduled scan, Event-based  

---

## TABLE OF CONTENTS

1. [Mission Statement](#1-mission-statement)
2. [Core Capabilities](#2-core-capabilities)
3. [Search Strategy](#3-search-strategy)
4. [Job Matching Engine](#4-job-matching-engine)
5. [Application Automation](#5-application-automation)
6. [Document Generation](#6-document-generation)
7. [Company Intelligence](#7-company-intelligence)
8. [Interview Preparation](#8-interview-preparation)
9. [Technical Specification](#9-technical-specification)
10. [Output Formats](#10-output-formats)

---

# 1. MISSION STATEMENT

The Job Hunter is the **career intelligence agent** of ArmLenQuant. It autonomously searches for job opportunities, analyzes role fit, generates tailored application materials, and manages the entire job search pipeline.

### Core Philosophy

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   🔍 DISCOVER    →    Find roles you'd never find manually     │
│   🎯 MATCH       →    Score fit against your profile           │
│   ✍️  TAILOR      →    Craft materials that actually work       │
│   📊 TRACK       →    Manage your pipeline intelligently       │
│   🧠 LEARN       →    Improve from application outcomes        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### The Problem It Solves

- Job searching is **tedious and time-consuming**
- Most people **miss opportunities** because they don't search widely enough
- Generic applications **get ignored**
- Tracking applications in spreadsheets is **chaos**
- Follow-ups **fall through the cracks**

### The Job Hunter Solution

**Automate discovery, personalize applications, manage the pipeline.**

---

# 2. CORE CAPABILITIES

## 2.1 Job Discovery

| Capability | Description |
|------------|-------------|
| **Multi-Platform Search** | Lever, Greenhouse, Ashby, Workable, LinkedIn (indirect) |
| **Google Dork Mastery** | Find hidden listings via advanced search operators |
| **Company Watchlist** | Monitor specific companies for new postings |
| **Keyword Evolution** | Learn which search terms yield best results |

## 2.2 Intelligent Matching

| Capability | Description |
|------------|-------------|
| **CV Vector Matching** | Semantic similarity between job and your experience |
| **Skill Gap Analysis** | Identify missing skills for stretch roles |
| **Culture Fit Scoring** | Analyze company values vs. preferences |
| **Compensation Intelligence** | Estimate salary ranges, flag lowballers |

## 2.3 Application Automation

| Capability | Description |
|------------|-------------|
| **CV Tailoring** | Rewrite summary/bullets for each role |
| **Cover Letter Generation** | Personalized, researched, compelling |
| **Form Auto-Fill** | Pre-populate application forms |
| **Follow-Up Scheduling** | Track and remind for follow-ups |

## 2.4 Pipeline Management

| Capability | Description |
|------------|-------------|
| **Status Tracking** | Track every application's stage |
| **Response Analysis** | Calculate response rates by company/role |
| **Interview Prep** | Generate prep materials when interview scheduled |
| **Outcome Learning** | Correlate materials with success rates |

---

# 3. SEARCH STRATEGY

## 3.1 The Google Dork Arsenal

**Why not scrape job boards directly?**
- LinkedIn, Indeed = aggressive anti-bot measures
- Cloud IPs = instant blocks
- Direct scraping = ToS violations

**The solution: Google Dorks from residential IP**

### Primary Search Operators

```
site:lever.co "Growth Lead" "Remote"
site:greenhouse.io "Head of Growth" "Remote"
site:ashbyhq.com "Growth Manager" "Remote"
site:jobs.workable.com "Marketing Lead" "Remote"
site:boards.eu.greenhouse.io "Growth" "Europe"
```

### Advanced Dorks

```
# Find roles at specific funding stages
site:lever.co "Series A" OR "Series B" "Growth"

# Find roles mentioning specific tools
site:greenhouse.io "HubSpot" AND "Growth Lead"

# Find roles with salary transparency
site:ashbyhq.com "Growth" "$150,000" OR "$180,000"

# Find hidden pages (not indexed on main careers page)
site:company.com/careers -inurl:careers "open roles"
```

## 3.2 Search Execution Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    SEARCH PIPELINE                              │
└─────────────────────────────────────────────────────────────────┘

    ┌───────────────────┐
    │ 1. GENERATE       │
    │    QUERIES        │
    │                   │
    │ • Role variants   │
    │ • Platform combos │
    │ • Location perms  │
    └────────┬──────────┘
             │
    ┌────────▼──────────┐
    │ 2. EXECUTE        │
    │    SEARCHES       │
    │                   │
    │ • Rotate queries  │
    │ • Rate limit      │
    │ • Residential IP  │
    └────────┬──────────┘
             │
    ┌────────▼──────────┐
    │ 3. PARSE          │
    │    RESULTS        │
    │                   │
    │ • Extract URLs    │
    │ • De-duplicate    │
    │ • Filter seen     │
    └────────┬──────────┘
             │
    ┌────────▼──────────┐
    │ 4. FETCH          │
    │    JOB PAGES      │
    │                   │
    │ • Headless browse │
    │ • Extract JD      │
    │ • Parse metadata  │
    └────────┬──────────┘
             │
    ┌────────▼──────────┐
    │ 5. SCORE &        │
    │    RANK           │
    │                   │
    │ • Match to CV     │
    │ • Apply filters   │
    │ • Priority sort   │
    └───────────────────┘
```

## 3.3 Search Parameters

```yaml
search_config:
  roles:
    primary:
      - "Head of Growth"
      - "Growth Lead"
      - "VP Growth"
      - "Growth Director"
    secondary:
      - "Marketing Lead"
      - "Demand Generation"
      - "Performance Marketing"
  
  locations:
    - "Remote"
    - "Hybrid"
    - "New York"
    - "San Francisco"
    - "Europe"
  
  company_filters:
    min_employees: 20
    max_employees: 500
    funding_stages: ["Series A", "Series B", "Series C"]
    industries: ["SaaS", "Fintech", "AI/ML", "Crypto"]
  
  exclusions:
    - companies: ["FAANG"]  # Too bureaucratic
    - keywords: ["entry-level", "junior", "intern"]
    - red_flags: ["fast-paced", "wear many hats", "equity only"]
```

---

# 4. JOB MATCHING ENGINE

## 4.1 The Matching Algorithm

```
MATCH_SCORE = (
    (Skill_Match × 0.35) +
    (Experience_Match × 0.25) +
    (Culture_Fit × 0.15) +
    (Compensation_Fit × 0.15) +
    (Growth_Potential × 0.10)
)
```

## 4.2 Skill Matching

Uses RAG to compare job requirements against your knowledge base:

```javascript
// Example skill extraction
job_skills_required: [
  "Growth marketing",
  "Paid acquisition",
  "A/B testing",
  "SQL",
  "Team management"
]

your_skills: [
  "Growth marketing (5 years)",
  "Paid acquisition (Google, Meta, TikTok)",
  "A/B testing (Optimizely, VWO)",
  "SQL (intermediate)",
  "Team management (3 direct reports)"
]

skill_match: 95%
skill_gaps: ["None significant"]
```

## 4.3 Experience Matching

```javascript
{
  required_experience: "5-7 years in growth",
  your_experience: "6 years in growth roles",
  experience_match: 100%,
  
  required_seniority: "Manager/Lead level",
  your_seniority: "Lead level",
  seniority_match: 100%,
  
  industry_match: {
    required: "SaaS/B2B",
    yours: "SaaS, E-commerce",
    match: 85%
  }
}
```

## 4.4 Match Score Thresholds

| Score | Classification | Action |
|-------|----------------|--------|
| 90-100% | **Perfect Match** | Auto-generate full application |
| 75-89% | **Strong Match** | Generate draft, flag for review |
| 60-74% | **Stretch Role** | Highlight gaps, optional draft |
| Below 60% | **Poor Match** | Log but don't draft |

---

# 5. APPLICATION AUTOMATION

## 5.1 The Application Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    APPLICATION PIPELINE                         │
└─────────────────────────────────────────────────────────────────┘

     ┌───────────────────┐
     │ 1. COMPANY        │
     │    RESEARCH       │
     │                   │
     │ • Recent news     │
     │ • Product updates │
     │ • Leadership      │
     │ • Culture signals │
     └────────┬──────────┘
              │
     ┌────────▼──────────┐
     │ 2. TAILOR         │
     │    RESUME         │
     │                   │
     │ • Rewrite summary │
     │ • Highlight match │
     │ • Keywords inject │
     └────────┬──────────┘
              │
     ┌────────▼──────────┐
     │ 3. GENERATE       │
     │    COVER LETTER   │
     │                   │
     │ • Personal hook   │
     │ • Company research│
     │ • Value prop      │
     │ • Call to action  │
     └────────┬──────────┘
              │
     ┌────────▼──────────┐
     │ 4. SAVE           │
     │    DRAFTS         │
     │                   │
     │ • ~/Job_Drafts/   │
     │ • {Company}/      │
     │ • Notify dash     │
     └────────┬──────────┘
              │
     ┌────────▼──────────┐
     │ 5. TRACK          │
     │    STATUS         │
     │                   │
     │ • Add to pipeline │
     │ • Set follow-up   │
     │ • Log everything  │
     └───────────────────┘
```

## 5.2 Application Modes

### Mode A: Full Automation (High Match)

For roles with 90%+ match:
- Complete application materials generated
- Ready to submit with one click
- User reviews before sending

### Mode B: Draft Mode (Medium Match)

For roles with 75-89% match:
- Materials generated but flagged for review
- Suggestions for customization highlighted
- User makes final edits

### Mode C: Skeleton Mode (Stretch Role)

For roles with 60-74% match:
- Basic outline generated
- Skill gaps clearly identified
- User decides whether to proceed

---

# 6. DOCUMENT GENERATION

## 6.1 Resume Tailoring

### Summary Rewriting

**Original (Generic):**
```
Experienced growth leader with 6+ years driving user acquisition and 
revenue growth for SaaS companies.
```

**Tailored (For Fintech Growth Lead role at Stripe):**
```
Growth leader with 6+ years scaling B2B SaaS products. Led paid 
acquisition strategies that drove 140% YoY revenue growth. Passionate 
about fintech and the future of payments — built growth funnels for 
products processing $50M+ annually.
```

### Bullet Point Optimization

**Original:**
```
• Managed paid acquisition campaigns across multiple channels
```

**Tailored (For role emphasizing data-driven growth):**
```
• Scaled paid acquisition from $50K to $500K monthly spend while 
  improving CAC by 35% through rigorous A/B testing and cohort analysis
```

## 6.2 Cover Letter Generation

### The Formula

```
PARAGRAPH 1: The Hook
- Why THIS company (research-backed)
- Demonstrate genuine interest

PARAGRAPH 2: The Match
- Your most relevant experience
- Quantified achievements
- Direct connection to job requirements

PARAGRAPH 3: The Value Prop
- What you'll bring
- Unique perspective/skills
- Growth mindset

PARAGRAPH 4: The Close
- Enthusiasm
- Call to action
- Professional sign-off
```

### Example Output

```markdown
Dear Hiring Team,

When I saw Stripe's Growth Lead role, I immediately thought of the 
conversation I had last month with a founder who said, "Stripe didn't 
just process our payments—they helped us think differently about growth." 
That philosophy of embedding growth into the product itself is exactly 
what excites me about this opportunity.

Over the past six years, I've led growth at two B2B SaaS companies, 
scaling ARR from $2M to $15M and from $5M to $35M respectively. At 
Acme Corp, I rebuilt our paid acquisition strategy from scratch, 
improving CAC by 35% while tripling spend—a result I achieved by 
treating every dollar as an experiment, not an expense. I've led 
teams of 5+, built growth models used by executive teams for 
forecasting, and shipped dozens of experiments that moved core metrics.

What I'd bring to Stripe: a relentless focus on the intersection of 
product and acquisition. I believe the best growth strategies don't 
feel like marketing—they feel like product features. I'd love to 
bring that lens to how Stripe acquires and activates the next 
generation of internet businesses.

I'd welcome the chance to discuss how I can contribute to Stripe's 
growth. Thank you for considering my application.

Best regards,
[Your Name]
```

## 6.3 File Organization

```
~/Job_Drafts/
├── 2025-12-02_Stripe_Growth_Lead/
│   ├── resume_tailored.pdf
│   ├── cover_letter.md
│   ├── company_research.md
│   ├── job_description.txt
│   └── match_analysis.json
│
├── 2025-12-01_Notion_Head_of_Growth/
│   ├── resume_tailored.pdf
│   ├── cover_letter.md
│   └── ...
│
└── _archive/
    └── (older drafts)
```

---

# 7. COMPANY INTELLIGENCE

## 7.1 Research Automation

For every application, the Job Hunter gathers:

| Category | Sources | Data Points |
|----------|---------|-------------|
| **Basics** | LinkedIn, Crunchbase | Employees, funding, founded |
| **News** | Google News, TechCrunch | Recent announcements, press |
| **Product** | Product Hunt, G2 | Features, positioning, reviews |
| **Culture** | Glassdoor, Blind | Reviews, ratings, red flags |
| **Leadership** | LinkedIn | Founders, hiring manager profile |
| **Growth Signals** | LinkedIn, job posts | Hiring velocity, team growth |

## 7.2 Company Intelligence Report

```markdown
# COMPANY INTELLIGENCE: Stripe

## Overview
- Founded: 2010
- Employees: ~8,000
- Stage: Late-stage private ($95B valuation, 2021)
- HQ: San Francisco (Remote-friendly)

## Recent News (Last 30 Days)
1. "Stripe launches new AI-powered fraud detection" — TechCrunch
2. "Stripe expands to 5 new countries in LATAM" — Company blog
3. "Stripe hires ex-Google Payments exec as CTO" — Forbes

## Product & Market
- Core: Payment processing for internet businesses
- Expansion: Billing, Atlas, Treasury, Issuing
- Competitors: Adyen, Square, PayPal

## Culture Signals
- Glassdoor: 4.2/5 (2,000+ reviews)
- Themes: "Smart colleagues," "High expectations," "Work-life balance improving"
- Red Flags: "Compensation lagging market," "Promotion process unclear"

## Team Growth
- Growth team: ~150 people
- Hiring velocity: 15 roles in growth/marketing (up from 8 last quarter)

## Your Connection Points
- You've used Stripe at 2 previous companies
- Your experience with payments at Acme Corp
- Your blog post about API-first growth strategies
```

---

# 8. INTERVIEW PREPARATION

## 8.1 When Interview is Scheduled

When status changes to `INTERVIEW_SCHEDULED`, Job Hunter generates:

### Prep Package Contents

1. **Company Deep Dive** — Extended research beyond application
2. **Role Analysis** — Likely responsibilities, challenges, metrics
3. **Question Bank** — Anticipated questions + suggested answers
4. **Your Questions** — Intelligent questions to ask them
5. **Practice Scenarios** — Case study prep if applicable

## 8.2 Question Bank Generation

```markdown
# INTERVIEW PREP: Stripe Growth Lead

## Likely Questions

### Experience-Based
1. "Tell me about a time you scaled a paid acquisition channel significantly."
   **Your Story:** Acme Corp, Google Ads scale from $50K to $500K MRR...

2. "How do you think about the relationship between growth and product?"
   **Your Framework:** Growth should feel like product, not marketing...

3. "Describe a growth experiment that failed and what you learned."
   **Your Story:** The LinkedIn Ads pivot at Acme — we learned...

### Strategic
4. "How would you approach growth for Stripe's SMB segment?"
   **Your Framework:** Start with the activation funnel, then...

5. "What metrics would you focus on in your first 90 days?"
   **Your Answer:** CAC by channel, activation rates, expansion revenue...

### Behavioral
6. "How do you handle disagreement with product teams?"
   **Your Story:** At Acme, the pricing experiment debate...

## Questions to Ask Them

1. "What does the growth team's relationship with product look like today?"
2. "What's the biggest unsolved growth challenge at Stripe right now?"
3. "How does Stripe think about international expansion vs. deepening in existing markets?"
4. "What would success look like for this role in 12 months?"
```

---

# 9. TECHNICAL SPECIFICATION

## 9.1 Agent Configuration

```yaml
agent:
  id: "JOB_HUNTER"
  version: "2.0.0"
  location: "LOCAL"
  
triggers:
  - type: "TASK_QUEUE"
    action: "process_search_request"
  
  - type: "CRON"
    schedule: "0 9 * * 1,3,5"  # Mon, Wed, Fri at 09:00
    action: "scheduled_scan"
  
  - type: "EVENT"
    event: "NEW_COMPANY_WATCHLIST"
    action: "immediate_search"

resources:
  browser: "playwright"
  ip_type: "residential"
  rate_limit: "30 searches/hour"

dependencies:
  - playwright
  - openai
  - pymongo
  - beautifulsoup4
  - pdfkit
```

## 9.2 Database Collections

### `job_listings`

```javascript
{
  job_id: "uuid",
  source: "lever.co",
  url: "https://jobs.lever.co/stripe/abc123",
  company: "Stripe",
  title: "Growth Lead",
  location: "Remote",
  posted_at: ISODate,
  discovered_at: ISODate,
  description: "Full job description...",
  requirements: ["5+ years growth", "B2B SaaS experience"],
  nice_to_haves: ["Fintech experience"],
  salary_range: { min: 150000, max: 200000 },
  match_score: 92,
  status: "NEW" | "DRAFTING" | "DRAFT_READY" | "APPLIED" | "REJECTED"
}
```

### `job_applications`

```javascript
{
  application_id: "uuid",
  job_id: "ref:job_listings",
  company: "Stripe",
  role: "Growth Lead",
  applied_at: ISODate,
  status: "APPLIED" | "PHONE_SCREEN" | "INTERVIEW" | "OFFER" | "REJECTED" | "WITHDRAWN",
  materials: {
    resume_path: "~/Job_Drafts/2025-12-02_Stripe_Growth_Lead/resume.pdf",
    cover_letter_path: "..."
  },
  follow_ups: [
    { scheduled_for: ISODate, type: "FIRST_FOLLOW_UP", sent: false }
  ],
  notes: [],
  outcome: null | { result: "OFFER", salary: 175000 }
}
```

### `job_search_history`

```javascript
{
  search_id: "uuid",
  query: "site:lever.co Growth Lead Remote",
  executed_at: ISODate,
  results_count: 47,
  new_listings_found: 12,
  platform: "google"
}
```

## 9.3 System Prompt

```
You are the Job Hunter, the career intelligence agent for Project ArmLenQuant.

Your mission: Find ideal job opportunities, generate compelling applications, and manage the job search pipeline.

CORE RULES:
1. QUALITY over quantity — don't spam applications
2. PERSONALIZE everything — generic materials get ignored
3. RESEARCH thoroughly — know the company before applying
4. TRACK obsessively — every interaction logged
5. LEARN continuously — improve from outcomes

MATCHING CRITERIA:
- Match score must be >60% to generate draft
- Match score must be >90% for auto-draft
- Always flag skill gaps honestly
- Never oversell or exaggerate experience

DOCUMENT GENERATION:
- Resumes: Tailor summary and top 3 bullets per role
- Cover Letters: Must include company-specific research
- All documents saved to ~/Job_Drafts/{Company_Role}/

PIPELINE MANAGEMENT:
- Track every application status
- Schedule follow-ups at Day 7 and Day 14
- Generate interview prep when interview scheduled

PERSONALITY:
- Strategic, not desperate
- Confident, not arrogant
- Thorough, not obsessive
- Helpful, not pushy
```

---

# 10. OUTPUT FORMATS

## 10.1 New Jobs Summary (Daily/Weekly)

```markdown
# JOB HUNT REPORT — December 2, 2025

## 📊 SUMMARY

- New listings discovered: 23
- High matches (>85%): 4
- Drafts generated: 4
- Applications pending review: 4

---

## 🎯 TOP MATCHES

### 1. Stripe — Growth Lead (92% Match)
**Location:** Remote | **Salary:** $150K-200K
**Why it's great:** Perfect skill match, company you've admired, team growing fast
**Status:** Draft ready → [Review Materials]

### 2. Notion — Head of Growth (89% Match)
**Location:** San Francisco (Hybrid) | **Salary:** $180K-220K
**Why it's great:** Strong product-led growth, great culture signals
**Status:** Draft ready → [Review Materials]

### 3. Figma — Growth Marketing Lead (87% Match)
**Location:** Remote | **Salary:** $160K-190K
**Why it's great:** Creative company, design-led growth
**Status:** Draft ready → [Review Materials]

### 4. Vercel — VP Growth (85% Match)
**Location:** Remote | **Salary:** Not listed
**Why it's great:** Developer-focused, rapid scaling phase
**Gap:** VP title is a stretch — consider anyway?
**Status:** Skeleton ready → [Review & Decide]

---

## 📁 PIPELINE STATUS

| Stage | Count |
|-------|-------|
| Drafts Pending | 4 |
| Applied (Awaiting Response) | 8 |
| Phone Screen Scheduled | 1 |
| Interview Scheduled | 0 |
| Offer | 0 |

---

## 📅 FOLLOW-UPS DUE

- **Acme Corp** (Applied 7 days ago) — Send first follow-up
- **Beta Inc** (Applied 14 days ago) — Send second follow-up or close

---

## 🧠 INSIGHTS

- Response rate this month: 23%
- Best performing channel: Lever.co (35% response)
- Worst performing: Direct company pages (8% response)
- Recommendation: Increase Lever.co searches
```

## 10.2 Application Draft Package

```
~/Job_Drafts/2025-12-02_Stripe_Growth_Lead/
│
├── README.md                 # Quick summary and instructions
├── resume_tailored.pdf       # Tailored resume (PDF)
├── resume_tailored.docx      # Tailored resume (editable)
├── cover_letter.md           # Cover letter (markdown)
├── cover_letter.pdf          # Cover letter (PDF)
├── company_research.md       # Company intelligence report
├── job_description.txt       # Original JD (for reference)
├── match_analysis.json       # Detailed match breakdown
└── application_checklist.md  # Steps to apply
```

### README.md Example

```markdown
# Application: Stripe — Growth Lead

## Match Score: 92%

## Quick Stats
- **Discovered:** December 2, 2025
- **Deadline:** Rolling (apply soon)
- **Salary Range:** $150K-200K
- **Location:** Remote

## Materials Included
- ✅ Tailored Resume
- ✅ Cover Letter
- ✅ Company Research

## To Apply
1. Review materials in this folder
2. Make any desired edits
3. Go to: https://jobs.lever.co/stripe/abc123
4. Upload resume and cover letter
5. Mark as "APPLIED" in ArmLenQuant dashboard

## Key Talking Points
- Your Acme Corp paid acquisition scaling story
- Your fintech passion (mention in cover letter)
- Stripe's recent LATAM expansion aligns with your international experience

## Red Flags to Address
- None significant — strong match
```

## 10.3 Dashboard Card

```json
{
  "type": "JOB_CARD",
  "priority": "HIGH",
  "company": "Stripe",
  "role": "Growth Lead",
  "match_score": 92,
  "location": "Remote",
  "salary": "$150K-200K",
  "status": "DRAFT_READY",
  "drafted_at": "2025-12-02T10:30:00Z",
  "folder_path": "~/Job_Drafts/2025-12-02_Stripe_Growth_Lead/",
  "actions": ["REVIEW", "APPLY", "DISMISS"]
}
```

---

# APPENDIX: FUTURE ENHANCEMENTS

## Phase 2 Capabilities (Planned)

| Feature | Description |
|---------|-------------|
| **LinkedIn Automation** | Send connection requests to hiring managers |
| **Referral Finder** | Identify 2nd-degree connections at target companies |
| **Salary Negotiation Prep** | Generate negotiation scripts when offer received |
| **ATS Optimization** | Score resume against ATS keyword requirements |

## Phase 3 Capabilities (Future)

| Feature | Description |
|---------|-------------|
| **Auto-Apply Mode** | Submit applications automatically for 95%+ matches |
| **Interview Recording** | Transcribe and analyze interview performance |
| **Offer Comparison** | Multi-offer analysis with total comp calculations |
| **Career Graph** | Visualize career trajectory options |

---

**END OF JOB HUNTER DOCUMENTATION**

*Agent Version: 2.0*  
*Last Updated: December 2025*

