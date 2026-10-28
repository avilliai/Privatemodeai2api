import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
import logging
from app.core.config import settings
from app.services.account_manager import AccountManager
from app.services.email_service import OutlookEmailService
from app.services.turnstile_service import TurnstileService
from app.services.privatemode_register import RegisterService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")

async def test_reg():
    mgr = AccountManager(settings)
    email_svc = OutlookEmailService(settings)
    ts = TurnstileService(settings)
    reg_svc = RegisterService(settings, mgr, email_svc, ts)
    print("Testing single account registration...")
    acc = await reg_svc.register_single_account()
    print("SUCCESS! Registered account:")
    print("Email:", acc.email)
    print("API Key:", acc.api_key)
    print("Key ID:", acc.key_id)

asyncio.run(test_reg())
