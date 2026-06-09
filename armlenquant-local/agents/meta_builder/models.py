"""
Meta Builder Data Models
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class AgentLocation(str, Enum):
    """Agent deployment location."""
    CLOUD = "CLOUD"
    LOCAL = "LOCAL"


class TriggerType(str, Enum):
    """Agent trigger types."""
    CRON = "CRON"
    TASK_QUEUE = "TASK_QUEUE"
    EVENT = "EVENT"
    MANUAL = "MANUAL"


class AgentSpec(BaseModel):
    """
    Agent specification defining all aspects of a new agent.
    """
    name: str
    version: str = "1.0.0"
    description: str
    purpose: str
    
    location: AgentLocation
    trigger_type: TriggerType
    trigger_config: Optional[Dict[str, Any]] = None
    
    inputs: List[Dict[str, str]] = Field(default_factory=list)  # name, type, description
    outputs: List[Dict[str, str]] = Field(default_factory=list)  # name, type, description
    
    capabilities: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)  # Python packages
    
    actions: List[Dict[str, Any]] = Field(default_factory=list)  # action definitions
    
    system_prompt: Optional[str] = None


class GeneratedCode(BaseModel):
    """
    Generated code output containing all files for a new agent.
    """
    agent_file: str  # Main agent file content
    models_file: Optional[str] = None
    routes_file: Optional[str] = None
    init_file: str
    
    documentation: str
    test_file: Optional[str] = None


class AgentBuildResult(BaseModel):
    """
    Result of agent build process.
    """
    success: bool
    agent_name: str
    agent_path: str
    files_created: List[str]
    validation_passed: bool
    registration_id: Optional[str] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    """
    Result of spec validation.
    """
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    spec_summary: Optional[Dict[str, Any]] = None

