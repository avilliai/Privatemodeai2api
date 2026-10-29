"""Application settings and configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def resolve_project_path(path_str: str | Path) -> Path:
    p = Path(path_str)
    if p.is_absolute():
        return p
    return (PROJECT_ROOT / p).resolve()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Service configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = False
    LOG_LEVEL: str = "INFO"
    API_KEY: str = ""  # If set, clients must supply Bearer <API_KEY> to access /v1 endpoints

    # Account Pool
    ACCOUNT_FILE: str = "data/accounts.json"
    ACCOUNT_FAILURE_LIMIT: int = 3
    ACCOUNT_MAX_CONSECUTIVE_REQUESTS: int = 20
    ACCOUNT_COOLDOWN_SECONDS: int = 300
    AUTO_DISABLE_EXHAUSTED: bool = True

    # Upstream Privatemode APIs
    PRIVATEMODE_PROXYLESS_URL: str = "https://proxyless-api.privatemode.ai/v1"
    PRIVATEMODE_SAAS_URL: str = "https://saas-api-403278544087.europe-west1.run.app"
    PRIVATEMODE_CLERK_URL: str = "https://clerk.privatemode.ai/v1"
    PRIVATEMODE_PORTAL_URL: str = "https://portal.privatemode.ai"
    PRIVATEMODE_CLERK_PK: str = "pk_live_Y2xlcmsucHJpdmF0ZW1vZGUuYWkk"
    DEFAULT_MODEL: str = "glm-latest"
    SUPPORTED_MODELS: str = "deepseek-ocr-2,glm-5.3,glm-latest,glm-5.3-flash,glm-flash-latest,gpt-oss-120b,qwen3-embedding-4b,voxtral-mini-3b,whisper-large-v3"
    MODEL_ALIASES_JSON: str = '{"glm-5":"glm-5.3"}'

    # Outlook Mail Service Configuration (Referencing genspark2api)
    OUTLOOK_ACCOUNT_FILE: str = "C:/Users/Administrator/PycharmProjects/genspark2api/OUT-20260728-S1000-00082_Filtered.txt"
    OUTLOOK_BLACKLIST_FILE: str = "data/outlook_email_blacklist.json"
    OUTLOOK_TOKEN_URL: str = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    OUTLOOK_IMAP_HOSTS: Any = ["outlook.office365.com", "outlook.live.com"]
    OUTLOOK_IMAP_PORT: int = 993
    OUTLOOK_IMAP_TIMEOUT: int = 20
    EMAIL_POLL_TIMEOUT: int = 120
    EMAIL_POLL_INTERVAL: int = 3

    # Turnstile Solver Configuration
    TURNSTILE_PORTAL_URL: str = "https://portal.privatemode.ai"
    TURNSTILE_SOLVER_URL: str = "http://127.0.0.1:5072"
    TURNSTILE_SITEKEY: str = "0x4AAAAAAAWXJGBD7bONzLBd"
    TURNSTILE_SOLVER_PATH: str = "C:/Users/Administrator/PycharmProjects/Turnstile-Solver-NEW"
    TURNSTILE_TIMEOUT: int = 60
    TURNSTILE_BROWSER_TYPE: str = "chromium"

    # Registration parameters
    REGISTER_PASSWORD_LENGTH: int = 16
    REGISTER_CONCURRENCY: int = 1
    REQUEST_TIMEOUT: int = 120

    @field_validator("OUTLOOK_IMAP_HOSTS", mode="before")
    @classmethod
    def parse_imap_hosts(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(h).strip() for h in parsed if str(h).strip()]
            except Exception:
                pass
            return [h.strip() for h in v.split(",") if h.strip()]
        if isinstance(v, list):
            return [str(h).strip() for h in v if str(h).strip()]
        return ["outlook.office365.com", "outlook.live.com"]

    @property
    def model_aliases(self) -> dict[str, str]:
        try:
            return json.loads(self.MODEL_ALIASES_JSON)
        except Exception:
            return {}

    @property
    def models_list(self) -> list[str]:
        return [m.strip() for m in self.SUPPORTED_MODELS.split(",") if m.strip()]


settings = Settings()
