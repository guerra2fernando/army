"""
Idea Analyzer
Extracts structure from raw ideas.
"""
from typing import Dict, Any
from loguru import logger
import json

from agents.llm_client import get_llm_client, LLMClient
from poller.config import get_settings
from .models import IdeaInput, IdeaAnalysis, ProjectSize, ProjectType

settings = get_settings()


class IdeaAnalyzer:
    """
    Analyzes and structures raw project ideas.
    """
    
    def __init__(self, llm_client: LLMClient = None):
        self.client = llm_client or get_llm_client()
        self.logger = logger.bind(component="analyzer")
    
    async def analyze(self, idea_input: IdeaInput) -> IdeaAnalysis:
        """
        Analyze a raw idea and extract structure.
        
        Args:
            idea_input: Raw idea from user
            
        Returns:
            Structured idea analysis
        """
        self.logger.info("Analyzing idea...")
        
        prompt = f"""Analyze this project idea and extract a structured specification.

**User's Idea:**
{idea_input.description}

**Reference URLs:** {', '.join(idea_input.reference_urls) if idea_input.reference_urls else 'None'}

**Constraints:** {json.dumps(idea_input.constraints) if idea_input.constraints else 'None'}

**Preferences:** {json.dumps(idea_input.preferences) if idea_input.preferences else 'None'}

Return a JSON object with this exact structure:
{{
    "title": "Project name (short, memorable)",
    "description": "One paragraph summary",
    "problem_statement": "What problem does this solve?",
    "target_user": "Who is this for?",
    "value_proposition": "Why would someone use this?",

    "project_type": "WEB_APP|API_SERVICE|CLI_TOOL|MOBILE_APP|CHROME_EXTENSION|DATA_PIPELINE|AI_APP",
    "project_size": "MICRO|SMALL|MEDIUM|LARGE",
    "estimated_hours": 80,

    "core_features": ["Feature 1", "Feature 2"],
    "mvp_features": ["MVP Feature 1", "MVP Feature 2"],
    "future_features": ["Future Feature 1", "Future Feature 2"],

    "risks": ["Risk 1", "Risk 2"],
    "assumptions": ["Assumption 1", "Assumption 2"]
}}

IMPORTANT:
- Return ONLY the JSON object, no additional text or explanation
- All string fields must be strings, all arrays must be arrays
- estimated_hours must be a number
- Do not wrap the JSON in a list or array

Be realistic about scope. Start with MVP mindset."""

        response = await self.client.chat(
            messages=[
                {"role": "system", "content": "You are a product strategist who helps structure project ideas. Always return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            json_response=True
        )
        
        result = response.json()

        # Handle case where LLM returns a list instead of dict
        if isinstance(result, list):
            self.logger.warning(f"LLM returned list instead of dict: {result}")
            if len(result) > 0 and isinstance(result[0], dict):
                result = result[0]  # Take first item if it's a list of dicts
            else:
                raise ValueError(f"LLM returned unexpected list format: {result}")

        if not isinstance(result, dict):
            raise ValueError(f"LLM returned non-dict result: {type(result)} - {result}")

        # Determine if this is a full-stack project
        project_type = ProjectType(result["project_type"])
        is_fullstack = self._detect_fullstack_project(project_type, result["description"], idea_input)

        return IdeaAnalysis(
            title=result["title"],
            description=result["description"],
            problem_statement=result["problem_statement"],
            target_user=result["target_user"],
            value_proposition=result["value_proposition"],
            project_type=project_type,
            project_size=ProjectSize(result["project_size"]),
            estimated_hours=result["estimated_hours"],
            is_fullstack=is_fullstack,
            core_features=result["core_features"],
            mvp_features=result["mvp_features"],
            future_features=result["future_features"],
            risks=result["risks"],
            assumptions=result["assumptions"]
        )
    
    def estimate_complexity(self, analysis: IdeaAnalysis) -> Dict[str, Any]:
        """Calculate complexity scores."""
        
        # Feature-based scoring
        feature_count = len(analysis.mvp_features)
        
        if feature_count <= 3:
            frontend_score = 3
        elif feature_count <= 6:
            frontend_score = 5
        else:
            frontend_score = 7
        
        # Type-based scoring
        type_complexity = {
            ProjectType.CLI_TOOL: 2,
            ProjectType.API_SERVICE: 4,
            ProjectType.WEB_APP: 5,
            ProjectType.CHROME_EXTENSION: 5,
            ProjectType.MOBILE_APP: 7,
            ProjectType.AI_APP: 7,
            ProjectType.DATA_PIPELINE: 6
        }
        
        # Handle both enum and string values
        project_type = analysis.project_type
        if isinstance(project_type, str):
            project_type = ProjectType(project_type)
        
        backend_score = type_complexity.get(project_type, 5)
        
        # Infrastructure based on size
        infra_scores = {
            ProjectSize.MICRO: 2,
            ProjectSize.SMALL: 3,
            ProjectSize.MEDIUM: 5,
            ProjectSize.LARGE: 7
        }
        
        # Handle both enum and string values
        project_size = analysis.project_size
        if isinstance(project_size, str):
            project_size = ProjectSize(project_size)
        
        infra_score = infra_scores.get(project_size, 4)
        
        overall = (frontend_score * 0.35 + backend_score * 0.40 + infra_score * 0.25)
        
        # Get classification as string
        classification = project_size if isinstance(project_size, str) else project_size.value
        
        return {
            "frontend": frontend_score,
            "backend": backend_score,
            "infrastructure": infra_score,
            "overall": round(overall, 1),
            "classification": classification
        }

    def _detect_fullstack_project(self, project_type: ProjectType, description: str, idea_input: IdeaInput) -> bool:
        """
        Detect if this is a full-stack project that needs both frontend and backend.

        Args:
            project_type: The classified project type
            description: Project description
            idea_input: Original idea input with constraints/preferences

        Returns:
            True if full-stack, False otherwise
        """
        # Explicit full-stack types
        explicit_fullstack_types = [
            ProjectType.WEB_APP,
            ProjectType.MOBILE_APP,
            ProjectType.AI_APP
        ]

        if project_type in explicit_fullstack_types:
            return True

        # Check for frontend/backend mentions in description
        description_lower = description.lower()
        has_frontend_indicators = any(word in description_lower for word in [
            'frontend', 'front-end', 'ui', 'interface', 'user interface', 'web app', 'website',
            'dashboard', 'react', 'vue', 'angular', 'next.js', 'nuxt', 'svelte'
        ])

        has_backend_indicators = any(word in description_lower for word in [
            'backend', 'back-end', 'api', 'database', 'server', 'authentication', 'auth',
            'data', 'storage', 'fastapi', 'flask', 'django', 'express', 'node.js'
        ])

        # If both frontend and backend indicators are present, it's full-stack
        if has_frontend_indicators and has_backend_indicators:
            return True

        # Check constraints and preferences for full-stack indicators
        all_text = ' '.join([
            description,
            ' '.join(idea_input.constraints.values()),
            ' '.join(idea_input.preferences.values())
        ]).lower()

        fullstack_keywords = [
            'full-stack', 'fullstack', 'frontend and backend', 'web application',
            'mobile app', 'user interface', 'api integration'
        ]

        if any(keyword in all_text for keyword in fullstack_keywords):
            return True

        return False

