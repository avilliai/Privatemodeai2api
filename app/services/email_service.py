"""Outlook IMAP email service for receiving verification codes, ported from genspark2api."""

from __future__ import annotations

import asyncio
import html
import imaplib
import json
import logging
import re
import time
from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from app.core.config import Settings, resolve_project_path, settings as app_settings
from app.core.exceptions import OutlookImapAuthenticationError, RegistrationError

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class EmailInbox:
    address: str
    token: str  # internal index
    created_at: float = 0.0


@dataclass(slots=True, frozen=True)
class OutlookAccount:
    address: str
    password: str
    client_id: str
    refresh_token: str


def load_outlook_accounts(path: str | Path) -> list[OutlookAccount]:
    """Load email----password----client_id----refresh_token account lines."""
    account_path = resolve_project_path(path)
    if not account_path.is_file():
        raise RegistrationError(f"Outlook account file not found: {account_path}")

    accounts: list[OutlookAccount] = []
    lines = account_path.read_text(encoding="utf-8-sig", errors="ignore").splitlines()
    for line_number, raw_line in enumerate(lines, 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("----", 3)
        if len(parts) != 4 or not all(part.strip() for part in parts):
            continue
        address, password, client_id, refresh_token = (part.strip() for part in parts)
        if "@" not in address:
            continue
        accounts.append(OutlookAccount(address, password, client_id, refresh_token))

    if not accounts:
        raise RegistrationError(f"Outlook account file is empty or has no valid accounts: {account_path}")
    return accounts


class OutlookEmailService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or app_settings
        self._accounts: list[OutlookAccount] = []
        try:
            self._accounts = load_outlook_accounts(self.settings.OUTLOOK_ACCOUNT_FILE)
            logger.info("Loaded %d Outlook accounts from %s", len(self._accounts), self.settings.OUTLOOK_ACCOUNT_FILE)
        except Exception as e:
            logger.warning("Could not load Outlook accounts at startup: %s", e)

        self._blacklist_path = resolve_project_path(self.settings.OUTLOOK_BLACKLIST_FILE)
        self._blacklist = self._load_blacklist()
        self._next_account = 0
        self._lock = asyncio.Lock()

    def get_inbox_by_address(self, address: str):
        target = address.strip().lower()
        for idx, acc in enumerate(self._accounts):
            if acc.address.lower() == target:
                return EmailInbox(address=acc.address, token=str(idx), created_at=time.time())
        return None

    def unblacklist(self, address: str) -> bool:
        target = address.strip().lower()
        if target in self._blacklist:
            del self._blacklist[target]
            try:
                import json
                self._blacklist_path.write_text(json.dumps(self._blacklist, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception as e:
                logger.warning(f"Failed to save blacklist after unblacklist: {e}")
            return True
        return False

    def reload_accounts(self) -> int:
        self._accounts = load_outlook_accounts(self.settings.OUTLOOK_ACCOUNT_FILE)
        return len(self._accounts)

    def _load_blacklist(self) -> dict[str, dict]:
        if not self._blacklist_path.is_file():
            return {}
        try:
            data = json.loads(self._blacklist_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Invalid Outlook blacklist file: %s", exc)
            return {}
        if isinstance(data, list):
            return {str(address).strip().lower(): {} for address in data if str(address).strip()}
        if isinstance(data, dict):
            return {
                str(address).strip().lower(): details if isinstance(details, dict) else {}
                for address, details in data.items()
                if str(address).strip()
            }
        return {}

    def _save_blacklist(self) -> None:
        self._blacklist_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._blacklist_path.with_suffix(self._blacklist_path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(self._blacklist, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self._blacklist_path)

    async def blacklist(self, inbox_or_address: EmailInbox | str, reason: str) -> None:
        address = inbox_or_address.address if isinstance(inbox_or_address, EmailInbox) else inbox_or_address
        async with self._lock:
            self._blacklist[address.strip().lower()] = {
                "reason": reason[:1000],
                "blacklisted_at": int(time.time()),
            }
            self._save_blacklist()
        logger.info("Blacklisted Outlook account %s: %s", address, reason)

    async def blacklist_registered(self, addresses: set[str]) -> int:
        source_addresses = {account.address.strip().lower() for account in self._accounts}
        matches = source_addresses.intersection(
            address.strip().lower() for address in addresses if address.strip()
        )
        async with self._lock:
            new_addresses = matches.difference(self._blacklist)
            for address in new_addresses:
                self._blacklist[address] = {
                    "reason": "Already registered in account pool",
                    "blacklisted_at": int(time.time()),
                }
            if new_addresses:
                self._save_blacklist()
        return len(new_addresses)

    async def create_email(self) -> EmailInbox:
        """Allocate the next unblacklisted Outlook account with verified OAuth token."""
        if not self._accounts:
            self.reload_accounts()

        async with self._lock:
            while self._next_account < len(self._accounts):
                index = self._next_account
                self._next_account += 1
                account = self._accounts[index]
                addr = account.address.strip().lower()
                if addr in self._blacklist:
                    continue
                try:
                    await self._access_token(account)
                    return EmailInbox(
                        address=account.address,
                        token=str(index),
                        created_at=time.time(),
                    )
                except Exception as exc:
                    logger.warning("Outlook account %s invalid/unusable: %s, skipping...", addr, exc)
                    continue
            raise RegistrationError(
                "Outlook account pool is exhausted (all available accounts were skipped or blacklisted)"
            )

    def _account(self, inbox: EmailInbox) -> OutlookAccount:
        try:
            account = self._accounts[int(inbox.token)]
        except (ValueError, IndexError):
            raise RegistrationError("Invalid Outlook inbox handle") from None
        if account.address.lower() != inbox.address.lower():
            raise RegistrationError("Outlook inbox handle does not match its email")
        return account

    async def _access_token(self, account: OutlookAccount) -> str:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            response = await client.post(
                self.settings.OUTLOOK_TOKEN_URL,
                data={
                    "client_id": account.client_id,
                    "grant_type": "refresh_token",
                    "refresh_token": account.refresh_token,
                },
            )
        if response.status_code != 200:
            err_msg = f"Outlook OAuth refresh failed for {account.address}: HTTP {response.status_code} {response.text[:200]}"
            await self.blacklist(account.address, f"OAuth refresh error: HTTP {response.status_code}")
            raise RegistrationError(err_msg)

        data = response.json()
        token = data.get("access_token")
        if not token:
            await self.blacklist(account.address, "OAuth response missing access_token")
            raise RegistrationError(f"Outlook OAuth response missing access_token for {account.address}")
        return str(token)

    async def fetch_messages(self, inbox: EmailInbox) -> list[dict]:
        account = self._account(inbox)
        access_token = await self._access_token(account)
        return await asyncio.to_thread(self._fetch_imap_messages, account, access_token)

    def _fetch_imap_messages(self, account: OutlookAccount, access_token: str) -> list[dict]:
        errors: list[str] = []
        authentication_failed = False
        for host in self.settings.OUTLOOK_IMAP_HOSTS:
            client: imaplib.IMAP4_SSL | None = None
            try:
                client = imaplib.IMAP4_SSL(
                    host,
                    self.settings.OUTLOOK_IMAP_PORT,
                    timeout=self.settings.OUTLOOK_IMAP_TIMEOUT,
                )
                auth = f"user={account.address}\x01auth=Bearer {access_token}\x01\x01".encode("utf-8")
                client.authenticate("XOAUTH2", lambda _challenge: auth)
                messages: list[dict] = []
                for folder in ("INBOX", "Junk"):
                    status, _ = client.select(folder, readonly=True)
                    if status != "OK":
                        continue
                    status, data = client.search(None, "ALL")
                    if status != "OK" or not data:
                        continue
                    message_ids = data[0].split()[-25:]
                    for message_id in reversed(message_ids):
                        status, fetched = client.fetch(message_id, "(RFC822)")
                        if status != "OK" or not fetched:
                            continue
                        raw_bytes = next(
                            (
                                item[1]
                                for item in fetched
                                if isinstance(item, tuple)
                                and len(item) > 1
                                and isinstance(item[1], bytes)
                            ),
                            None,
                        )
                        if raw_bytes is None:
                            continue
                        raw = raw_bytes.decode("utf-8", "replace")
                        parsed = BytesParser(policy=policy.default).parsebytes(raw_bytes)
                        received = ""
                        if parsed.get("Date"):
                            try:
                                received = parsedate_to_datetime(parsed["Date"]).isoformat()
                            except (TypeError, ValueError, OverflowError):
                                pass
                        messages.append(
                            {
                                "id": f"{folder}:{message_id.decode('ascii', 'replace')}",
                                "receivedDateTime": received,
                                "raw": raw,
                            }
                        )
                return messages
            except imaplib.IMAP4.error as exc:
                authentication_failed = True
                errors.append(f"{host}: {str(exc)[:160]}")
            except OSError as exc:
                errors.append(f"{host}: {str(exc)[:160]}")
            finally:
                if client is not None:
                    try:
                        client.logout()
                    except (OSError, imaplib.IMAP4.error):
                        pass

        detail = "; ".join(errors) or "no IMAP hosts configured"
        message = f"Outlook IMAP authentication/fetch failed for {account.address}: {detail}"
        if authentication_failed:
            raise OutlookImapAuthenticationError(message)
        raise RegistrationError(message)

    async def wait_for_code(self, inbox: EmailInbox) -> str:
        deadline = asyncio.get_running_loop().time() + self.settings.EMAIL_POLL_TIMEOUT
        seen: set[str] = set()
        while asyncio.get_running_loop().time() < deadline:
            try:
                messages = await self.fetch_messages(inbox)
            except Exception as e:
                logger.warning("Error fetching emails for %s: %s", inbox.address, e)
                messages = []

            for message in messages:
                received = str(message.get("receivedDateTime") or "")
                raw = str(message.get("raw") or "")
                fingerprint = str(message.get("id") or hash(raw))
                if fingerprint in seen:
                    continue
                seen.add(fingerprint)

                # Ignore emails received well before inbox allocation
                if received:
                    try:
                        from datetime import datetime
                        timestamp = datetime.fromisoformat(received.replace("Z", "+00:00")).timestamp()
                        if timestamp < inbox.created_at - 60:
                            continue
                    except ValueError:
                        pass

                code = extract_verification_code(raw)
                if code:
                    logger.info("Extracted verification code %s for %s", code, inbox.address)
                    return code

            await asyncio.sleep(self.settings.EMAIL_POLL_INTERVAL)

        raise RegistrationError(
            f"Timed out waiting for the verification email sent to {inbox.address}"
        )


def _decode_mime(raw_email: str) -> str:
    try:
        message = BytesParser(policy=policy.default).parsebytes(raw_email.encode("utf-8", "replace"))
    except Exception:
        return raw_email
    parts: list[str] = []
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() not in {"text/plain", "text/html"}:
                continue
            try:
                parts.append(part.get_content())
            except Exception:
                payload = part.get_payload(decode=True) or b""
                parts.append(payload.decode(part.get_content_charset() or "utf-8", "replace"))
    else:
        try:
            parts.append(message.get_content())
        except Exception:
            parts.append(raw_email)
    return "\n".join(parts)


def extract_verification_code(raw_email: str) -> str | None:
    """Extract 6-digit OTP code from email text or HTML."""
    content = html.unescape(_decode_mime(raw_email))
    content = BeautifulSoup(content, "html.parser").get_text(" ")
    content = re.sub(r"\s+", " ", content)

    # Clerk specific patterns or general OTP
    preferred = [
        r"(?:verification|security|confirmation|one[- ]time|OTP|code)\s*(?:code)?\s*[:：]?\s*([0-9]{6})",
        r"(?:验证码|驗證碼)\s*[:：]?\s*([0-9]{6})",
        r"\b([0-9]{6})\b",
    ]
    for pattern in preferred:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group(1)
    return None
