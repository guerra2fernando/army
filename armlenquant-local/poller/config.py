"""
Local Poller Configuration
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Local application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False
    )
    
    # API Connection
    api_url: str = "http://127.0.0.1:8000"
    agent_name: str = "LOCAL_POLLER"
    agent_token: str = ""
    hmac_key: str = ""
    hmac_key_version: int = 1
    agent_secret: Optional[str] = None  # Legacy compatibility
    
    # Worker Identity
    worker_id: str = "WINDOWS_LOCAL_01"
    
    # Polling Configuration
    poll_interval_seconds: int = 30
    task_timeout_seconds: int = 300
    heartbeat_interval_seconds: int = 60
    task_lease_duration_minutes: int = 30
    lease_renewal_interval_seconds: int = 60
    max_task_retries: int = 3
    idempotency_window_hours: int = 1
    
    # LLM Configuration
    # Provider: "cloudflare", "gemini", or "openai"
    llm_provider: str = "gemini"
    llm_auto_fallback: bool = True  # Fallback to other provider if primary fails
    llm_delay_seconds: float = 1.5  # Delay between LLM calls to prevent rate limits
    
    # Google Gemini (default)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    
    # OpenAI (fallback/alternative)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # Cloudflare Workers AI gateway
    cloudflare_ai_base_url: str = "https://ai.army.lengrowth.com/v1"
    cloudflare_ai_model: str = "@cf/deepseek-ai/deepseek-v4-pro-0813"
    cloudflare_ai_gateway_token: str = ""
    
    # Paths
    base_path: Path = Path(".")
    operator_data_root: Path = REPO_ROOT / "operator_data"
    job_drafts_path: Path = Path.home() / "Job_Drafts"
    projects_path: Path = Path.home() / "Projects"
    outreach_exports_path: Path = Path.home() / "Outreach_Exports"
    cv_path: Path = Path.home() / "Documents" / "CV" / "master_cv.md"
    logs_path: Path = Path(".") / "logs"
    active_operator_profile_slug: str = "default"
    active_business_slugs: List[str] = []
    
    # Browser Automation
    headless_mode: bool = True
    browser_timeout: int = 30000

    # Conservative send configuration
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_from_email: str = ""
    
    # Logging
    log_level: str = "INFO"

    # mTLS (optional)
    mtls_cert_path: Optional[str] = None
    mtls_key_path: Optional[str] = None
    ca_cert_path: Optional[str] = None
    
    # Supported Agents
    supported_agents: List[str] = ["JOB_HUNTER", "COMMERCIAL_SCOUT", "OUTREACH_EXECUTOR", "IDEAS_MACHINE", "META_BUILDER"]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
