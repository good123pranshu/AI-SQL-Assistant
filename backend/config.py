"""
Configuration module for AI SQL Assistant.
Loads environment variables and sets application defaults.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "AI SQL Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Database Configuration
    # Defaults to SQLite demo database in BASE_DIR / "data" / "ecommerce_demo.db"
    # To use PostgreSQL, set DATABASE_URL="postgresql://user:password@localhost:5432/dbname"
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'data' / 'ecommerce_demo.db'}"
    )
    MAX_QUERY_ROWS_LIMIT: int = 100
    QUERY_TIMEOUT_SECONDS: int = 10

    # LLM Settings
    # Supported providers: "gemini", "openai", "ollama", "mock"
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "mock")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", None)
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", None)
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")

    model_config = {
        "env_file": ".env",
        "extra": "allow"
    }


settings = Settings()
