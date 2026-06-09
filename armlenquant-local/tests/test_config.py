"""
Tests for Configuration Module
"""
import os
import pytest


class TestSettings:
    """Tests for settings configuration."""

    def test_settings_loads_from_environment(self):
        """Test that settings loads values from environment."""
        from poller.config import get_settings
        
        settings = get_settings()
        
        assert settings.api_url == "http://test-api.local"
        assert settings.agent_name == "LOCAL_POLLER"
        assert settings.agent_token == "test-agent-token"
        assert settings.hmac_key_version == 1
        assert settings.worker_id == "TEST_WORKER_01"

    def test_settings_has_default_values(self):
        """Test that settings has default values."""
        from poller.config import get_settings
        
        settings = get_settings()
        
        assert settings.poll_interval_seconds == 5
        assert settings.task_timeout_seconds == 30
        assert settings.heartbeat_interval_seconds == 10

    def test_settings_supported_agents(self):
        """Test that supported agents list is configured."""
        from poller.config import get_settings
        
        settings = get_settings()
        
        assert "JOB_HUNTER" in settings.supported_agents
        assert "IDEAS_MACHINE" in settings.supported_agents
        assert "META_BUILDER" in settings.supported_agents

    def test_settings_is_cached(self):
        """Test that settings instance is cached."""
        from poller.config import get_settings
        
        settings1 = get_settings()
        settings2 = get_settings()
        
        assert settings1 is settings2

