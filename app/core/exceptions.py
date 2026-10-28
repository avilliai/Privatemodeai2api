"""Custom exception hierarchy for Privatemode 2API."""

from __future__ import annotations


class PrivatemodeError(Exception):
    """Base exception for all project errors."""


class RegistrationError(PrivatemodeError):
    """Raised when an account registration step fails."""


class OutlookImapAuthenticationError(RegistrationError):
    """Raised when Outlook OAuth succeeds but IMAP authentication fails."""


class TurnstileError(RegistrationError):
    """Raised when Cloudflare Turnstile cannot be solved."""


class AccountPoolError(PrivatemodeError):
    """Raised when account pool is empty or cannot provide an active account."""


class UpstreamError(PrivatemodeError):
    """Raised when Privatemode upstream API returns an error."""

    def __init__(self, message: str, status_code: int = 502, detail: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail or {}


class QuotaExceededError(UpstreamError):
    """Raised when an account's quota has been exhausted."""

    def __init__(self, message: str = "Account quota exceeded", detail: dict | None = None):
        super().__init__(message, status_code=429, detail=detail)


class AuthenticationError(PrivatemodeError):
    """Raised when an API key or token is invalid."""
