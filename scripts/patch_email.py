import sys

with open("app/services/email_service.py", "r", encoding="utf-8") as f:
    code = f.read()

target = """    async def create_email(self) -> EmailInbox:
        \"\"\"Allocate the next unblacklisted Outlook account.\"\"\"
        if not self._accounts:
            self.reload_accounts()

        async with self._lock:
            while self._next_account < len(self._accounts):
                index = self._next_account
                self._next_account += 1
                account = self._accounts[index]
                if account.address.strip().lower() not in self._blacklist:
                    return EmailInbox(
                        address=account.address,
                        token=str(index),
                        created_at=time.time(),
                    )
            raise RegistrationError(
                "Outlook account pool is exhausted (all available accounts were skipped or blacklisted)"
            )"""

replacement = """    async def create_email(self) -> EmailInbox:
        \"\"\"Allocate the next unblacklisted Outlook account with verified OAuth token.\"\"\"
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
            )"""

if target in code:
    code = code.replace(target, replacement)
    with open("app/services/email_service.py", "w", encoding="utf-8") as f:
        f.write(code)
    print("Updated email_service.py successfully!")
else:
    print("Target not found!")
