"""Core configuration — loads .env + YAML configs with environment overlay."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env file from project root
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_ENV_FILE = _PROJECT_ROOT / ".env"
load_dotenv(_ENV_FILE)

_COMMON_CONFIG = SettingsConfigDict(
    extra="ignore",
    env_file=_ENV_FILE if _ENV_FILE.exists() else None,
    env_file_encoding="utf-8",
)


class GroqSettings(BaseSettings):
    """Groq LLM provider settings."""
    model_config = _COMMON_CONFIG

    api_key: str = Field(default="", alias="GROQ_API_KEY")
    model: str = Field(default="openai/gpt-oss-120b", alias="GROQ_MODEL")
    temperature: float = Field(default=0.1, alias="GROQ_TEMPERATURE")
    max_tokens: int = Field(default=2048, alias="GROQ_MAX_TOKENS")



class EmbeddingSettings(BaseSettings):
    """Embedding model settings."""
    model_config = _COMMON_CONFIG

    model: str = Field(default="all-MiniLM-L6-v2", alias="EMBEDDING_MODEL")
    dimension: int = Field(default=384, alias="EMBEDDING_DIMENSION")


class ChromaSettings(BaseSettings):
    """ChromaDB vector store settings."""
    model_config = _COMMON_CONFIG

    persist_dir: str = Field(default="./data/chroma", alias="CHROMA_PERSIST_DIR")
    collection_name: str = Field(default="ragops_documents", alias="CHROMA_COLLECTION_NAME")


class DatabaseSettings(BaseSettings):
    """Database settings."""
    model_config = _COMMON_CONFIG

    url: str = Field(default="sqlite+aiosqlite:///./data/ragops.db", alias="DATABASE_URL")


class RetrievalSettings(BaseSettings):
    """Retrieval pipeline settings."""
    model_config = _COMMON_CONFIG

    top_k: int = Field(default=10, alias="RETRIEVAL_TOP_K")
    rerank_top_n: int = Field(default=5, alias="RERANK_TOP_N")
    reranker_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2", alias="RERANKER_MODEL"
    )


class IngestionSettings(BaseSettings):
    """Ingestion pipeline settings."""
    model_config = _COMMON_CONFIG

    chunk_size: int = Field(default=512, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=50, alias="CHUNK_OVERLAP")


class APISettings(BaseSettings):
    """API server settings."""
    model_config = _COMMON_CONFIG

    host: str = Field(default="0.0.0.0", alias="API_HOST")
    port: int = Field(default=8000, alias="API_PORT")
    reload: bool = Field(default=True, alias="API_RELOAD")


class ObservabilitySettings(BaseSettings):
    """Observability settings."""
    model_config = _COMMON_CONFIG

    service_name: str = Field(default="ragops", alias="OTEL_SERVICE_NAME")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    exporter_otlp_endpoint: str = Field(
        default="http://localhost:4317", alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )


class Settings(BaseSettings):
    """Root application settings — aggregates all sub-settings."""
    model_config = _COMMON_CONFIG

    environment: str = Field(default="development", alias="ENVIRONMENT")

    groq: GroqSettings = Field(default_factory=GroqSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    chroma: ChromaSettings = Field(default_factory=ChromaSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    ingestion: IngestionSettings = Field(default_factory=IngestionSettings)
    api: APISettings = Field(default_factory=APISettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)

    # YAML-loaded config values
    yaml_config: dict[str, Any] = Field(default_factory=dict)



def _load_yaml_config(environment: str) -> dict[str, Any]:
    """Load base.yaml + environment overlay."""
    configs_dir = _PROJECT_ROOT / "configs"
    config: dict[str, Any] = {}

    # Load base config
    base_path = configs_dir / "base.yaml"
    if base_path.exists():
        with open(base_path) as f:
            config = yaml.safe_load(f) or {}

    # Overlay environment-specific config
    env_path = configs_dir / f"{environment}.yaml"
    if env_path.exists():
        with open(env_path) as f:
            env_config = yaml.safe_load(f) or {}
            _deep_merge(config, env_config)

    return config


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Recursively merge overlay into base."""
    for key, value in overlay.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached application settings singleton."""
    environment = os.getenv("ENVIRONMENT", "development")
    yaml_config = _load_yaml_config(environment)

    settings = Settings(yaml_config=yaml_config)

    # Apply YAML values as fallbacks for generation system prompt, etc.
    gen_config = yaml_config.get("generation", {})
    if gen_config.get("system_prompt"):
        settings.yaml_config["system_prompt"] = gen_config["system_prompt"]

    eval_config = yaml_config.get("evaluation", {})
    if eval_config:
        settings.yaml_config["evaluation"] = eval_config

    return settings
