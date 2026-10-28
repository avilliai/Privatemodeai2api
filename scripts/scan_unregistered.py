import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
import httpx
from app.core.config import settings
from app.services.email_service import OutlookEmailService

async def scan():
    svc = OutlookEmailService(settings)
    clerk_base = settings.PRIVATEMODE_CLERK_URL.rstrip("/")
    headers = {
        "Origin": "https://portal.privatemode.ai",
        "Referer": "https://portal.privatemode.ai/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    }
    
    print("Scanning accounts in outlook_accounts.txt for unregistered email...")
    found = []
    async with httpx.AsyncClient(headers=headers, timeout=15) as client:
        while len(found) < 3:
            try:
                inbox = await svc.create_email()
            except Exception as e:
                print("Pool ended or error:", e)
                break
                
            res = await client.post(
                f"{clerk_base}/client/sign_ups?_clerk_js_version=5",
                data={
                    "first_name": "Test",
                    "last_name": "User",
                    "email_address": inbox.address,
                    "password": "Password123!",
                    "legal_accepted": "true",
                    "captcha_token": "dummy_check",
                }
            )
            body = res.text
            if "form_identifier_exists" in body:
                print(f"[-] {inbox.address} is already registered. Blacklisting...")
                await svc.blacklist(inbox.address, "Already registered on Privatemode")
            else:
                print(f"[+] FOUND UNREGISTERED EMAIL: {inbox.address}! (Response: {res.status_code} {body[:100]})")
                found.append(inbox.address)

    print("Found available emails:", found)

asyncio.run(scan())
