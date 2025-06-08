"""Configuration for the Sales Discovery Bot."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict


class AgentConfig(BaseSettings):
    """Agent configuration settings."""
    
    # LLM Settings
    llm_model: str = Field(default="claude-3-5-sonnet-20241022", validation_alias="LLM_MODEL")
    llm_temperature: float = Field(default=0.7, validation_alias="LLM_TEMPERATURE")
    max_tokens: int = Field(default=1000, validation_alias="MAX_TOKENS")
    
    # API Keys
    anthropic_api_key: str = Field(..., validation_alias="ANTHROPIC_API_KEY")
    
    # Database (optional for now)
    postgres_dsn: Optional[str] = Field(default=None, validation_alias="POSTGRES_DSN")
    redis_url: str = Field(default="redis://localhost:6379", validation_alias="REDIS_URL")
    
    # Business Settings
    calendly_url: str = Field(
        default="https://calendly.com/justin-erezcapital/30min",
        validation_alias="CALENDLY_URL"
    )
    
    # Partnership Tiers
    starter_price: int = 1250
    growth_price: int = 2500
    enterprise_price: int = 5000
    
    # Token Management
    daily_token_limit: int = Field(default=1000000, validation_alias="DAILY_TOKEN_LIMIT")
    daily_cost_limit: float = Field(default=50.0, validation_alias="DAILY_COST_LIMIT")
    
    # Debug
    debug_mode: bool = Field(default=False, validation_alias="DEBUG_LOCAL")
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"  # Allow extra fields from .env file
    )


def get_config() -> AgentConfig:
    """Get the agent configuration."""
    return AgentConfig()