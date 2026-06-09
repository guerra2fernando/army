"""
Ideas Machine Data Models
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ProjectSize(str, Enum):
    """Project size classification."""
    MICRO = "MICRO"      # 1-3 days
    SMALL = "SMALL"      # 1-2 weeks
    MEDIUM = "MEDIUM"    # 1-2 months
    LARGE = "LARGE"      # 3-6 months


class ProjectType(str, Enum):
    """Project type classification."""
    WEB_APP = "WEB_APP"
    API_SERVICE = "API_SERVICE"
    CLI_TOOL = "CLI_TOOL"
    MOBILE_APP = "MOBILE_APP"
    CHROME_EXTENSION = "CHROME_EXTENSION"
    DATA_PIPELINE = "DATA_PIPELINE"
    AI_APP = "AI_APP"


class IdeaInput(BaseModel):
    """Raw idea input from user."""
    description: str
    reference_urls: List[str] = Field(default_factory=list)
    constraints: Dict[str, str] = Field(default_factory=dict)  # budget, timeline, etc.
    preferences: Dict[str, str] = Field(default_factory=dict)  # tech preferences


class IdeaAnalysis(BaseModel):
    """Analyzed and structured idea."""
    title: str
    description: str
    problem_statement: str
    target_user: str
    value_proposition: str

    project_type: ProjectType
    project_size: ProjectSize
    estimated_hours: int
    is_fullstack: bool = False

    core_features: List[str] = Field(default_factory=list)
    mvp_features: List[str] = Field(default_factory=list)
    future_features: List[str] = Field(default_factory=list)

    risks: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)

    class Config:
        use_enum_values = True


class TechStackRecommendation(BaseModel):
    """Recommended technology stack."""
    frontend: Dict[str, str] = Field(default_factory=dict)  # framework, styling, state, etc.
    backend: Dict[str, str] = Field(default_factory=dict)   # framework, database, auth, etc.
    infrastructure: Dict[str, str] = Field(default_factory=dict)  # hosting, ci_cd, monitoring
    
    reasoning: str = ""
    alternatives: List[Dict[str, str]] = Field(default_factory=list)


class ProjectArchitecture(BaseModel):
    """System architecture specification."""
    overview: str = ""
    components: List[Dict[str, str]] = Field(default_factory=list)
    data_flow: str = ""
    api_endpoints: List[Dict[str, str]] = Field(default_factory=list)
    data_models: List[Dict[str, str]] = Field(default_factory=list)
    
    diagrams: Dict[str, str] = Field(default_factory=dict)  # ASCII art diagrams


class ProjectScaffold(BaseModel):
    """Generated project scaffold."""
    project_name: str
    project_path: str
    
    directories: List[str] = Field(default_factory=list)
    files: List[Dict[str, str]] = Field(default_factory=list)  # path, content
    
    documentation: Dict[str, str] = Field(default_factory=dict)  # doc_name, content
    prompts: List[Dict[str, str]] = Field(default_factory=list)  # prompt files for Cursor
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PhaseTask(BaseModel):
    """Individual task within a development phase."""
    task_id: str
    description: str
    deliverables: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)  # task_ids this depends on
    test_requirements: List[str] = Field(default_factory=list)


class PhaseSpec(BaseModel):
    """Specification for a development phase."""
    phase_number: int
    phase_name: str
    goal: str
    duration: str

    features: List[str] = Field(default_factory=list)
    user_stories: List[str] = Field(default_factory=list)
    technical_tasks: List[str] = Field(default_factory=list)
    tasks: List[PhaseTask] = Field(default_factory=list)

    ui_mockups: Optional[str] = None  # ASCII art
    api_endpoints: List[Dict[str, str]] = Field(default_factory=list)
    database_changes: List[str] = Field(default_factory=list)

    success_criteria: List[str] = Field(default_factory=list)
    ai_prompt: str = ""
    test_commands: List[str] = Field(default_factory=list)


class PhaseExecutionResult(BaseModel):
    """Result of executing a development phase."""
    phase_id: str
    success: bool
    generated_files: List[str] = Field(default_factory=list)
    test_results: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    fixes_applied: List[Dict[str, Any]] = Field(default_factory=list)  # Applied fixes with success status


class ProjectContext(BaseModel):
    """Complete project context for AI prompts and knowledge base."""
    architecture: Dict[str, Any] = Field(default_factory=dict)
    models: List[Dict[str, Any]] = Field(default_factory=list)
    endpoints: List[Dict[str, Any]] = Field(default_factory=list)
    components: List[Dict[str, Any]] = Field(default_factory=list)
    test_coverage: Dict[str, Any] = Field(default_factory=dict)

