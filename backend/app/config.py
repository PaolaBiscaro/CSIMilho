from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: SecretStr | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    gemini_api_key_2: SecretStr | None = Field(default=None, validation_alias="GEMINI_API_KEY_2")
    gemini_api_key_3: SecretStr | None = Field(default=None, validation_alias="GEMINI_API_KEY_3")
    gemini_model: str = Field(default="gemini-2.5-flash", validation_alias="GEMINI_MODEL")
    gemini_timeout_seconds: int = Field(default=90, ge=1, validation_alias="GEMINI_TIMEOUT_SECONDS")
    gemini_key_cooldown_seconds: int = Field(
        default=30, ge=0, validation_alias="GEMINI_KEY_COOLDOWN_SECONDS",
    )
    gemini_max_tool_calls: int = Field(default=8, ge=1, validation_alias="GEMINI_MAX_TOOL_CALLS")
    max_upload_mb: int = Field(default=100, ge=1, validation_alias="MAX_UPLOAD_MB")
    app_env: str = Field(default="development", validation_alias="APP_ENV")
    app_version: str = "1.0.0"

    @property
    def gemini_api_keys(self) -> tuple[SecretStr, ...]:
        """Configured, non-blank and de-duplicated keys, never serialized by Pydantic."""
        keys: list[SecretStr] = []
        seen: set[str] = set()
        for secret in (self.gemini_api_key, self.gemini_api_key_2, self.gemini_api_key_3):
            value = secret.get_secret_value().strip() if secret is not None else ""
            if value and value not in seen:
                seen.add(value)
                keys.append(SecretStr(value))
        return tuple(keys)

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_keys)


@lru_cache
def get_settings() -> Settings:
    return Settings()
