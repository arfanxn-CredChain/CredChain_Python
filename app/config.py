"""Application settings loaded from environment / .env file."""

from typing import Any

from pydantic import Field, field_validator
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

_CSV_FIELDS: frozenset[str] = frozenset({"easyocr_langs", "cors_allow_origins"})


def _split_csv_if_csv_field(
    field_name: str, value: Any
) -> tuple[Any, bool]:
    """Return (parsed_value, was_csv). When the field is a known CSV field
    and value is a string, split on commas. Otherwise return value unchanged.
    """
    if field_name in _CSV_FIELDS and isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()], True
    return value, False


class _CsvEnvSettingsSource(EnvSettingsSource):
    """EnvSettingsSource that splits comma-separated values for known
    CSV fields instead of attempting JSON decoding (which fails on bare
    strings like "id,en"). pydantic-settings 2.6.1 does not export
    NoDecode, so we override prepare_field_value directly.
    """

    def prepare_field_value(
        self,
        field_name: str,
        field: FieldInfo,
        value: Any,
        value_is_complex: bool,
    ) -> Any:
        parsed, was_csv = _split_csv_if_csv_field(field_name, value)
        if was_csv:
            return parsed
        return super().prepare_field_value(field_name, field, value, value_is_complex)


class _CsvDotEnvSettingsSource(DotEnvSettingsSource):
    """DotEnvSettingsSource counterpart with the same CSV bypass."""

    def prepare_field_value(
        self,
        field_name: str,
        field: FieldInfo,
        value: Any,
        value_is_complex: bool,
    ) -> Any:
        parsed, was_csv = _split_csv_if_csv_field(field_name, value)
        if was_csv:
            return parsed
        return super().prepare_field_value(field_name, field, value, value_is_complex)


class Settings(BaseSettings):
    """Type-validated settings loaded from environment variables.

    All fields have sensible defaults; only LOG_OUTPUT and MODEL_DIR
    typically need overriding in production. Comma-separated env vars
    (EASYOCR_LANGS, CORS_ALLOW_ORIGINS) are split into lists by custom
    settings sources before reaching pydantic's JSON decoder.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    fastapi_port: int = 8081
    log_level: str = "info"
    log_output: str = "stdout"

    model_dir: str = "/models"
    easyocr_langs: list[str] = Field(default_factory=lambda: ["id", "en"])

    llm_max_new_tokens: int = 512
    llm_device: str = "cpu"
    llm_timeout_seconds: int = 60
    llm_model_name: str = "Qwen2.5-0.5B-Instruct"
    llm_model_file: str = "qwen2.5-0.5b-instruct-q4_k_m.gguf"
    embedding_model_name: str = "LaBSE"

    locales_dir: str = "./locales"

    custom_id_patterns_file: str = "./custom_id_patterns.txt"
    override_builtin_id_patterns: bool = False
    max_files_per_request: int = 100

    cors_allow_origins: list[str] = Field(default_factory=lambda: ["*"])

    @field_validator("easyocr_langs", "cors_allow_origins", mode="before")
    @classmethod
    def split_csv(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            _CsvEnvSettingsSource(settings_cls),
            _CsvDotEnvSettingsSource(settings_cls),
            file_secret_settings,
        )


settings = Settings()
