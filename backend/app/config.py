from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Smart Shopping Guide Agent"
    app_version: str = "0.1.0"
    app_host: str = "0.0.0.0"
    app_port: int = 8080

    demo_mode: bool = Field(default=True, alias="DEMO_MODE")
    log_retention_days: int = Field(default=7, alias="LOG_RETENTION_DAYS")
    recognition_confidence_threshold: float = Field(default=0.6, alias="RECOGNITION_CONFIDENCE_THRESHOLD")

    workspace_dir: Path = Field(default=Path(__file__).resolve().parents[2], alias="WORKSPACE_DIR")
    knowledge_dir: Path = Field(default=Path(__file__).resolve().parents[2] / "knowledge", alias="KNOWLEDGE_DIR")
    knowledge_products_dir: Path = Field(
        default=Path(__file__).resolve().parents[2] / "knowledge" / "products",
        alias="KNOWLEDGE_PRODUCTS_DIR",
    )
    image_dir: Path = Field(default=Path(__file__).resolve().parents[2] / "knowledge" / "images", alias="IMAGE_DIR")

    models_dir: Path = Field(default=Path(__file__).resolve().parents[1] / "models", alias="MODELS_DIR")
    logs_dir: Path = Field(default=Path(__file__).resolve().parents[1] / "logs", alias="LOGS_DIR")

    vlm_provider: str = Field(default="mock", alias="VLM_PROVIDER")
    vlm_model_name: str = Field(default="Qwen/Qwen2.5-VL-7B-Instruct", alias="VLM_MODEL_NAME")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

