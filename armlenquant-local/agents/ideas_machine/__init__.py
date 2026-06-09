"""
Ideas Machine Agent
Project scaffolding and development blueprint generator.
"""
from .agent import IdeasMachineAgent
from .analyzer import IdeaAnalyzer
from .architect import SystemArchitect
from .scaffolder import ProjectScaffolder
from .models import (
    ProjectSize,
    ProjectType,
    IdeaInput,
    IdeaAnalysis,
    TechStackRecommendation,
    ProjectArchitecture,
    ProjectScaffold,
    PhaseSpec
)

__all__ = [
    "IdeasMachineAgent",
    "IdeaAnalyzer",
    "SystemArchitect",
    "ProjectScaffolder",
    "ProjectSize",
    "ProjectType",
    "IdeaInput",
    "IdeaAnalysis",
    "TechStackRecommendation",
    "ProjectArchitecture",
    "ProjectScaffold",
    "PhaseSpec"
]
