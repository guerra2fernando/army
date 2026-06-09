"""
Prompt Generator
Creates AI-optimized prompts with RAG context integration.
"""
import json
from typing import Dict, Any, Optional, List
from loguru import logger

from agents.llm_client import get_llm_client, LLMClient
from .models import (
    IdeaAnalysis, TechStackRecommendation, ProjectArchitecture,
    ProjectContext, PhaseSpec
)


class PromptGenerator:
    """
    Generates AI prompts with full project context and RAG augmentation.
    """

    def __init__(self, llm_client: LLMClient = None):
        self.client = llm_client or get_llm_client()
        self.logger = logger.bind(component="prompt_generator")

    async def generate_phase_prompt(
        self,
        phase: PhaseSpec,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation,
        architecture: ProjectArchitecture,
        context: ProjectContext,
        rag_context: Optional[str] = None
    ) -> str:
        """
        Generate AI prompt for a development phase with full context.

        Args:
            phase: Phase specification
            analysis: Project analysis
            tech_stack: Tech stack recommendation
            architecture: System architecture
            context: Current project context
            rag_context: Additional context from knowledge base

        Returns:
            Complete AI prompt
        """
        # Get relevant context for this phase
        relevant_context = self._get_relevant_context_for_phase(context, phase)

        # Get similar successful templates for guidance
        similar_templates = []
        try:
            from .context_manager import ContextManager
            context_mgr = ContextManager()
            similar_templates = await context_mgr.get_similar_templates(analysis, tech_stack, limit=2)
        except Exception as e:
            self.logger.warning(f"Could not retrieve similar templates: {e}")

        # Build comprehensive prompt
        prompt_parts = [
            self._generate_system_context(analysis, tech_stack),
            self._generate_project_overview(analysis, architecture),
            self._generate_tech_stack_context(tech_stack),
            self._generate_architecture_context(architecture, context),
            self._generate_phase_requirements(phase),
        ]

        if similar_templates:
            prompt_parts.append(self._generate_template_guidance(similar_templates))

        if rag_context:
            prompt_parts.append(self._generate_rag_context(rag_context))

        if relevant_context:
            prompt_parts.append(self._generate_existing_code_context(relevant_context))

        prompt_parts.append(self._generate_output_instructions(phase))

        return "\n\n".join(prompt_parts)

    def _generate_system_context(self, analysis: IdeaAnalysis, tech_stack: TechStackRecommendation) -> str:
        """Generate system context for AI."""
        return f"""# PROJECT CONTEXT

**Project Name:** {analysis.title}
**Description:** {analysis.description}
**Type:** {analysis.project_type.value if hasattr(analysis.project_type, 'value') else analysis.project_type}
**Size:** {analysis.project_size.value if hasattr(analysis.project_size, 'value') else analysis.project_size}
**Full-Stack:** {"Yes" if analysis.is_fullstack else "No"}

**Tech Stack Overview:**
- Frontend: {tech_stack.frontend.get('framework', 'Not specified')}
- Backend: {tech_stack.backend.get('framework', 'Not specified')}
- Database: {tech_stack.backend.get('database', 'Not specified')}
- Infrastructure: {tech_stack.infrastructure.get('hosting', 'Not specified')}

**Problem Statement:** {analysis.problem_statement}
**Target Users:** {analysis.target_user}
**Value Proposition:** {analysis.value_proposition}

**Core Features:**
{chr(10).join(f"- {feature}" for feature in analysis.core_features)}

**MVP Features:**
{chr(10).join(f"- {feature}" for feature in analysis.mvp_features)}
"""

    def _generate_project_overview(self, analysis: IdeaAnalysis, architecture: ProjectArchitecture) -> str:
        """Generate project overview section."""
        return f"""# PROJECT OVERVIEW

**Architecture Overview:**
{architecture.overview}

**Data Flow:**
{architecture.data_flow}

**System Components:**
{chr(10).join(f"- {comp.get('name', 'Unknown')}: {comp.get('purpose', 'Unknown purpose')}" for comp in architecture.components)}

**Key Data Models:**
{chr(10).join(f"- {model.get('name', 'Unknown')}: {model.get('fields', 'No fields specified')}" for model in architecture.data_models)}
"""

    def _generate_tech_stack_context(self, tech_stack: TechStackRecommendation) -> str:
        """Generate detailed tech stack context."""
        return f"""# TECH STACK DETAILS

## Frontend
{chr(10).join(f"**{k}:** {v}" for k, v in tech_stack.frontend.items())}

## Backend
{chr(10).join(f"**{k}:** {v}" for k, v in tech_stack.backend.items())}

## Infrastructure
{chr(10).join(f"**{k}:** {v}" for k, v in tech_stack.infrastructure.items())}

## Reasoning
{tech_stack.reasoning}

## Alternatives Considered
{chr(10).join(f"- {alt.get('name', 'Unknown')}: {alt.get('description', 'No description')}" for alt in tech_stack.alternatives)}
"""

    def _generate_architecture_context(self, architecture: ProjectArchitecture, context: ProjectContext) -> str:
        """Generate architecture and current implementation context."""
        api_endpoints = "\n".join(
            f"- `{endpoint.get('method', 'GET')} {endpoint.get('path', '/unknown')}`: {endpoint.get('description', 'No description')}"
            for endpoint in context.endpoints
        )

        data_models = "\n".join(
            f"- **{model.get('name', 'Unknown')}**: {model.get('fields', 'No fields')} | Relations: {model.get('relationships', 'None')}"
            for model in context.models
        )

        components = "\n".join(
            f"- {comp}" for comp in context.components
        ) if context.components else "No components implemented yet"

        return f"""# CURRENT ARCHITECTURE & IMPLEMENTATION

## API Endpoints (Defined)
{api_endpoints}

## Data Models (Schema)
{data_models}

## Components Implemented
{components}

## Test Coverage
{json.dumps(context.test_coverage, indent=2) if context.test_coverage else "No tests executed yet"}

## Architecture Diagrams
```
{architecture.diagrams.get('system_diagram', 'No diagram available')}
```

```
{architecture.diagrams.get('data_flow', 'No diagram available')}
```
"""

    def _generate_phase_requirements(self, phase: PhaseSpec) -> str:
        """Generate phase-specific requirements."""
        tasks = "\n".join(
            f"- **{task.task_id}**: {task.description}\n  - Deliverables: {', '.join(task.deliverables)}\n  - Dependencies: {', '.join(task.dependencies) if task.dependencies else 'None'}\n  - Tests: {', '.join(task.test_requirements)}"
            for task in phase.tasks
        ) if phase.tasks else "No specific tasks defined"

        ui_mockup = f"```\n{phase.ui_mockups}\n```" if phase.ui_mockups else "No UI mockups provided"

        api_endpoints = "\n".join(
            f"- `{endpoint.get('method', 'GET')} {endpoint.get('path', '/unknown')}`: {endpoint.get('description', 'No description')}"
            for endpoint in phase.api_endpoints
        ) if phase.api_endpoints else "No API endpoints required for this phase"

        return f"""# PHASE REQUIREMENTS

## Phase: {phase.phase_name}
**Goal:** {phase.goal}
**Duration:** {phase.duration}

## Features to Implement
{chr(10).join(f"- {feature}" for feature in phase.features)}

## User Stories
{chr(10).join(f"- {story}" for feature in phase.user_stories)}

## Technical Tasks
{tasks}

## UI Mockups
{ui_mockup}

## API Endpoints
{api_endpoints}

## Database Changes
{chr(10).join(f"- {change}" for change in phase.database_changes)}

## Success Criteria
{chr(10).join(f"- [ ] {criterion}" for criterion in phase.success_criteria)}

## Test Commands
{chr(10).join(f"- {command}" for command in phase.test_commands)}
"""

    def _generate_rag_context(self, rag_context: str) -> str:
        """Generate RAG-augmented context section."""
        return f"""# KNOWLEDGE BASE CONTEXT

The following relevant information was retrieved from the knowledge base:

{rag_context}

Use this context to inform your implementation decisions and ensure consistency with existing patterns.
"""

    def _generate_existing_code_context(self, relevant_context: Dict[str, Any]) -> str:
        """Generate context from existing implemented code."""
        endpoints = relevant_context.get('endpoints', [])
        models = relevant_context.get('models', [])
        components = relevant_context.get('components', [])

        context_parts = []

        if endpoints:
            context_parts.append("## Relevant API Endpoints\n" + "\n".join(
                f"- `{ep.get('method', 'GET')} {ep.get('path', '/unknown')}`: {ep.get('description', 'No description')}"
                for ep in endpoints
            ))

        if models:
            context_parts.append("## Related Data Models\n" + "\n".join(
                f"- **{model.get('name', 'Unknown')}**: {model.get('fields', 'No fields')}"
                for model in models
            ))

        if components:
            context_parts.append("## Existing Components\n" + "\n".join(
                f"- {comp}" for comp in components
            ))

        return "\n\n".join(context_parts) if context_parts else ""

    def _generate_output_instructions(self, phase: PhaseSpec) -> str:
        """Generate output format instructions."""
        return f"""# OUTPUT INSTRUCTIONS

Generate complete, production-ready code for the **{phase.phase_name}** phase. Return a JSON object where each key is a file path and each value is the complete file content.

## Requirements
- **NO placeholders** - Every file must be complete and runnable
- **Production-ready** - Include proper error handling, validation, and logging
- **Well-tested** - Code should pass all specified test requirements
- **Type-safe** - Use proper TypeScript types and Python type hints
- **Documented** - Include docstrings and comments
- **Consistent** - Follow the established tech stack and patterns

## File Structure
- Use relative paths from project root
- Follow the established folder structure
- Include proper `__init__.py` files for Python packages
- Use kebab-case for file names, PascalCase for component names

## Code Quality Standards
- **Frontend**: Functional components, TypeScript strict mode, proper error boundaries
- **Backend**: Async/await patterns, Pydantic validation, proper HTTP status codes
- **Database**: Proper indexes, constraints, relationships, migrations
- **Testing**: Comprehensive unit tests, integration tests, proper mocking
- **Security**: Input validation, authentication checks, secure defaults

## Example Output Format
```json
{{
  "src/components/Button.tsx": "import React from 'react';\\n\\nexport const Button = () => <button>Click me</button>;",
  "src/components/Button.test.tsx": "import {{ render, screen }} from '@testing-library/react';\\n\\ntest('renders button', () => {{ render(<Button />); expect(screen.getByText('Click me')).toBeInTheDocument(); }});",
  "app/routes/users.py": "from fastapi import APIRouter\\n\\nrouter = APIRouter()\\n\\n@router.get('/')\\nasync def get_users():\\n    return {{'users': []}}"
}}
```

## Important
- Return **only** the JSON object, no additional text or explanation
- Ensure all generated code follows the project's established conventions
- Include all necessary imports and dependencies
- Generate both implementation files and comprehensive tests
- Make sure the code integrates properly with existing architecture
"""

    def _get_relevant_context_for_phase(self, context: ProjectContext, phase: PhaseSpec) -> Dict[str, Any]:
        """
        Get context most relevant to the current phase.

        Args:
            context: Current project context
            phase: Phase being executed

        Returns:
            Filtered context dictionary
        """
        relevant_endpoints = []
        relevant_models = []
        relevant_components = []

        # Filter endpoints relevant to this phase
        phase_endpoints = set()
        for endpoint in phase.api_endpoints:
            path = endpoint.get('path', '').strip('/')
            if path:
                phase_endpoints.add(path.split('/')[0])  # Get resource name

        for endpoint in context.endpoints:
            path = endpoint.get('path', '').strip('/')
            if path and path.split('/')[0] in phase_endpoints:
                relevant_endpoints.append(endpoint)

        # Filter models relevant to this phase
        phase_models = set()
        for change in phase.database_changes:
            # Extract model names from database changes
            change_lower = change.lower()
            for model in context.models:
                model_name = model.get('name', '').lower()
                if model_name in change_lower:
                    phase_models.add(model['name'])

        for model in context.models:
            if model.get('name') in phase_models:
                relevant_models.append(model)

        # Include all current components (they might be relevant)
        relevant_components = context.components[:5]  # Limit to recent components

        return {
            'endpoints': relevant_endpoints,
            'models': relevant_models,
            'components': relevant_components
        }

    async def generate_cursor_prompts(
        self,
        phase: PhaseSpec,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation,
        architecture: ProjectArchitecture,
        context: ProjectContext
    ) -> Dict[str, str]:
        """
        Generate Cursor AI prompts for manual implementation.

        Args:
            phase: Phase specification
            analysis: Project analysis
            tech_stack: Tech stack
            architecture: Architecture
            context: Project context

        Returns:
            Dictionary of prompt files
        """
        prompts = {}

        # Generate main commands file
        prompts["prompts/CURSOR_COMMANDS.md"] = self._generate_cursor_commands(phase, analysis, tech_stack)

        # Generate individual phase prompts
        if phase.tasks:
            for task in phase.tasks:
                prompts[f"prompts/{task.task_id}.md"] = self._generate_task_prompt(
                    task, phase, analysis, tech_stack, architecture, context
                )

        return prompts

    def _generate_cursor_commands(self, phase: PhaseSpec, analysis: IdeaAnalysis, tech_stack: TechStackRecommendation) -> str:
        """Generate main Cursor commands file."""
        return f"""# Cursor Commands for {analysis.title} - {phase.phase_name}

Use these prompts with Cursor AI to implement {phase.phase_name}.

## Quick Start
1. Read `docs/00_MASTER_PLAN.md` for project overview
2. Read `docs/{phase.phase_number:02d}_PHASE_{phase.phase_name.upper().replace(' ', '_')}.md` for phase specs
3. Read `PROJECT_CONTEXT.md` for current implementation status
4. Start with the prompts below in order

## Implementation Prompts
{chr(10).join(f"### {task.task_id.replace('_', ' ').title()}{chr(10)}@Cursor: Read prompts/{task.task_id}.md and implement the requirements.{chr(10)}" for task in phase.tasks)}

## Tech Stack
- **Frontend:** {tech_stack.frontend.get('framework', 'Not specified')}
- **Backend:** {tech_stack.backend.get('framework', 'Not specified')}
- **Database:** {tech_stack.backend.get('database', 'Not specified')}

## Testing
After implementation, run: {', '.join(phase.test_commands)}

## Validation
Ensure all success criteria are met:
{chr(10).join(f"- [ ] {criterion}" for criterion in phase.success_criteria)}
"""

    def _generate_task_prompt(
        self,
        task: Any,
        phase: PhaseSpec,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation,
        architecture: ProjectArchitecture,
        context: ProjectContext
    ) -> str:
        """Generate individual task prompt."""
        return f"""# {task.task_id.replace('_', ' ').title()}

## Context
**Project:** {analysis.title}
**Phase:** {phase.phase_name}
**Task:** {task.description}

## Requirements
**Deliverables:**
{chr(10).join(f"- {deliverable}" for deliverable in task.deliverables)}

**Dependencies:**
{chr(10).join(f"- {dep}" for dep in task.dependencies) if task.dependencies else "None"}

**Tests Required:**
{chr(10).join(f"- {test}" for test in task.test_requirements)}

## Tech Stack
{chr(10).join(f"- **{k}:** {v}" for k, v in tech_stack.frontend.items())}
{chr(10).join(f"- **{k}:** {v}" for k, v in tech_stack.backend.items())}

## Implementation Instructions
1. Read PROJECT_CONTEXT.md for current status
2. Implement the required functionality
3. Add comprehensive tests
4. Ensure proper error handling
5. Follow established patterns and conventions

## Success Criteria
{chr(10).join(f"- [ ] {criterion}" for criterion in phase.success_criteria)}
"""

    def _generate_template_guidance(self, templates: List[Dict[str, Any]]) -> str:
        """Generate guidance from similar successful templates."""
        if not templates:
            return ""

        template_guidance = ["# LESSONS FROM SIMILAR SUCCESSFUL PROJECTS"]

        for i, template in enumerate(templates, 1):
            metadata = template.get("metadata", {})
            template_guidance.append(f"""
## Template {i}: {template.get('title', 'Unknown')}

**Tech Stack That Worked:**
- Frontend: {', '.join(metadata.get('tech_stack', {}).get('frontend', {}).values())}
- Backend: {', '.join(metadata.get('tech_stack', {}).get('backend', {}).values())}
- Infrastructure: {', '.join(metadata.get('tech_stack', {}).get('infrastructure', {}).values())}

**Key Success Patterns:**
{json.dumps(metadata.get('success_patterns', {}), indent=2)}

**Project Size:** {metadata.get('project_size', 'Unknown')}
**Estimated Hours:** {metadata.get('estimated_hours', 'Unknown')}
**Full-Stack:** {'Yes' if metadata.get('is_fullstack') else 'No'}
""")

        template_guidance.append("""
**Guidance:** These similar projects succeeded with the approaches shown above.
Consider adapting these proven patterns to ensure your implementation follows
best practices established by successful projects.
""")

        return "\n".join(template_guidance)
