"""Account and API Key pool manager for Privatemode 2API."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from app.core.config import Settings, resolve_project_path, settings as app_settings
from app.core.exceptions import AccountPoolError

logger = logging.getLogger(__name__)


@dataclass
class AccountRecord:
    email: str
    password: str
    api_key: str  # The Privatemode license_key
    key_id: str = ""
    org_id: str = ""
    session_id: str = ""
    status: str = "active"  # active, rate_limited, exhausted, disabled
    consecutive_failures: int = 0
    total_requests: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    effective_tokens_used: int = 0
    initial_quota: int = 5_000_000
    created_at: float = field(default_factory=time.time)
    last_used_at: float = 0.0
    rate_limited_until: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_usable(self, now: float) -> bool:
        if self.status == "disabled" or self.status == "exhausted":
            return False
        if self.status == "rate_limited":
            if now < self.rate_limited_until:
                return False
            # Cooldown passed, restore to active
            self.status = "active"
            self.consecutive_failures = 0
        return True


class AccountManager:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or app_settings
        self.account_file = resolve_project_path(self.settings.ACCOUNT_FILE)
        self.accounts: list[AccountRecord] = []
        self._current_index: int = 0
        self._lock = asyncio.Lock()
        self._load_accounts()

    def _load_accounts(self) -> None:
        if not self.account_file.is_file():
            self.account_file.parent.mkdir(parents=True, exist_ok=True)
            self.account_file.write_text("[]", encoding="utf-8")
            self.accounts = []
            return

        try:
            data = json.loads(self.account_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                self.accounts = [
                    AccountRecord(
                        email=acc.get("email", ""),
                        password=acc.get("password", ""),
                        api_key=acc.get("api_key", ""),
                        key_id=acc.get("key_id", ""),
                        org_id=acc.get("org_id", ""),
                        session_id=acc.get("session_id", ""),
                        status=acc.get("status", "active"),
                        consecutive_failures=acc.get("consecutive_failures", 0),
                        total_requests=acc.get("total_requests", 0),
                        created_at=acc.get("created_at", time.time()),
                        last_used_at=acc.get("last_used_at", 0.0),
                        rate_limited_until=acc.get("rate_limited_until", 0.0),
                        metadata=acc.get("metadata", {}),
                    )
                    for acc in data
                    if acc.get("api_key")
                ]
                logger.info("Loaded %d accounts with API keys from %s", len(self.accounts), self.account_file)
        except Exception as e:
            logger.error("Failed to load accounts from %s: %s", self.account_file, e)
            self.accounts = []

    def save_accounts(self) -> None:
        self.account_file.parent.mkdir(parents=True, exist_ok=True)
        temp_file = self.account_file.with_suffix(self.account_file.suffix + ".tmp")
        data = [asdict(acc) for acc in self.accounts]
        temp_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_file.replace(self.account_file)

    async def add_account(
        self,
        email: str,
        password: str,
        api_key: str,
        key_id: str = "",
        org_id: str = "",
        session_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> AccountRecord:
        """Add a newly registered account with its created API key."""
        async with self._lock:
            # Check if account already exists
            for acc in self.accounts:
                if acc.email.lower() == email.lower() or acc.api_key == api_key:
                    acc.password = password
                    acc.api_key = api_key
                    acc.key_id = key_id or acc.key_id
                    acc.org_id = org_id or acc.org_id
                    acc.session_id = session_id or acc.session_id
                    acc.status = "active"
                    acc.consecutive_failures = 0
                    if metadata:
                        acc.metadata.update(metadata)
                    self.save_accounts()
                    logger.info("Updated existing account %s in pool", email)
                    return acc

            record = AccountRecord(
                email=email,
                password=password,
                api_key=api_key,
                key_id=key_id,
                org_id=org_id,
                session_id=session_id,
                metadata=metadata or {},
            )
            self.accounts.append(record)
            self.save_accounts()
            logger.info("Added new account %s to pool (total: %d)", email, len(self.accounts))
            return record

    async def get_next_account(self) -> AccountRecord:
        """Select the next available account using round-robin rotation."""
        async with self._lock:
            if not self.accounts:
                raise AccountPoolError("No accounts registered in pool. Please run registration first.")

            now = time.time()
            total = len(self.accounts)

            # Look for active account starting from current_index
            for offset in range(total):
                idx = (self._current_index + offset) % total
                acc = self.accounts[idx]
                if acc.is_usable(now):
                    self._current_index = (idx + 1) % total
                    acc.last_used_at = now
                    acc.total_requests += 1
                    return acc

            raise AccountPoolError(
                f"All {total} accounts in pool are currently exhausted, rate-limited, or disabled"
            )

    async def mark_success(self, account: AccountRecord) -> None:
        async with self._lock:
            account.consecutive_failures = 0
            account.total_requests += 1
            account.last_used_at = time.time()
            if account.status == "rate_limited":
                account.status = "active"
            self.save_accounts()

    async def record_usage(
        self,
        account: AccountRecord,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        effective_tokens: int = 0,
    ) -> None:
        async with self._lock:
            account.prompt_tokens = getattr(account, "prompt_tokens", 0) + prompt_tokens
            account.completion_tokens = getattr(account, "completion_tokens", 0) + completion_tokens
            account.total_tokens = getattr(account, "total_tokens", 0) + (prompt_tokens + completion_tokens)
            account.effective_tokens_used = getattr(account, "effective_tokens_used", 0) + effective_tokens
            account.total_requests = getattr(account, "total_requests", 0) + 1
            account.last_used_at = time.time()
            account.consecutive_failures = 0
            if account.status == "rate_limited":
                account.status = "active"
            if account.effective_tokens_used >= getattr(account, "initial_quota", 5_000_000):
                if self.settings.AUTO_DISABLE_EXHAUSTED:
                    account.status = "exhausted"
            self.save_accounts()

    async def mark_failure(self, account: AccountRecord, error_type: str = "transient", detail: str = "") -> None:
        async with self._lock:
            account.consecutive_failures += 1
            now = time.time()

            if error_type in ("quota_exceeded", "quota", "balance"):
                logger.warning("Account %s quota exhausted: %s", account.email, detail)
                if self.settings.AUTO_DISABLE_EXHAUSTED:
                    account.status = "exhausted"
                else:
                    account.status = "rate_limited"
                    account.rate_limited_until = now + self.settings.ACCOUNT_COOLDOWN_SECONDS * 4
            elif error_type in ("rate_limit", "429"):
                logger.warning("Account %s hit rate limit (429): %s", account.email, detail)
                account.status = "rate_limited"
                account.rate_limited_until = now + self.settings.ACCOUNT_COOLDOWN_SECONDS
            elif error_type in ("auth", "401", "403"):
                logger.warning("Account %s auth failed (%s): %s", account.email, error_type, detail)
                if account.consecutive_failures >= 2:
                    account.status = "disabled"
            else:
                if account.consecutive_failures >= self.settings.ACCOUNT_FAILURE_LIMIT:
                    logger.warning("Account %s reached failure limit (%d), cooling down", account.email, account.consecutive_failures)
                    account.status = "rate_limited"
                    account.rate_limited_until = now + self.settings.ACCOUNT_COOLDOWN_SECONDS

            self.save_accounts()

    async def list_accounts(self) -> list[dict[str, Any]]:
        async with self._lock:
            now = time.time()
            return [
                {
                    "email": acc.email,
                    "api_key_masked": acc.api_key[:8] + "..." + acc.api_key[-4:] if len(acc.api_key) > 12 else "***",
                    "key_id": acc.key_id,
                    "org_id": acc.org_id,
                    "status": acc.status if acc.is_usable(now) else ("cooling_down" if acc.status == "rate_limited" else acc.status),
                    "consecutive_failures": acc.consecutive_failures,
                    "total_requests": acc.total_requests,
                    "prompt_tokens": getattr(acc, "prompt_tokens", 0),
                    "completion_tokens": getattr(acc, "completion_tokens", 0),
                    "total_tokens": getattr(acc, "total_tokens", 0),
                    "effective_tokens_used": getattr(acc, "effective_tokens_used", 0),
                    "initial_quota": getattr(acc, "initial_quota", 5_000_000),
                    "created_at": acc.created_at,
                    "last_used_at": acc.last_used_at,
                }
                for acc in self.accounts
            ]

    async def get_stats(self) -> dict[str, Any]:
        async with self._lock:
            now = time.time()
            total = len(self.accounts)
            active = sum(1 for acc in self.accounts if acc.is_usable(now))
            rate_limited = sum(1 for acc in self.accounts if acc.status == "rate_limited" and not acc.is_usable(now))
            exhausted = sum(1 for acc in self.accounts if acc.status == "exhausted")
            disabled = sum(1 for acc in self.accounts if acc.status == "disabled")
            total_requests = sum(acc.total_requests for acc in self.accounts)

            return {
                "total_accounts": total,
                "active_accounts": active,
                "rate_limited_accounts": rate_limited,
                "exhausted_accounts": exhausted,
                "disabled_accounts": disabled,
                "total_requests_served": total_requests,
            }

    async def get_account_by_email(self, email: str) -> AccountRecord | None:
        async with self._lock:
            for acc in self.accounts:
                if acc.email == email:
                    return acc
            return None

    async def purge_dead_accounts(self) -> int:
        return await self.purge_exhausted()

    async def remove_account(self, email: str) -> bool:
        async with self._lock:
            initial_len = len(self.accounts)
            self.accounts = [acc for acc in self.accounts if acc.email.lower() != email.lower()]
            if len(self.accounts) < initial_len:
                self.save_accounts()
                logger.info('Removed account %s from pool', email)
                return True
            return False

    async def reset_account(self, email: str) -> bool:
        async with self._lock:
            for acc in self.accounts:
                if acc.email.lower() == email.lower():
                    acc.status = 'active'
                    acc.consecutive_failures = 0
                    acc.rate_limited_until = 0.0
                    self.save_accounts()
                    logger.info('Reset account %s status to active', email)
                    return True
            return False

    async def purge_exhausted(self) -> int:
        async with self._lock:
            initial_len = len(self.accounts)
            self.accounts = [acc for acc in self.accounts if acc.status not in ('exhausted', 'disabled')]
            purged = initial_len - len(self.accounts)
            if purged > 0:
                self.save_accounts()
                logger.info('Purged %d exhausted/disabled accounts from pool', purged)
            return purged
