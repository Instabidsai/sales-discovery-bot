"""Configuration for the Sales Discovery Bot."""

import os
from typing import Optional
from pydantic import BaseSettings, Field


class AgentConfig(BaseSettings):
    """Agent configuration settings."""
    
    # LLM Settings
    llm_model: str = Field(default="gpt-4o", env="LLM_MODEL")
    llm_temperature: float = Field(default=0.7, env="LLM_TEMPERATURE")
    max_tokens: int = Field(default=1000, env="MAX_TOKENS")
    
    # API Keys
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    
    # Database
    postgres_dsn: str = Field(..., env="POSTGRES_DSN")
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # Business Settings
    calendly_url: str = Field(
        default="https://calendly.com/justin-erezcapital/30min",
        env="CALENDLY_URL"
    )
    
    # Partnership Tiers
    starter_price: int = 1250
    growth_price: int = 2500
    enterprise_price: int = 5000
    
    # Token Management
    daily_token_limit: int = Field(default=1000000, env="DAILY_TOKEN_LIMIT")
    daily_cost_limit: float = Field(default=50.0, env="DAILY_COST_LIMIT")
    
    # Debug
    debug_mode: bool = Field(default=False, env="DEBUG_LOCAL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_config() -> AgentConfig:
    """Get the agent configuration."""
    return AgentConfig()