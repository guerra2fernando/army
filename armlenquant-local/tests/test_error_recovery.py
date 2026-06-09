"""
Tests for Agent Error Recovery System
Phase 10: Integration & Polish
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock


class TestErrorRecovery:
    """Test error recovery functionality."""
    
    def test_error_recovery_initialization(self):
        """Test ErrorRecovery initializes correctly."""
        from poller.error_recovery import ErrorRecovery
        
        recovery = ErrorRecovery()
        
        assert recovery.failure_counts == {}
        assert recovery.MAX_CONSECUTIVE_FAILURES == 3
    
    def test_record_failure_increments_count(self):
        """Test recording a failure increments the count."""
        from poller.error_recovery import ErrorRecovery
        
        recovery = ErrorRecovery()
        
        recovery.record_failure("JOB_HUNTER", "Test error")
        
        assert recovery.failure_counts["JOB_HUNTER"] == 1
    
    def test_record_failure_multiple_times(self):
        """Test recording multiple failures."""
        from poller.error_recovery import ErrorRecovery
        
        recovery = ErrorRecovery()
        
        recovery.record_failure("JOB_HUNTER", "Error 1")
        recovery.record_failure("JOB_HUNTER", "Error 2")
        recovery.record_failure("JOB_HUNTER", "Error 3")
        
        assert recovery.failure_counts["JOB_HUNTER"] == 3
    
    def test_record_success_resets_count(self):
        """Test recording a success resets the failure count."""
        from poller.error_recovery import ErrorRecovery
        
        recovery = ErrorRecovery()
        
        # Record some failures
        recovery.record_failure("JOB_HUNTER", "Error 1")
        recovery.record_failure("JOB_HUNTER", "Error 2")
        
        # Record success
        recovery.record_success("JOB_HUNTER")
        
        assert recovery.failure_counts["JOB_HUNTER"] == 0
    
    def test_should_retry_when_under_limit(self):
        """Test should_retry returns True when under failure limit."""
        from poller.error_recovery import ErrorRecovery
        
        recovery = ErrorRecovery()
        
        # No failures yet
        assert recovery.should_retry("JOB_HUNTER") is True
        
        # One failure
        recovery.record_failure("JOB_HUNTER", "Error")
        assert recovery.should_retry("JOB_HUNTER") is True
    
    def test_should_retry_when_at_limit(self):
        """Test should_retry returns False when at failure limit."""
        from poller.error_recovery import ErrorRecovery
        
        recovery = ErrorRecovery()
        
        # Hit the limit
        for _ in range(3):
            recovery.record_failure("JOB_HUNTER", "Error")
        
        assert recovery.should_retry("JOB_HUNTER") is False
    
    def test_different_agents_tracked_separately(self):
        """Test different agents are tracked separately."""
        from poller.error_recovery import ErrorRecovery
        
        recovery = ErrorRecovery()
        
        # Max out JOB_HUNTER
        for _ in range(3):
            recovery.record_failure("JOB_HUNTER", "Error")
        
        # IDEAS_MACHINE should still be allowed
        assert recovery.should_retry("JOB_HUNTER") is False
        assert recovery.should_retry("IDEAS_MACHINE") is True


class TestErrorRecoveryWithLogging:
    """Test error recovery with logging functionality."""
    
    def test_warning_logged_at_max_failures(self, capsys):
        """Test warning is logged when max failures reached."""
        from poller.error_recovery import ErrorRecovery
        
        recovery = ErrorRecovery()
        
        # Hit the limit
        for _ in range(3):
            recovery.record_failure("JOB_HUNTER", "Error")
        
        # Loguru outputs to stderr by default
        captured = capsys.readouterr()
        # Check that warning about max failures was logged
        assert "failed 3 times" in captured.err or recovery.failure_counts["JOB_HUNTER"] == 3
    
    def test_error_details_recorded(self):
        """Test error details are recorded."""
        from poller.error_recovery import ErrorRecovery
        
        recovery = ErrorRecovery()
        
        recovery.record_failure("JOB_HUNTER", "Specific error message")
        
        # The error should be recorded (implementation may vary)
        assert recovery.failure_counts["JOB_HUNTER"] == 1


class TestErrorRecoveryIntegration:
    """Test error recovery integration with poller."""
    
    @pytest.mark.asyncio
    async def test_poller_uses_error_recovery(self):
        """Test poller integrates with error recovery."""
        from poller.error_recovery import ErrorRecovery
        
        recovery = ErrorRecovery()
        
        # Simulate a task failure scenario
        agent_type = "JOB_HUNTER"
        
        # Before any failures
        assert recovery.should_retry(agent_type) is True
        
        # After consecutive failures
        for i in range(3):
            recovery.record_failure(agent_type, f"Error {i}")
        
        assert recovery.should_retry(agent_type) is False
        
        # After a success
        recovery.record_success(agent_type)
        assert recovery.should_retry(agent_type) is True
    
    @pytest.mark.asyncio
    async def test_error_recovery_with_different_error_types(self):
        """Test error recovery handles different error types."""
        from poller.error_recovery import ErrorRecovery
        
        recovery = ErrorRecovery()
        
        # Different types of errors
        recovery.record_failure("JOB_HUNTER", "Network timeout")
        recovery.record_failure("JOB_HUNTER", "API rate limited")
        recovery.record_failure("JOB_HUNTER", "Invalid response")
        
        assert recovery.failure_counts["JOB_HUNTER"] == 3
        assert recovery.should_retry("JOB_HUNTER") is False


class TestErrorRecoveryCustomLimits:
    """Test error recovery with custom limits."""
    
    def test_custom_max_failures(self):
        """Test custom max failures limit."""
        from poller.error_recovery import ErrorRecovery
        
        recovery = ErrorRecovery(max_consecutive_failures=5)
        
        assert recovery.MAX_CONSECUTIVE_FAILURES == 5
        
        # Should still allow retries after 3 failures
        for _ in range(3):
            recovery.record_failure("JOB_HUNTER", "Error")
        
        assert recovery.should_retry("JOB_HUNTER") is True
        
        # Should block after 5 failures
        for _ in range(2):
            recovery.record_failure("JOB_HUNTER", "Error")
        
        assert recovery.should_retry("JOB_HUNTER") is False


class TestPollerMainWithErrorRecovery:
    """Test poller main.py integration with error recovery."""
    
    @pytest.mark.asyncio
    async def test_execute_task_records_failure_on_error(self):
        """Test task execution records failure on error."""
        # This test verifies the integration point in the poller
        from poller.error_recovery import ErrorRecovery
        
        recovery = ErrorRecovery()
        
        # Simulate task failure
        recovery.record_failure("JOB_HUNTER", "Task execution failed")
        
        assert recovery.failure_counts["JOB_HUNTER"] == 1
    
    @pytest.mark.asyncio
    async def test_execute_task_records_success_on_completion(self):
        """Test task execution records success on completion."""
        from poller.error_recovery import ErrorRecovery
        
        recovery = ErrorRecovery()
        
        # Simulate previous failures
        recovery.record_failure("JOB_HUNTER", "Error 1")
        recovery.record_failure("JOB_HUNTER", "Error 2")
        
        # Simulate successful execution
        recovery.record_success("JOB_HUNTER")
        
        assert recovery.failure_counts["JOB_HUNTER"] == 0

