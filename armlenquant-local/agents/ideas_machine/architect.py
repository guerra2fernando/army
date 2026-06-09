"""
System Architect
Designs technical architecture for projects.
"""
from typing import Dict, List, Optional
from loguru import logger
import json

from agents.llm_client import get_llm_client, LLMClient
from poller.config import get_settings
from .models import IdeaAnalysis, TechStackRecommendation, ProjectArchitecture, ProjectType

settings = get_settings()


class SystemArchitect:
    """
    Designs system architecture and tech stack.
    """
    
    # Tech stack presets by project type
    STACK_PRESETS = {
        ProjectType.WEB_APP: {
            "frontend": {
                "framework": "Next.js 14",
                "styling": "Tailwind CSS + Shadcn UI",
                "state": "Zustand",
                "forms": "React Hook Form + Zod"
            },
            "backend": {
                "api": "Next.js API Routes",
                "database": "Supabase (PostgreSQL)",
                "auth": "Supabase Auth",
                "storage": "Supabase Storage"
            },
            "infrastructure": {
                "hosting": "Vercel",
                "ci_cd": "GitHub Actions",
                "monitoring": "Vercel Analytics"
            }
        },
        ProjectType.API_SERVICE: {
            "backend": {
                "framework": "FastAPI",
                "database": "PostgreSQL",
                "auth": "JWT",
                "cache": "Redis"
            },
            "infrastructure": {
                "hosting": "Railway / DigitalOcean",
                "ci_cd": "GitHub Actions",
                "monitoring": "Sentry"
            }
        },
        ProjectType.CLI_TOOL: {
            "backend": {
                "language": "Python",
                "framework": "Typer",
                "ui": "Rich",
                "config": "Pydantic"
            },
            "infrastructure": {
                "distribution": "PyPI",
                "ci_cd": "GitHub Actions"
            }
        },
        ProjectType.AI_APP: {
            "frontend": {
                "framework": "Next.js 14",
                "styling": "Tailwind CSS",
                "state": "Zustand"
            },
            "backend": {
                "framework": "FastAPI",
                "database": "PostgreSQL + pgvector",
                "llm": "OpenAI API",
                "embeddings": "text-embedding-3-small"
            },
            "infrastructure": {
                "hosting": "Railway / Vercel",
                "ci_cd": "GitHub Actions"
            }
        },
        ProjectType.CHROME_EXTENSION: {
            "frontend": {
                "framework": "React + Vite",
                "styling": "Tailwind CSS",
                "manifest": "V3"
            },
            "backend": {
                "storage": "Chrome Storage API",
                "messaging": "Chrome Messaging"
            },
            "infrastructure": {
                "distribution": "Chrome Web Store",
                "ci_cd": "GitHub Actions"
            }
        },
        ProjectType.DATA_PIPELINE: {
            "backend": {
                "language": "Python",
                "orchestration": "Apache Airflow / Prefect",
                "processing": "Pandas / Polars",
                "storage": "S3 / GCS"
            },
            "infrastructure": {
                "hosting": "AWS / GCP",
                "ci_cd": "GitHub Actions",
                "monitoring": "Datadog"
            }
        },
        ProjectType.MOBILE_APP: {
            "frontend": {
                "framework": "React Native / Expo",
                "styling": "NativeWind",
                "state": "Zustand"
            },
            "backend": {
                "api": "Supabase / Firebase",
                "database": "PostgreSQL / Firestore",
                "auth": "Supabase Auth / Firebase Auth"
            },
            "infrastructure": {
                "distribution": "App Store / Play Store",
                "ci_cd": "EAS Build"
            }
        }
    }
    
    def __init__(self, llm_client: LLMClient = None):
        self.client = llm_client or get_llm_client()
        self.logger = logger.bind(component="architect")
    
    async def recommend_tech_stack(
        self,
        analysis: IdeaAnalysis,
        preferences: Optional[Dict[str, str]] = None
    ) -> TechStackRecommendation:
        """
        Recommend optimal tech stack for the project, respecting user preferences.
        """
        self.logger.info(f"Recommending tech stack for {analysis.project_type}")

        # Handle both enum and string values
        project_type = analysis.project_type
        if isinstance(project_type, str):
            project_type = ProjectType(project_type)

        # Extract explicit preferences from description and preferences dict
        explicit_prefs = self._extract_explicit_preferences(analysis.description, preferences or {})

        # Get preset if available
        preset = self.STACK_PRESETS.get(project_type, {})
        
        # Ask AI to customize/validate
        preferences_str = ""
        if preferences:
            preferences_str = f"\n**User Preferences:**\n{chr(10).join('- ' + f'{k}: {v}' for k, v in preferences.items())}"

        # Build preferences string
        preferences_str = ""
        if explicit_prefs:
            preferences_str = f"\n\n**EXPLICIT USER PREFERENCES (MUST BE RESPECTED):**\n{chr(10).join('- ' + f'{k}: {v}' for k, v in explicit_prefs.items())}"

        prompt = f"""Recommend a tech stack for this project:

**Project:** {analysis.title}
**Type:** {analysis.project_type if isinstance(analysis.project_type, str) else analysis.project_type.value}
**Size:** {analysis.project_size if isinstance(analysis.project_size, str) else analysis.project_size.value}
**Estimated Hours:** {analysis.estimated_hours}

**Core Features:**
{chr(10).join('- ' + f for f in analysis.core_features)}{preferences_str}

**Default Preset:**
{json.dumps(preset, indent=2)}

CRITICAL: If explicit user preferences are provided above, you MUST use them as the primary choice over any preset defaults. Only use presets as fallback for unspecified technologies.

Return a JSON object with EXACTLY this structure:
{{
    "frontend": {{
        "framework": "Next.js",
        "styling": "Tailwind CSS - Shadcn UI",
        "state": "Zustand",
        "forms": "React Hook Form + Zod"
    }},
    "backend": {{
        "framework": "FastAPI",
        "database": "MongoDB",
        "auth": "JWT",
        "cache": "Redis",
        "testing": "Pytest",
        "deployment": "Docker",
    }},
    "infrastructure": {{
        "hosting": "DigitalOcean",
        "ci_cd": "GitHub Actions",

    }},
    "reasoning": "One sentence explanation of why this stack was chosen",
    "alternatives": [
        {{
            "name": "Alternative Stack Name",
            "description": "Why this would be a good alternative"
        }}
    ]
}}

IMPORTANT:
- reasoning must be a STRING, not an object
- alternatives must be an ARRAY of objects, not a single object
- frontend, backend, infrastructure must be objects with technology key-value pairs
"""

        response = await self.client.chat(
            messages=[
                {"role": "system", "content": "You are a senior software architect. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            json_response=True
        )
        
        result = response.json()

        # Handle case where LLM returns a list instead of dict
        if isinstance(result, list):
            self.logger.warning(f"LLM returned list instead of dict for tech stack: {result}")
            if len(result) > 0 and isinstance(result[0], dict):
                result = result[0]  # Take first item if it's a list of dicts
            else:
                raise ValueError(f"LLM returned unexpected list format for tech stack: {result}")

        if not isinstance(result, dict):
            raise ValueError(f"LLM returned non-dict result for tech stack: {type(result)} - {result}")

        # Extract and validate fields with fallbacks
        frontend = result.get("frontend", {})
        backend = result.get("backend", {})
        infrastructure = result.get("infrastructure", {})

        # Handle case where reasoning is returned as a dict instead of string
        reasoning = result.get("reasoning", "Standard stack for this project type")
        if isinstance(reasoning, dict):
            reasoning = f"Custom stack with {', '.join(reasoning.keys())}"
        elif not isinstance(reasoning, str):
            reasoning = str(reasoning)

        # Handle case where alternatives is returned as a dict instead of list
        alternatives = result.get("alternatives", [])
        if isinstance(alternatives, dict):
            alternatives = [{"name": "Alternative Stack", "description": "Alternative technology choices"}]
        elif not isinstance(alternatives, list):
            alternatives = []

        # Ensure we have valid tech stack data
        if not frontend and preset.get("frontend"):
            frontend = preset["frontend"]
        if not backend and preset.get("backend"):
            backend = preset["backend"]
        if not infrastructure and preset.get("infrastructure"):
            infrastructure = preset["infrastructure"]

        return TechStackRecommendation(
            frontend=frontend,
            backend=backend,
            infrastructure=infrastructure,
            reasoning=reasoning,
            alternatives=alternatives
        )
    
    def _determine_scope(self, analysis: IdeaAnalysis) -> str:
        """
        Determine project scope based on analysis and explicit user requirements.

        Returns:
            "FRONTEND", "BACKEND", or "FULLSTACK"
        """
        description_lower = analysis.description.lower()
        project_type = analysis.project_type.value.lower() if hasattr(analysis.project_type, 'value') else str(analysis.project_type).lower()

        # Check for explicit mentions of both frontend and backend technologies
        frontend_keywords = ["frontend", "nextjs", "react", "vue", "angular", "svelte", "ui", "interface", "client", "web app", "spa"]
        backend_keywords = ["backend", "api", "fastapi", "flask", "django", "express", "spring", "database", "mongodb", "postgresql", "server", "python", "nodejs"]

        has_frontend = any(keyword in description_lower for keyword in frontend_keywords)
        has_backend = any(keyword in description_lower for keyword in backend_keywords)

        # If both frontend and backend are mentioned explicitly, it's FULLSTACK
        if has_frontend and has_backend:
            return "FULLSTACK"

        # Check for explicit frontend-only indicators
        frontend_indicators = ["frontend", "spa", "mobile_app", "chrome_extension"]
        if project_type in frontend_indicators or any(word in description_lower for word in ["frontend only", "client-side", "ui only", "interface only"]):
            return "FRONTEND"

        # Check for explicit backend-only indicators
        backend_indicators = ["api", "backend", "microservice", "data_pipeline", "cli_tool"]
        if project_type in backend_indicators or any(word in description_lower for word in ["backend only", "api only", "server-side", "data only"]):
            return "BACKEND"

        # Default to fullstack for web_app and ai_app types
        if project_type in ["web_app", "ai_app"]:
            return "FULLSTACK"

        # If only frontend keywords found, assume frontend-only
        if has_frontend and not has_backend:
            return "FRONTEND"

        # If only backend keywords found, assume backend-only
        if has_backend and not has_frontend:
            return "BACKEND"

        # Default fallback
        return "FULLSTACK"

    def _extract_explicit_preferences(self, description: str, preferences: Dict[str, str]) -> Dict[str, str]:
        """
        Extract explicit technology preferences from user description and preferences dict.

        Args:
            description: User project description
            preferences: Additional preferences dict

        Returns:
            Dict of explicit preferences found
        """
        explicit = {}
        description_lower = description.lower()

        # Merge preferences dict with description analysis
        all_prefs = {**preferences}

        # Extract database preferences
        if 'mongodb' in description_lower or preferences.get('database') == 'mongodb':
            explicit['database'] = 'mongodb'
        elif 'postgresql' in description_lower or 'postgres' in description_lower or preferences.get('database') == 'postgresql':
            explicit['database'] = 'postgresql'
        elif 'mysql' in description_lower or preferences.get('database') == 'mysql':
            explicit['database'] = 'mysql'
        elif 'sqlite' in description_lower or preferences.get('database') == 'sqlite':
            explicit['database'] = 'sqlite'

        # Extract backend framework preferences
        if 'fastapi' in description_lower or preferences.get('backend_framework') == 'fastapi':
            explicit['backend_framework'] = 'fastapi'
        elif 'flask' in description_lower or preferences.get('backend_framework') == 'flask':
            explicit['backend_framework'] = 'flask'
        elif 'django' in description_lower or preferences.get('backend_framework') == 'django':
            explicit['backend_framework'] = 'django'
        elif 'express' in description_lower or preferences.get('backend_framework') == 'express':
            explicit['backend_framework'] = 'express'
        elif 'spring' in description_lower or preferences.get('backend_framework') == 'spring':
            explicit['backend_framework'] = 'spring'

        # Extract frontend framework preferences
        if 'nextjs' in description_lower or 'next.js' in description_lower or preferences.get('frontend_framework') == 'nextjs':
            explicit['frontend_framework'] = 'nextjs'
        elif 'react' in description_lower and 'next' not in description_lower or preferences.get('frontend_framework') == 'react':
            explicit['frontend_framework'] = 'react'
        elif 'vue' in description_lower or preferences.get('frontend_framework') == 'vue':
            explicit['frontend_framework'] = 'vue'
        elif 'angular' in description_lower or preferences.get('frontend_framework') == 'angular':
            explicit['frontend_framework'] = 'angular'
        elif 'svelte' in description_lower or preferences.get('frontend_framework') == 'svelte':
            explicit['frontend_framework'] = 'svelte'

        # Extract language preferences
        if 'python' in description_lower or preferences.get('language') == 'python':
            explicit['language'] = 'python'
        elif 'javascript' in description_lower or 'js' in description_lower or preferences.get('language') == 'javascript':
            explicit['language'] = 'javascript'
        elif 'typescript' in description_lower or 'ts' in description_lower or preferences.get('language') == 'typescript':
            explicit['language'] = 'typescript'
        elif 'java' in description_lower or preferences.get('language') == 'java':
            explicit['language'] = 'java'

        return explicit

    async def _design_frontend_only(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation
    ) -> ProjectArchitecture:
        """Design architecture for frontend-only projects."""
        self.logger.info("Designing frontend-only architecture...")

        prompt = f"""Design a frontend-only application architecture:

**Project:** {analysis.title}
**Description:** {analysis.description}

**Tech Stack:**
- Frontend: {json.dumps(tech_stack.frontend)}
- External Services: {json.dumps(tech_stack.infrastructure)}

**MVP Features:**
{chr(10).join('- ' + f for f in analysis.mvp_features)}

**Scope:** This is a FRONTEND-ONLY project. Focus on UI/UX, state management, and external API integration.

Return a JSON object with EXACTLY this structure:
{{
    "overview": "Frontend-only architecture description focusing on UI and external integrations",
    "components": [
        {{"name": "Component Name", "purpose": "What it does", "technology": "Tech used"}}
    ],
    "data_flow": "Description of how data flows from external APIs to UI components",
    "api_endpoints": [
        {{"method": "GET/POST/etc", "path": "/api/...", "description": "External API endpoints the frontend will call"}}
    ],
    "data_models": [
        {{"name": "ModelName", "fields": "UI state and external data fields", "relationships": "UI state relationships"}}
    ]
}}

IMPORTANT: Focus on frontend architecture, external API integration, and UI state management.
"""

        response = await self.client.chat(
            messages=[
                {"role": "system", "content": "You are a senior frontend architect. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            json_response=True
        )

        result = response.json()
        return self._process_architecture_result(result, analysis, tech_stack)

    async def _design_backend_only(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation
    ) -> ProjectArchitecture:
        """Design architecture for backend-only projects."""
        self.logger.info("Designing backend-only architecture...")

        prompt = f"""Design a backend-only API service architecture:

**Project:** {analysis.title}
**Description:** {analysis.description}

**Tech Stack:**
- Backend: {json.dumps(tech_stack.backend)}
- Infrastructure: {json.dumps(tech_stack.infrastructure)}

**MVP Features:**
{chr(10).join('- ' + f for f in analysis.mvp_features)}

**Scope:** This is a BACKEND-ONLY project. Focus on API design, data processing, and server-side logic.

Return a JSON object with EXACTLY this structure:
{{
    "overview": "Backend-only architecture description focusing on API services and data processing",
    "components": [
        {{"name": "Component Name", "purpose": "What it does", "technology": "Tech used"}}
    ],
    "data_flow": "Description of how data flows through the backend services and processing pipeline",
    "api_endpoints": [
        {{"method": "GET/POST/etc", "path": "/api/...", "description": "API endpoints the backend will expose"}}
    ],
    "data_models": [
        {{"name": "ModelName", "fields": "Database fields and API data structures", "relationships": "Database relationships and API schemas"}}
    ]
}}

IMPORTANT: Focus on backend services, API design, data models, and server-side processing.
"""

        response = await self.client.chat(
            messages=[
                {"role": "system", "content": "You are a senior backend architect. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            json_response=True
        )

        result = response.json()
        return self._process_architecture_result(result, analysis, tech_stack)

    async def _design_fullstack(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation
    ) -> ProjectArchitecture:
        """Design architecture for full-stack projects."""
        self.logger.info("Designing full-stack architecture...")

        prompt = f"""Design a complete full-stack application architecture:

**Project:** {analysis.title}
**Description:** {analysis.description}

**Tech Stack:**
- Frontend: {json.dumps(tech_stack.frontend)}
- Backend: {json.dumps(tech_stack.backend)}
- Infrastructure: {json.dumps(tech_stack.infrastructure)}

**MVP Features:**
{chr(10).join('- ' + f for f in analysis.mvp_features)}

**Scope:** This is a FULL-STACK project requiring both frontend and backend components.

Return a JSON object with EXACTLY this structure:
{{
    "overview": "Complete full-stack architecture description with frontend, backend, and data layers",
    "components": [
        {{"name": "Component Name", "purpose": "What it does", "technology": "Tech used"}}
    ],
    "data_flow": "Description of how data flows from frontend through backend to database and back",
    "api_endpoints": [
        {{"method": "GET/POST/etc", "path": "/api/...", "description": "API endpoints for frontend-backend communication"}}
    ],
    "data_models": [
        {{"name": "ModelName", "fields": "Database fields, API schemas, and frontend state", "relationships": "All relationships across the full stack"}}
    ]
}}

IMPORTANT: Design a complete architecture covering frontend UI, backend API, database, and their interactions.
"""

        response = await self.client.chat(
            messages=[
                {"role": "system", "content": "You are a senior full-stack architect. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            json_response=True
        )

        result = response.json()
        return self._process_architecture_result(result, analysis, tech_stack)

    def _process_architecture_result(
        self,
        result: dict,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation
    ) -> ProjectArchitecture:
        """Process and validate architecture result from LLM."""
        # Handle case where LLM returns a list instead of dict
        if isinstance(result, list):
            self.logger.warning(f"LLM returned list instead of dict for architecture: {result}")
            if len(result) > 0 and isinstance(result[0], dict):
                result = result[0]  # Take first item if it's a list of dicts
            else:
                raise ValueError(f"LLM returned unexpected list format for architecture: {result}")

        if not isinstance(result, dict):
            raise ValueError(f"LLM returned non-dict result for architecture: {type(result)} - {result}")

        # Generate ASCII diagrams
        diagrams = {
            "system_diagram": self._generate_system_diagram(analysis, tech_stack),
            "data_flow": self._generate_data_flow_diagram(result.get("data_flow", ""))
        }

        # Extract and validate fields with fallbacks
        overview = result.get("overview", "")
        if not isinstance(overview, str):
            overview = str(overview)

        data_flow = result.get("data_flow", "")
        if not isinstance(data_flow, str):
            data_flow = str(data_flow)

        components = result.get("components", [])
        if not isinstance(components, list):
            components = []

        api_endpoints = result.get("api_endpoints", [])
        if not isinstance(api_endpoints, list):
            api_endpoints = []

        data_models = result.get("data_models", [])
        if not isinstance(data_models, list):
            data_models = []

        return ProjectArchitecture(
            overview=overview,
            components=components,
            data_flow=data_flow,
            api_endpoints=api_endpoints,
            data_models=data_models,
            diagrams=diagrams
        )

    async def design_architecture(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation
    ) -> ProjectArchitecture:
        """
        Design system architecture based on project scope.
        """
        self.logger.info("Designing architecture...")

        # Determine project scope and use appropriate design method
        scope = self._determine_scope(analysis)
        self.logger.info(f"Project scope determined: {scope}")

        if scope == "FRONTEND":
            return await self._design_frontend_only(analysis, tech_stack)
        elif scope == "BACKEND":
            return await self._design_backend_only(analysis, tech_stack)
        else:  # FULLSTACK
            return await self._design_fullstack(analysis, tech_stack)
    
    def _generate_system_diagram(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation
    ) -> str:
        """Generate ASCII system diagram based on project scope."""

        scope = self._determine_scope(analysis)
        title = analysis.title.upper()[:40]

        if scope == "FRONTEND":
            return self._generate_frontend_diagram(analysis, tech_stack, title)
        elif scope == "BACKEND":
            return self._generate_backend_diagram(analysis, tech_stack, title)
        else:  # FULLSTACK
            return self._generate_fullstack_diagram(analysis, tech_stack, title)

    def _generate_frontend_diagram(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation,
        title: str
    ) -> str:
        """Generate diagram for frontend-only projects."""

        frontend = tech_stack.frontend.get("framework", "Frontend")
        frontend_display = frontend[:15] if frontend else "Frontend"

        return f"""
┌─────────────────────────────────────────────────────────────────┐
│                    {title:^40}│
│                  (Frontend Only)                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────────┐                                              │
│   │    Client    │                                              │
│   │   (Browser)  │                                              │
│   └──────┬───────┘                                              │
│          │                                                       │
│          ▼                                                       │
│   ┌─────────────────┐                                            │
│   │  {frontend_display:^15}  │                                            │
│   │   (Frontend)    │                                            │
│   └──────┬──────────┘                                            │
│          │                                                       │
│          ▼                                                       │
│   ┌─────────────────┐                                            │
│   │ External APIs   │                                            │
│   │ (Third Party)   │                                            │
│   └─────────────────┘                                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
"""

    def _generate_backend_diagram(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation,
        title: str
    ) -> str:
        """Generate diagram for backend-only projects."""

        backend = tech_stack.backend.get("framework", tech_stack.backend.get("api", "Backend"))
        db = tech_stack.backend.get("database", "Database")
        backend_display = backend[:12] if backend else "Backend"
        db_display = db[:12] if db else "Database"

        return f"""
┌─────────────────────────────────────────────────────────────────┐
│                    {title:^40}│
│                  (Backend Only)                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────────┐                                              │
│   │   Clients    │                                              │
│   │ (API Calls)  │                                              │
│   └──────┬───────┘                                              │
│          │                                                       │
│          ▼                                                       │
│   ┌──────────────┐       ┌──────────────┐                       │
│   │   {backend_display:^12}   │ ◄───► │  {db_display:^12}  │                       │
│   │   (Backend)  │       │  (Database)  │                       │
│   └──────────────┘       └──────────────┘                       │
│                                                                 │
│   ┌──────────────┐                                              │
│   │   Response   │                                              │
│   │   (JSON)     │                                              │
│   └──────────────┘                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
"""

    def _generate_fullstack_diagram(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation,
        title: str
    ) -> str:
        """Generate diagram for full-stack projects."""

        frontend = tech_stack.frontend.get("framework", "Frontend")
        backend = tech_stack.backend.get("framework", tech_stack.backend.get("api", "Backend"))
        db = tech_stack.backend.get("database", "Database")

        # Truncate for display
        frontend_display = frontend[:12] if frontend else "Frontend"
        backend_display = backend[:12] if backend else "Backend"
        db_display = db[:12] if db else "Database"

        return f"""
┌─────────────────────────────────────────────────────────────────┐
│                    {title:^40}│
│                   (Full Stack)                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────────┐                                              │
│   │    Client    │                                              │
│   │   (Browser)  │                                              │
│   └──────┬───────┘                                              │
│          │                                                       │
│          ▼                                                       │
│   ┌──────────────┐       ┌──────────────┐                       │
│   │   {frontend_display:^12}   │ ◄───► │   {backend_display:^12}   │                       │
│   │  (Frontend)  │       │   (API)     │                       │
│   └──────────────┘       └──────┬───────┘                       │
│                                 │                                │
│                                 ▼                                │
│                         ┌──────────────┐                        │
│                         │  {db_display:^12}  │                        │
│                         │  (Database)  │                        │
│                         └──────────────┘                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
"""
    
    def _generate_data_flow_diagram(self, data_flow: str) -> str:
        """Generate data flow diagram."""
        # Truncate data flow description
        data_flow_short = data_flow[:60] if data_flow else "Standard request/response flow"
        
        return f"""
┌─────────────────────────────────────────────────────────────────┐
│                       DATA FLOW                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   User Action  ──►  Frontend  ──►  API  ──►  Database          │
│                                                                 │
│   Response  ◄──  Frontend  ◄──  API  ◄──  Database             │
│                                                                 │
│   {data_flow_short}...                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
"""

