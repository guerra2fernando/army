"""ArmLenQuant Local Agents"""
from .base_agent import BaseAgent, AgentResult
from .llm_client import LLMClient, LLMProvider, LLMResponse, get_llm_client
from .job_hunter import JobHunterAgent
from .ideas_machine import IdeasMachineAgent
from .meta_builder import MetaBuilderAgent
from .crypto_sentinel import CryptoSentinelAgent

__all__ = [
    "BaseAgent",
    "AgentResult",
    "LLMClient",
    "LLMProvider",
    "LLMResponse",
    "get_llm_client",
    "JobHunterAgent",
    "IdeasMachineAgent",
    "MetaBuilderAgent",
    "CryptoSentinelAgent"
]

