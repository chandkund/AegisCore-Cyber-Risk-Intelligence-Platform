from __future__ import annotations



from functools import lru_cache

from pathlib import Path

from typing import List



from pydantic import Field, computed_field, field_validator

from pydantic_settings import BaseSettings, SettingsConfigDict





class Settings(BaseSettings):

    model_config = SettingsConfigDict(

        env_file=".env",

        env_file_encoding="utf-8",

        extra="ignore",

    )



    app_env: str = Field(default="development", validation_alias="APP_ENV")

    api_v1_prefix: str = Field(default="/api/v1", validation_alias="API_V1_PREFIX")

    project_name: str = Field(default="AegisCore Intelligence API", validation_alias="PROJECT_NAME")



    database_url: str = Field(validation_alias="DATABASE_URL")



    jwt_secret_key: str = Field(validation_alias="JWT_SECRET_KEY")

    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")

    access_token_expire_minutes: int = Field(

        default=30, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES"

    )

    refresh_token_expire_days: int = Field(default=14, validation_alias="REFRESH_TOKEN_EXPIRE_DAYS")



    cors_origins_raw: str = Field(

        default="http://localhost:3000",

        validation_alias="CORS_ORIGINS",

    )

    redis_url: str | None = Field(default=None, validation_alias="REDIS_URL")

    rate_limit_per_minute: int = Field(default=120, validation_alias="RATE_LIMIT_PER_MINUTE")



    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    log_json: bool = Field(default=False, validation_alias="LOG_JSON")



    ml_model_path: str = Field(

        default="ml/models/artifacts/risk_prioritization.joblib",

        validation_alias="ML_MODEL_PATH",

    )

    ml_inference_enabled: bool = Field(default=True, validation_alias="ML_INFERENCE_ENABLED")



    prometheus_metrics_enabled: bool = Field(

        default=False,

        validation_alias="PROMETHEUS_METRICS_ENABLED",

    )

    otel_enabled: bool = Field(default=False, validation_alias="OTEL_ENABLED")

    otel_service_name: str = Field(default="aegiscore-api", validation_alias="OTEL_SERVICE_NAME")

    otel_exporter_otlp_endpoint: str | None = Field(

        default=None, validation_alias="OTEL_EXPORTER_OTLP_ENDPOINT"

    )

    secret_provider: str = Field(default="env", validation_alias="SECRET_PROVIDER")

    secret_provider_prefix: str = Field(default="SECRET_", validation_alias="SECRET_PROVIDER_PREFIX")

    vault_addr: str | None = Field(default=None, validation_alias="VAULT_ADDR")



    @computed_field  # type: ignore[prop-decorator]

    @property

    def database_url_sync(self) -> str:

        u = self.database_url.strip()

        if u.startswith("postgresql+asyncpg"):

            return u.replace("postgresql+asyncpg", "postgresql+psycopg", 1)

        return u



    @computed_field  # type: ignore[prop-decorator]

    @property

    def cors_origins(self) -> List[str]:

        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]



    @computed_field  # type: ignore[prop-decorator]

    @property

    def ml_model_path_resolved(self) -> Path:

        """Resolve artifact path: absolute, cwd-relative, or repo-root-relative."""

        p = Path(self.ml_model_path)

        if p.is_absolute():

            return p

        cwd = Path.cwd()

        if (cwd / p).is_file():

            return (cwd / p).resolve()

        here = Path(__file__).resolve()

        repo_root = here.parents[3]

        return (repo_root / p).resolve()



    @field_validator("jwt_secret_key")

    @classmethod

    def jwt_not_empty(cls, v: str) -> str:

        if not v or not str(v).strip():

            raise ValueError("JWT_SECRET_KEY must be set")

        v = str(v).strip()

        if len(v) < 32:

            raise ValueError("JWT_SECRET_KEY must be at least 32 characters for HS256 security")

        return v





@lru_cache(maxsize=1)

def get_settings() -> Settings:

    # Environment-backed settings; mypy cannot see env-populated required fields.

    return Settings()  # type: ignore[call-arg]





def reset_settings_cache() -> None:

    get_settings.cache_clear()

