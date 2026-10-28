"""Application shared dependencies and singletons."""

from __future__ import annotations

from app.core.config import settings
from app.services.account_manager import AccountManager
from app.services.email_service import OutlookEmailService
from app.services.privatemode_client import PrivatemodeClient
from app.services.privatemode_register import RegisterService
from app.services.turnstile_service import TurnstileService

account_manager = AccountManager(settings)
email_service = OutlookEmailService(settings)
turnstile_service = TurnstileService(settings)
register_service = RegisterService(
    settings=settings,
    account_manager=account_manager,
    email_service=email_service,
    turnstile_service=turnstile_service,
)
privatemode_client = PrivatemodeClient(
    settings=settings,
    account_manager=account_manager,
)
