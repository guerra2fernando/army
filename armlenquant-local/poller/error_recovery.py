"""
Agent Error Recovery System
Phase 10: Integration & Polish
"""
from typing import Dict, Optional
from datetime import datetime
from loguru import logger


class ErrorRecovery:
    """
    Handles agent error recovery and failure tracking.
    
    Tracks consecutive failures per agent and determines when
    to stop retrying based on configurable thresholds.
    """
    
    def __init__(self, max_consecutive_failures: int = 3):
        """
        Initialize error recovery system.
        
        Args:
            max_consecutive_failures: Maximum failures before stopping retries
        """
        self.MAX_CONSECUTIVE_FAILURES = max_consecutive_failures
        self.failure_counts: Dict[str, int] = {}
        self.last_errors: Dict[str, str] = {}
        self.last_failure_times: Dict[str, datetime] = {}
        self.logger = logger.bind(component="error_recovery")
    
    def record_failure(self, agent_type: str, error: str) -> None:
        """
        Record an agent failure.
        
        Args:
            agent_type: The type of agent that failed (e.g., "JOB_HUNTER")
            error: The error message
        """
        current_count = self.failure_counts.get(agent_type, 0)
        self.failure_counts[agent_type] = current_count + 1
        self.last_errors[agent_type] = error
        self.last_failure_times[agent_type] = datetime.utcnow()
        
        self.logger.warning(
            f"Agent {agent_type} failure recorded: {error} "
            f"(count: {self.failure_counts[agent_type]})"
        )
        
        if self.failure_counts[agent_type] >= self.MAX_CONSECUTIVE_FAILURES:
            self.logger.warning(
                f"Agent {agent_type} has failed {self.MAX_CONSECUTIVE_FAILURES} times consecutively. "
                "Consider investigating the issue."
            )
    
    def record_success(self, agent_type: str) -> None:
        """
        Record a successful execution, resetting the failure count.
        
        Args:
            agent_type: The type of agent that succeeded
        """
        if agent_type in self.failure_counts and self.failure_counts[agent_type] > 0:
            self.logger.info(
                f"Agent {agent_type} succeeded after {self.failure_counts[agent_type]} failures. "
                "Resetting failure count."
            )
        
        self.failure_counts[agent_type] = 0
        self.last_errors.pop(agent_type, None)
        self.last_failure_times.pop(agent_type, None)
    
    def should_retry(self, agent_type: str) -> bool:
        """
        Check if we should retry for this agent.
        
        Args:
            agent_type: The type of agent to check
            
        Returns:
            True if retry is allowed, False if max failures reached
        """
        return self.failure_counts.get(agent_type, 0) < self.MAX_CONSECUTIVE_FAILURES
    
    def get_failure_count(self, agent_type: str) -> int:
        """
        Get the current failure count for an agent.
        
        Args:
            agent_type: The type of agent
            
        Returns:
            Current consecutive failure count
        """
        return self.failure_counts.get(agent_type, 0)
    
    def get_last_error(self, agent_type: str) -> Optional[str]:
        """
        Get the last error message for an agent.
        
        Args:
            agent_type: The type of agent
            
        Returns:
            Last error message or None
        """
        return self.last_errors.get(agent_type)
    
    def get_status(self) -> Dict:
        """
        Get overall status of all tracked agents.
        
        Returns:
            Dictionary with status information for all agents
        """
        return {
            agent_type: {
                "failure_count": count,
                "can_retry": count < self.MAX_CONSECUTIVE_FAILURES,
                "last_error": self.last_errors.get(agent_type),
                "last_failure": self.last_failure_times.get(agent_type, None)
            }
            for agent_type, count in self.failure_counts.items()
        }
    
    def reset_agent(self, agent_type: str) -> None:
        """
        Manually reset an agent's failure tracking.
        
        Args:
            agent_type: The type of agent to reset
        """
        self.failure_counts.pop(agent_type, None)
        self.last_errors.pop(agent_type, None)
        self.last_failure_times.pop(agent_type, None)
        self.logger.info(f"Agent {agent_type} failure tracking reset")
    
    def reset_all(self) -> None:
        """Reset all failure tracking."""
        self.failure_counts.clear()
        self.last_errors.clear()
        self.last_failure_times.clear()
        self.logger.info("All agent failure tracking reset")


# Singleton instance for use across the poller
error_recovery = ErrorRecovery()

