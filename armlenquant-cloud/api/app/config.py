"""
ArmLenQuant API Configuration
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional, List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "ArmLenQuant API"
    app_version: str = "1.0.0"
    debug: bool = False
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    
    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # MongoDB
    mongodb_uri: str
    mongodb_db_name: str = "armlenquant"
    
    # JWT Authentication
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 168  # 7 days
    
    # Agent Authentication
    agent_secret: str
    
    # mTLS
    mtls_required: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    ca_cert_path: Optional[str] = None

    # HMAC Signing
    secret_rotation_days: int = 30
    signature_grace_period_seconds: int = 300
    key_overlap_days: int = 7

    # Scoped Tokens
    token_expiry_hours: int = 24
    max_token_uses: int = 10000
    require_ip_restrictions: bool = False
    
    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"

    # LLM Provider Configuration
    llm_provider: str = "gemini"  # Supported: cloudflare, gemini, openai
    llm_auto_fallback: bool = True  # Whether to automatically fallback to alternative providers
    cloudflare_ai_base_url: str = "https://ai.army.lengrowth.com/v1"
    cloudflare_ai_model: str = "@cf/deepseek-ai/deepseek-v4-pro-0813"
    cloudflare_ai_gateway_token: str = ""
    embedding_provider: str = "openai"

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    
    # Crypto APIs
    coingecko_api_key: str = ""
    cryptopanic_api_key: str = ""
    
    # Telegram Bot
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""  # Your personal chat ID for notifications
    telegram_enabled: bool = False
    telegram_webhook_url: Optional[str] = None  # For webhook mode (optional)

    # Scheduling
    morning_brief_timezone: str = "UTC"  # Timezone for morning brief scheduling (e.g., "America/New_York", "Europe/London")
    
    # Notification Settings
    notifications_enabled: bool = True
    notify_on_task_complete: bool = True
    notify_on_task_failed: bool = True
    notify_on_agent_alert: bool = True
    notify_on_system_error: bool = True

    # Task Reliability
    task_lease_duration_minutes: int = 30
    max_task_retries: int = 3
    idempotency_window_hours: int = 1
    lease_renewal_interval_seconds: int = 60
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    # Orchestrator Safety
    orchestrator_safety_enabled: bool = True
    schema_change_approval_required: bool = True
    spawn_budget_enabled: bool = True
    auto_rollback_enabled: bool = True
    kill_switch_enabled: bool = True
    max_spawns_per_hour: int = 10
    error_rate_threshold: float = 0.05
    performance_degradation_threshold: float = 0.15
    resource_exhaustion_threshold: float = 0.95
    change_impact_monitoring: bool = True
    monitoring_window_minutes: int = 5
    rollback_grace_period_minutes: int = 10
    
    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def cors_origins_list(self) -> List[str]:
        """Return configured browser origins as a trimmed allowlist."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
