from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    mock_port: int = Field(default=8000, validation_alias="MOCK_PORT")
    mock_default_model: str = Field(default="mock-chat-v1", validation_alias="MOCK_DEFAULT_MODEL")
    mock_chunk_delay_ms: int = Field(default=30, ge=0, validation_alias="MOCK_CHUNK_DELAY_MS")
    mock_embedding_dims: int = Field(default=1536, ge=1, validation_alias="MOCK_EMBEDDING_DIMS")
    mock_require_auth: bool = Field(default=False, validation_alias="MOCK_REQUIRE_AUTH")
    mock_chaos_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        validation_alias="MOCK_CHAOS_RATE",
    )
    mock_log_requests: bool = Field(default=True, validation_alias="MOCK_LOG_REQUESTS")

    @property
    def chunk_delay_seconds(self) -> float:
        return self.mock_chunk_delay_ms / 1000


@lru_cache
def get_settings() -> Settings:
    return Settings()
