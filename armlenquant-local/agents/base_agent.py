"""
Base Agent Class
All agents must inherit from this class.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, Awaitable
from datetime import datetime
from pathlib import Path
from loguru import logger
import asyncio
import traceback
import hashlib
import json

from agents.capability_manager import (
    CapabilityManager,
    CapabilityError,
    QuotaExceededError,
    default_capability_manager,
)
from models.capability import CapabilityGrant


class AgentResult:
    """Standardized agent execution result."""
    
    def __init__(
        self,
        success: bool,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        execution_time_ms: int = 0
    ):
        self.success = success
        self.data = data or {}
        self.error = error
        self.execution_time_ms = execution_time_ms
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp.isoformat()
        }


class BaseAgent(ABC):
    """
    Abstract base class for all ArmLenQuant agents.
    
    Every agent must implement:
    - execute(): Main execution logic
    - get_capabilities(): List of agent capabilities
    """
    
    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        capability_manager: Optional[CapabilityManager] = None,
    ):
        self.name = name
        self.version = version
        # Bind both agent and component for structured logging
        self.logger = logger.bind(agent=name, component=name)
        self._current_task_id: Optional[str] = None
        self._is_running: bool = False
        self._execution_cache: Dict[str, AgentResult] = {}
        self.capability_manager = capability_manager or default_capability_manager
        # Convenience alias to mirror docs
        self.capabilities = self.capability_manager
        # Register agent grants up front
        try:
            self.capability_manager.register_agent(
                self.name, self.get_capability_grants()
            )
        except Exception as exc:
            self.logger.warning(f"Capability registration skipped: {exc}")
    
    @property
    def agent_name(self) -> str:
        """Get agent name."""
        return self.name
    
    @abstractmethod
    async def execute(self, payload: Dict[str, Any]) -> AgentResult:
        """
        Execute the agent's main task.
        
        Args:
            payload: Task payload from the queue
            
        Returns:
            AgentResult with execution outcome
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> list:
        """
        Get list of agent capabilities.
        
        Returns:
            List of capability strings
        """
        pass

    def get_capability_grants(self) -> list[CapabilityGrant]:
        """Return capability grants for the sandbox (optional per-agent override)."""
        return []
    
    async def execute_step(self, workflow_step: Dict[str, Any]) -> AgentResult:
        """
        Execute a workflow step. Default implementation proxies to execute().
        """
        return await self.execute(workflow_step.get("inputs", {}))
    
    async def run(self, task_id: str, payload: Dict[str, Any]) -> AgentResult:
        """
        Run the agent with error handling and timing.
        
        Args:
            task_id: Task identifier
            payload: Task payload
            
        Returns:
            AgentResult
        """
        self._current_task_id = task_id
        self._is_running = True
        
        start_time = datetime.utcnow()
        self.logger.info(f"Starting task {task_id}")
        
        cache_key = self._get_execution_key(payload)
        cached_result = await self._check_previous_execution(cache_key)

        try:
            if cached_result:
                self.logger.info(f"Idempotency hit for task {task_id}")
                result = cached_result
            else:
                result = await self.execute(payload)
                if result.success:
                    await self._cache_execution_result(cache_key, result)
            
        except asyncio.CancelledError:
            self.logger.warning(f"Task {task_id} cancelled")
            result = AgentResult(
                success=False,
                error="Task cancelled"
            )
            
        except Exception as e:
            self.logger.error(f"Task {task_id} failed: {e}")
            self.logger.error(traceback.format_exc())
            result = AgentResult(
                success=False,
                error=str(e)
            )
        
        finally:
            self._is_running = False
            self._current_task_id = None
        
        # Calculate execution time
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        result.execution_time_ms = int(execution_time)
        
        self.logger.info(
            f"Task {task_id} completed: success={result.success}, "
            f"time={result.execution_time_ms}ms"
        )
        
        return result

    async def execute_with_capability(
        self,
        capability: str,
        action: Callable[..., Awaitable[Any]],
        policy_params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """Execute an action with sandbox enforcement."""
        try:
            return await self.capability_manager.execute_with_capability(
                self.name,
                capability,
                action,
                policy_params=policy_params,
                **kwargs,
            )
        except (CapabilityError, QuotaExceededError) as exc:
            self.logger.error(f"Capability blocked: {exc}")
            raise

    async def write_file_safe(self, path: str, content: str):
        """Write a file using the capability sandbox."""

        async def _write(path: str, content: str, **_: Any):
            def _sync_write():
                target = Path(path).expanduser()
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                return {"path": str(target), "size": len(content)}

            return await asyncio.to_thread(_sync_write)

        size_mb = len(content) / (1024 * 1024)
        extension = Path(path).suffix
        return await self.execute_with_capability(
            "file_write",
            _write,
            path=path,
            content=content,
            size_mb=size_mb,
            extension=extension,
        )
    
    @property
    def is_running(self) -> bool:
        """Check if agent is currently executing a task."""
        return self._is_running
    
    @property
    def current_task(self) -> Optional[str]:
        """Get current task ID if running."""
        return self._current_task_id
    
    def get_status(self) -> dict:
        """Get agent status."""
        return {
            "name": self.name,
            "version": self.version,
            "is_running": self._is_running,
            "current_task": self._current_task_id,
            "capabilities": self.get_capabilities()
        }

    def _get_execution_key(self, payload: Dict[str, Any]) -> str:
        """Generate a deterministic hash for idempotency."""
        try:
            blob = json.dumps(payload or {}, sort_keys=True, default=str)
        except Exception:
            blob = str(payload)
        return hashlib.sha256(blob.encode()).hexdigest()

    async def _check_previous_execution(self, key: str) -> Optional[AgentResult]:
        """Return cached result if we have executed this payload before."""
        return self._execution_cache.get(key)

    async def _cache_execution_result(self, key: str, result: AgentResult) -> None:
        """Cache successful execution result for idempotency."""
        self._execution_cache[key] = result
