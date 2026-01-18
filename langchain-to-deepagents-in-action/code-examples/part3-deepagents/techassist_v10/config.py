"""
TechAssist v1.0 配置管理
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class TechAssistConfig(BaseSettings):
    """TechAssist 配置"""

    # API Keys
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")

    # Model Settings
    primary_model: str = "claude-sonnet-4-20250514"
    fallback_model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.7
    max_tokens: int = 4096

    # Planning Settings
    max_plan_steps: int = 10
    replan_threshold: float = 0.5

    # Memory Settings
    short_term_window: int = 20
    long_term_top_k: int = 5
    memory_importance_threshold: float = 0.6

    # Reflexion Settings
    max_iterations: int = 3
    quality_threshold: float = 0.8

    # Session Settings
    session_timeout_minutes: int = 30

    class Config:
        env_file = ".env"
        extra = "ignore"


# 全局配置實例
config = TechAssistConfig()
