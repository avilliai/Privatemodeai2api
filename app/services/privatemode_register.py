"""Privatemode account registration and API key generation orchestration."""

from __future__ import annotations

import asyncio
import logging
import random
import secrets
import string
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app.core.config import Settings, settings as app_settings
from app.core.exceptions import OutlookImapAuthenticationError,  RegistrationError, TurnstileError
from app.services.account_manager import AccountManager, AccountRecord
from app.services.email_service import EmailInbox, OutlookEmailService
from app.services.turnstile_service import TurnstileService

logger = logging.getLogger(__name__)

FIRST_NAMES = [
    "Alex", "David", "James", "John", "Robert", "Michael", "William",
    "Emma", "Olivia", "Sophia", "Lucas", "Oliver", "Daniel", "Thomas"
]
LAST_NAMES = [
    "Smith", "Johnson", "Brown", "Taylor", "Miller", "Wilson", "Moore",
    "Davis", "Anderson", "Clark", "Hall", "Allen", "Young", "Wright"
]


def generate_password(length: int = 16) -> str:
    length = max(12, length)
    required = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%._-"),
    ]
    alphabet = string.ascii_letters + string.digits + "!@#$%._-"
    required.extend(secrets.choice(alphabet) for _ in range(length - len(required)))
    random.SystemRandom().shuffle(required)
    return "".join(required)


def generate_org_name() -> str:
    adjectives = ["Nova", "Apex", "Echo", "Flux", "Nexus", "Vortex", "Pulse", "Quantum", "Hyper", "Cyber"]
    nouns = ["Labs", "AI", "Tech", "Systems", "Studio", "Cloud", "Works", "Group", "Dynamics", "Hub"]
    return f"{random.choice(adjectives)} {random.choice(nouns)} {random.randint(10, 99)}"


class RegisterService:
    _recovering_emails: set[str] = set()

    async def trigger_background_recovery(self, email: str) -> None:
        """Trigger non-blocking background recovery for an account that hit 401 invalid key."""
        email_clean = email.strip()
        if email_clean in self._recovering_emails:
            return
        self._recovering_emails.add(email_clean)

        async def _worker():
            try:
                logger.info("[Auto-Recovery] 正在为失效账号 %s 在后台自动恢复并刷新 API Key...", email_clean)
                await self.recover_single_account(email_clean)
                logger.info("[Auto-Recovery] 账号 %s 自动恢复完成，已重新生效上线！", email_clean)
            except Exception as e:
                logger.warning("[Auto-Recovery] 账号 %s 自动恢复失败: %s", email_clean, e)
            finally:
                self._recovering_emails.discard(email_clean)

        asyncio.create_task(_worker())

    def __init__(
        self,
        settings: Settings | None = None,
        account_manager: AccountManager | None = None,
        email_service: OutlookEmailService | None = None,
        turnstile_service: TurnstileService | None = None,
    ):
        self.settings = settings or app_settings
        self.account_manager = account_manager or AccountManager(self.settings)
        self.email_service = email_service or OutlookEmailService(self.settings)
        self.turnstile_service = turnstile_service or TurnstileService(self.settings)
        self.jobs: dict[str, dict[str, Any]] = {}
        self.tasks: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    def _log_job(self, job_id: Optional[str], message: str, level: str = "info") -> None:
        logger.info(message)
        if job_id and job_id in self.jobs:
            now_str = datetime.now().strftime("%H:%M:%S")
            self.jobs[job_id]["logs"].append({
                "time": now_str,
                "level": level,
                "message": message,
            })

    async def register_single_account(self, job_id: Optional[str] = None, max_retries: int = 15) -> AccountRecord:
        """Execute one full account registration flow and create its API key.
        Automatically retries with the next Outlook account if an email is already taken.
        """
        for attempt in range(1, max_retries + 1):
            inbox = await self.email_service.create_email()
            email = inbox.address
            password = generate_password(self.settings.REGISTER_PASSWORD_LENGTH)
            first_name = random.choice(FIRST_NAMES)
            last_name = random.choice(LAST_NAMES)
            org_name = generate_org_name()

            self._log_job(job_id, f"[{email}] 准备注册 Privatemode 账号 (尝试 {attempt}/{max_retries})...")

            try:
                record = await self._register_via_api(
                    inbox=inbox,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    org_name=org_name,
                    job_id=job_id,
                )
                return record
            except Exception as api_err:
                err_str = str(api_err)
                if "form_identifier_exists" in err_str or "email address is taken" in err_str.lower():
                    self._log_job(job_id, f"[{email}] 邮箱已被注册，已加入黑名单并自动切换下一个邮箱...", level="warning")
                    await self.email_service.blacklist(inbox, "Email already registered in Privatemode")
                    continue

                self._log_job(job_id, f"[{email}] 注册遇到异常: {api_err}", level="error")
                await self.email_service.blacklist(inbox, f"Registration failed: {api_err}")
                if attempt == max_retries:
                    raise RegistrationError(f"Registration failed after {max_retries} attempts: {api_err}") from api_err

        raise RegistrationError(f"Failed to find an unregistered Outlook account after {max_retries} attempts")

    async def _register_via_api(
        self,
        inbox: EmailInbox,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        org_name: str,
        job_id: Optional[str] = None,
    ) -> AccountRecord:
        """Register account via Clerk REST API + Privatemode SaaS API."""
        # 1. Obtain Turnstile token
        self._log_job(job_id, f"[{email}] 正在使用 Turnstile Solver 自动过验证码...")
        captcha_token = await self.turnstile_service.solve(
            url="https://portal.privatemode.ai/",
            sitekey=self.settings.TURNSTILE_SITEKEY,
        )
        if not captcha_token:
            raise TurnstileError("Failed to obtain Cloudflare Turnstile token")

        self._log_job(job_id, f"[{email}] Turnstile 验证码已成功破解 (Token长度: {len(captcha_token)})")

        clerk_base = self.settings.PRIVATEMODE_CLERK_URL.rstrip("/")
        headers = {
            "Origin": "https://portal.privatemode.ai",
            "Referer": "https://portal.privatemode.ai/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        }

        async with httpx.AsyncClient(headers=headers, timeout=30, follow_redirects=True) as client:
            # 2. Clerk sign up
            self._log_job(job_id, f"[{email}] 提交 Clerk 注册请求...")
            signup_payload = {
                "first_name": first_name,
                "last_name": last_name,
                "email_address": email,
                "password": password,
                "legal_accepted": "true",
                "captcha_token": captcha_token,
            }
            res = await client.post(
                f"{clerk_base}/client/sign_ups?_clerk_js_version=5",
                data=signup_payload,
            )
            if res.status_code not in (200, 201):
                raise RegistrationError(f"Clerk sign_up failed: HTTP {res.status_code} {res.text[:300]}")

            signup_data = res.json()
            response_obj = signup_data.get("response") or signup_data
            signup_id = response_obj.get("id")
            if not signup_id:
                raise RegistrationError(f"Clerk sign_up response missing id: {signup_data}")

            # 3. Prepare email code verification
            self._log_job(job_id, f"[{email}] 请求向 Outlook 邮箱下发 6 位验证码...")
            res = await client.post(
                f"{clerk_base}/client/sign_ups/{signup_id}/prepare_verification?_clerk_js_version=5",
                data={"strategy": "email_code"},
            )
            if res.status_code not in (200, 201):
                raise RegistrationError(f"Prepare verification failed: HTTP {res.status_code} {res.text[:200]}")

            # 4. Wait for email code via Outlook IMAP
            self._log_job(job_id, f"[{email}] 正在通过 Outlook IMAP 轮询提取邮件验证码...")
            code = await self.email_service.wait_for_code(inbox)
            self._log_job(job_id, f"[{email}] 成功截获 6 位验证码: {code}")

            # 5. Attempt email verification
            self._log_job(job_id, f"[{email}] 提交验证码完成邮箱校验...")
            res = await client.post(
                f"{clerk_base}/client/sign_ups/{signup_id}/attempt_verification?_clerk_js_version=5",
                data={"strategy": "email_code", "code": code},
            )
            if res.status_code not in (200, 201):
                raise RegistrationError(f"Verification code attempt failed: HTTP {res.status_code} {res.text[:200]}")

            verify_data = res.json()
            verify_obj = verify_data.get("response") or verify_data
            session_id = verify_obj.get("created_session_id")

            if not session_id:
                client_obj = (verify_data.get("client") or {}).get("sessions") or []
                if client_obj:
                    session_id = client_obj[0].get("id")

            if not session_id:
                raise RegistrationError(f"Sign up completed but missing created_session_id: {verify_data}")

            # 6. Fetch user session JWT token & cookies
            self._log_job(job_id, f"[{email}] 获取用户 Session 凭据...")
            # In Clerk frontend API, session token requires client cookies (__session, __client) or session endpoint
            res = await client.post(
                f"{clerk_base}/client/sessions/{session_id}/tokens?_clerk_js_version=5",
                data={},
            )
            user_jwt = None
            if res.status_code in (200, 201):
                user_jwt = res.json().get("jwt")

            # 7. Create Organization in Clerk
            self._log_job(job_id, f"[{email}] 创建 Organization '{org_name}'...")
            # First try using existing client with cookies
            res = await client.post(
                f"{clerk_base}/organizations?_clerk_js_version=5",
                data={"name": org_name},
            )
            # If not authorized, try with Authorization Bearer header
            if res.status_code == 401 and user_jwt:
                res = await client.post(
                    f"{clerk_base}/organizations?_clerk_js_version=5",
                    headers={"Authorization": f"Bearer {user_jwt}"},
                    data={"name": org_name},
                )

            if res.status_code not in (200, 201):
                raise RegistrationError(f"Failed to create organization in Clerk: HTTP {res.status_code} {res.text[:200]}")
            org_data = res.json().get("response") or res.json()
            org_id = org_data.get("id")
            if not org_id:
                raise RegistrationError(f"Organization creation missing id: {org_data}")

            # 8. Fetch org-scoped JWT token
            self._log_job(job_id, f"[{email}] 签发 Organization 专属 JWT Token...")
            res = await client.post(
                f"{clerk_base}/client/sessions/{session_id}/tokens?organization_id={org_id}&_clerk_js_version=5",
                data={},
            )
            if res.status_code not in (200, 201) and user_jwt:
                res = await client.post(
                    f"{clerk_base}/client/sessions/{session_id}/tokens?organization_id={org_id}&_clerk_js_version=5",
                    headers={"Authorization": f"Bearer {user_jwt}"},
                    data={},
                )
            if res.status_code not in (200, 201):
                raise RegistrationError(f"Failed to get org-scoped token: HTTP {res.status_code} {res.text[:200]}")
            org_jwt = res.json().get("jwt")
            if not org_jwt:
                raise RegistrationError(f"Missing org-scoped jwt in response: {res.json()}")
            # 9. Initialize & Verify Organization in Privatemode SaaS backend
        saas_base = self.settings.PRIVATEMODE_SAAS_URL.rstrip("/")
        async with httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {org_jwt}",
                "Content-Type": "application/json",
                "Origin": "https://portal.privatemode.ai",
                "Referer": "https://portal.privatemode.ai/",
            },
            timeout=30,
        ) as saas_client:
            self._log_job(job_id, f"[{email}] 在 Privatemode 后端激活并初始化 Organization...")
            org_payload = {
                "industry": "software_it",
                "developer_count": "1_20",
                "use_cases": ["chat", "coding_assistant"],
            }
            # Provision organization on SaaS backend (retry up to 3 times to guarantee persistence)
            provisioned = False
            for p_att in range(1, 4):
                res = await saas_client.post(f"{saas_base}/api/v2/organizations", json=org_payload)
                if res.status_code in (200, 201, 204):
                    # Verify organization is recognized
                    v_res = await saas_client.get(f"{saas_base}/api/v2/organizations")
                    if v_res.status_code == 200:
                        provisioned = True
                        break
                await asyncio.sleep(1.0)

            if not provisioned:
                raise RegistrationError(f"Failed to provision and verify organization for {email} in Privatemode SaaS")

            # 10. Create API key in Privatemode SaaS backend
            self._log_job(job_id, f"[{email}] 正在为该账号生成专属 API Key (共享对话配额)...")
            exp_year = datetime.now(timezone.utc).year + 2
            key_payload = {
                "name": "default-key",
                "comment": "Auto-created 2API key",
                "expiration_date": f"{exp_year}-12-31",
            }
            res = await saas_client.post(f"{saas_base}/api/v3/keys", json=key_payload)
            if res.status_code not in (200, 201):
                raise RegistrationError(f"Failed to create API key in Privatemode backend: HTTP {res.status_code} {res.text[:300]}")

            key_data = res.json()
            license_key = key_data.get("license_key")
            key_id = key_data.get("key_id", "")
            if not license_key:
                raise RegistrationError(f"API key response missing license_key: {key_data}")

            self._log_job(job_id, f"[{email}] 🎉 注册与 API Key 创建成功! Key: {license_key[:8]}...{license_key[-4:]}")

        # 11. Add to AccountManager pool
        record = await self.account_manager.add_account(
            email=email,
            password=password,
            api_key=license_key,
            key_id=key_id,
            org_id=org_id,
            session_id=session_id,
            metadata={
                "org_name": org_name,
                "first_name": first_name,
                "last_name": last_name,
            },
        )
        return record

    def start_background_job(self, count: int = 1, concurrency: int = 1) -> str:
        """Start background registration job for `count` accounts."""
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {
            "job_id": job_id,
            "status": "running",
            "requested": count,
            "succeeded": 0,
            "failed": 0,
            "created_accounts": [],
            "errors": [],
            "logs": [],
            "started_at": time.time(),
            "finished_at": None,
        }
        self._log_job(job_id, f"🚀 启动批量注册任务，目标数量: {count} 个账号")

        concurrency = max(1, min(concurrency, 10))
        self.jobs[job_id]["concurrency"] = concurrency
        task = asyncio.create_task(self._run_job(job_id, count, concurrency))
        self.tasks[job_id] = task
        return job_id

    async def _run_job(self, job_id: str, count: int, concurrency: int = 1) -> None:
        job = self.jobs[job_id]
        self.jobs[job_id]["concurrency"] = concurrency
        sem = asyncio.Semaphore(concurrency)
        counter_lock = asyncio.Lock()
        completed_count = 0

        async def worker(worker_idx: int):
            nonlocal completed_count
            async with sem:
                self._log_job(job_id, f"--- [Worker #{worker_idx + 1}] 开始处理账号注册任务 ---")
                try:
                    acc = await self.register_single_account(job_id=job_id)
                    async with counter_lock:
                        completed_count += 1
                        job["succeeded"] += 1
                        job["created_accounts"].append({
                            "email": acc.email,
                            "api_key_masked": acc.api_key[:8] + "..." + acc.api_key[-4:] if len(acc.api_key) > 12 else "***",
                            "status": acc.status,
                        })
                        cur_done = completed_count
                    self._log_job(job_id, f"✅ [进度 {cur_done}/{count}] 账号 {acc.email} 注册成功并存入账号池！")
                except Exception as e:
                    logger.error("Job %s worker %d failed: %s", job_id, worker_idx + 1, e)
                    async with counter_lock:
                        completed_count += 1
                        job["failed"] += 1
                        job["errors"].append(str(e))
                        cur_done = completed_count
                    self._log_job(job_id, f"❌ [进度 {cur_done}/{count}] 账号注册失败: {e}", level="error")

                await asyncio.sleep(1)

        tasks = [asyncio.create_task(worker(i)) for i in range(count)]
        await asyncio.gather(*tasks, return_exceptions=True)

        job["status"] = "completed" if job["failed"] == 0 else ("partial" if job["succeeded"] > 0 else "failed")
        job["finished_at"] = time.time()
        self._log_job(job_id, f"🏁 批量注册任务执行完毕: 目标 {count} 个, 成功 {job['succeeded']} 个, 失败 {job['failed']} 个 (并发数: {concurrency})")

    async def recover_single_account(self, email: str, job_id: Optional[str] = None) -> AccountRecord:
        """Recover an already-registered Privatemode account via Clerk sign-in & IMAP OTP."""
        email = email.strip()
        inbox = self.email_service.get_inbox_by_address(email)
        if not inbox:
            raise RegistrationError(f"Email {email} not found in Outlook account file")

        self._log_job(job_id, f"[{email}] 正在找回已注册账号，请求 Turnstile Solver 求解人机验证...")
        captcha_token = await self.turnstile_service.solve(
            url="https://portal.privatemode.ai/",
            sitekey=self.settings.TURNSTILE_SITEKEY,
        )
        if not captcha_token:
            raise TurnstileError("Failed to obtain Turnstile token for account recovery")

        clerk_base = self.settings.PRIVATEMODE_CLERK_URL.rstrip("/")
        headers = {
            "Origin": "https://portal.privatemode.ai",
            "Referer": "https://portal.privatemode.ai/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        }

        async with httpx.AsyncClient(headers=headers, timeout=30, follow_redirects=True) as client:
            # 1. Clerk sign_in
            self._log_job(job_id, f"[{email}] 发起 Clerk 登录流程...")
            res = await client.post(
                f"{clerk_base}/client/sign_ins?_clerk_js_version=5",
                data={"identifier": email, "captcha_token": captcha_token},
            )
            if res.status_code not in (200, 201):
                raise RegistrationError(f"Clerk sign_in initiation failed: HTTP {res.status_code} {res.text[:300]}")

            resp_data = res.json().get("response") or res.json()
            sia_id = resp_data.get("id")
            factors = resp_data.get("supported_first_factors", [])
            email_factor = next((f for f in factors if f.get("strategy") == "email_code"), None)
            if not email_factor or not sia_id:
                raise RegistrationError(f"Clerk sign_in missing email_code factor or ID: {resp_data}")

            # 2. Prepare email code factor
            self._log_job(job_id, f"[{email}] 准备发送 Outlook 邮箱登录验证码...")
            res = await client.post(
                f"{clerk_base}/client/sign_ins/{sia_id}/prepare_first_factor?_clerk_js_version=5",
                data={"strategy": "email_code", "email_address_id": email_factor["email_address_id"]},
            )
            if res.status_code not in (200, 201):
                raise RegistrationError(f"Prepare first factor failed: HTTP {res.status_code} {res.text[:200]}")

            # 3. Wait for email code via IMAP
            self._log_job(job_id, f"[{email}] 正在从 Outlook IMAP 邮箱获取验证码...")
            code = await self.email_service.wait_for_code(inbox)
            self._log_job(job_id, f"[{email}] 成功截获 6 位登录验证码: {code}")

            # 4. Attempt first factor
            self._log_job(job_id, f"[{email}] 正在提交验证码校验...")
            res = await client.post(
                f"{clerk_base}/client/sign_ins/{sia_id}/attempt_first_factor?_clerk_js_version=5",
                data={"strategy": "email_code", "code": code},
            )
            if res.status_code not in (200, 201):
                raise RegistrationError(f"Verification code attempt failed: HTTP {res.status_code} {res.text[:200]}")

            attempt_obj = res.json().get("response") or res.json()
            session_id = attempt_obj.get("created_session_id")
            if not session_id:
                client_obj = (res.json().get("client") or {}).get("sessions") or []
                if client_obj:
                    session_id = client_obj[0].get("id")
            if not session_id:
                raise RegistrationError(f"Sign in completed but missing session_id: {res.json()}")

            # 5. Check if user already has an organization
            res = await client.get(f"{clerk_base}/client/sessions/{session_id}?_clerk_js_version=5")
            session_info = res.json().get("response") or res.json()
            user_info = session_info.get("user") or {}
            org_memberships = user_info.get("organization_memberships") or []

            org_id = None
            org_name = "Recovered Org"
            if org_memberships:
                org_obj = org_memberships[0].get("organization") or {}
                org_id = org_obj.get("id")
                org_name = org_obj.get("name", org_name)
                self._log_job(job_id, f"[{email}] 检测到已有 Organization: {org_name} ({org_id})")
            else:
                org_name = generate_org_name()
                self._log_job(job_id, f"[{email}] 自动新建 Organization 工作空间: '{org_name}'...")
                res = await client.post(
                    f"{clerk_base}/organizations?_clerk_js_version=5",
                    data={"name": org_name},
                )
                if res.status_code not in (200, 201):
                    raise RegistrationError(f"Failed to create organization: HTTP {res.status_code} {res.text[:200]}")
                org_data = res.json().get("response") or res.json()
                org_id = org_data.get("id")

            # 6. Fetch org-scoped JWT token
            self._log_job(job_id, f"[{email}] 正在获取 Organization 作用域 JWT Token...")
            res = await client.post(
                f"{clerk_base}/client/sessions/{session_id}/tokens?organization_id={org_id}&_clerk_js_version=5",
                data={},
            )
            if res.status_code not in (200, 201):
                raise RegistrationError(f"Failed to get org-scoped token: HTTP {res.status_code} {res.text[:200]}")
            org_jwt = res.json().get("jwt")
            if not org_jwt:
                raise RegistrationError(f"Missing org-scoped jwt: {res.json()}")

        # 7. Check or create API key in Privatemode SaaS backend
        saas_base = self.settings.PRIVATEMODE_SAAS_URL.rstrip("/")
        async with httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {org_jwt}",
                "Content-Type": "application/json",
                "Origin": "https://portal.privatemode.ai",
                "Referer": "https://portal.privatemode.ai/",
            },
            timeout=30,
        ) as saas_client:
            # Init organization on SaaS backend (safe to repeat)
            await saas_client.post(
                f"{saas_base}/api/v2/organizations",
                json={
                    "industry": "software_it",
                    "developer_count": "1_20",
                    "use_cases": ["chat", "coding_assistant"],
                },
            )

            # Query existing keys and clean up old/masked keys
            license_key = None
            key_id = ""
            res = await saas_client.get(f"{saas_base}/api/v3/keys")
            if res.status_code in (200, 201):
                existing_keys = res.json()
                if isinstance(existing_keys, list) and existing_keys:
                    for k in existing_keys:
                        # Privatemode masks keys on subsequent GETs. Delete old invalid keys so we can create a working one.
                        if not k.get("license_key") and k.get("key_id"):
                            try:
                                await saas_client.delete(f"{saas_base}/api/v3/keys/{k['key_id']}")
                            except Exception:
                                pass
                        elif k.get("license_key"):
                            license_key = k["license_key"]
                            key_id = k.get("key_id", "")
                            break

            # If no existing license key found or readable, create a fresh one
            if not license_key:
                self._log_job(job_id, f"[{email}] 正在创建全新的 License API Key...")
                exp_year = datetime.now(timezone.utc).year + 2
                res = await saas_client.post(
                    f"{saas_base}/api/v3/keys",
                    json={
                        "name": "recovered-key",
                        "comment": "Recovered 2API key",
                        "expiration_date": f"{exp_year}-12-31",
                    },
                )
                if res.status_code not in (200, 201):
                    raise RegistrationError(f"Failed to create key on Privatemode SaaS: HTTP {res.status_code} {res.text[:200]}")
                key_data = res.json()
                license_key = key_data.get("license_key")
                key_id = key_data.get("key_id", "")

            if not license_key:
                raise RegistrationError("Could not retrieve or create license_key")

            self._log_job(job_id, f"[{email}] 账号找回成功! License Key: {license_key[:8]}...{license_key[-4:]}")

        # 8. Unblacklist from Outlook email service
        self.email_service.unblacklist(email)

        # 9. Add or update account in AccountManager
        record = await self.account_manager.add_account(
            email=email,
            password="",
            api_key=license_key,
            key_id=key_id,
            org_id=org_id or "",
            session_id=session_id or "",
            metadata={
                "org_name": org_name,
                "recovered": True,
                "recovered_at": time.time(),
            },
        )
        return record

    def start_recovery_job(self, emails: list[str], concurrency: int = 3) -> str:
        """Start background recovery job for specified emails with concurrency support."""
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {
            "job_id": job_id,
            "status": "running",
            "requested": len(emails),
            "succeeded": 0,
            "failed": 0,
            "created_accounts": [],
            "errors": [],
            "logs": [],
            "started_at": time.time(),
            "finished_at": None,
        }
        self._log_job(job_id, f"启动批量账号找回任务: 共 {len(emails)} 个账号 (并发数: {concurrency})")

        task = asyncio.create_task(self._run_recovery_job(job_id, emails, concurrency=concurrency))
        self.tasks[job_id] = task
        return job_id

    async def _run_recovery_job(self, job_id: str, emails: list[str], concurrency: int = 3) -> None:
        job = self.jobs[job_id]
        total = len(emails)
        semaphore = asyncio.Semaphore(max(1, concurrency))
        lock = asyncio.Lock()
        completed_count = 0

        async def _worker(idx: int, email: str):
            nonlocal completed_count
            async with semaphore:
                self._log_job(job_id, f"--- 开始恢复 [{idx + 1}/{total}]: {email} ---")
                try:
                    acc = await self.recover_single_account(email, job_id=job_id)
                    async with lock:
                        job["succeeded"] += 1
                        job["created_accounts"].append({
                            "email": acc.email,
                            "api_key_masked": acc.api_key[:8] + "..." + acc.api_key[-4:] if len(acc.api_key) > 12 else "***",
                            "status": acc.status,
                        })
                        completed_count += 1
                    self._log_job(job_id, f"✅ [{completed_count}/{total}] 账号 {email} 成功找回并已签发新Key！")
                except (OutlookImapAuthenticationError, Exception) as e:
                    err_str = str(e)
                    is_imap_err = isinstance(e, OutlookImapAuthenticationError) or "User is authenticated but not connected" in err_str
                    if is_imap_err:
                        logger.error("Recovery job %s for %s: Outlook IMAP rejected: %s", job_id, email, err_str)
                        acc_rec = await self.account_manager.get_account_by_email(email)
                        if acc_rec:
                            acc_rec.disabled = True
                            acc_rec.status = "disabled"
                            acc_rec.error = f"Outlook IMAP已失效: {err_str[:80]}"
                            await self.account_manager.save_accounts()
                        async with lock:
                            job["failed"] += 1
                            job["errors"].append(f"{email}: Outlook邮箱已失效")
                            completed_count += 1
                        self._log_job(job_id, f"⛔ [{completed_count}/{total}] 账号 {email} Outlook 邮箱已不可用，已自动标记为【禁用】", level="error")
                    else:
                        logger.error("Recovery job %s for %s failed: %s", job_id, email, e)
                        async with lock:
                            job["failed"] += 1
                            job["errors"].append(f"{email}: {e}")
                            completed_count += 1
                        self._log_job(job_id, f"❌ [{completed_count}/{total}] 账号 {email} 找回失败: {e}", level="error")

                # 任务完成后稍作微弱间隔，错开并发请求
                await asyncio.sleep(0.5)

        # 启动所有协程
        tasks = [_worker(i, em) for i, em in enumerate(emails)]
        await asyncio.gather(*tasks)

        job["status"] = "completed" if job["failed"] == 0 else ("partial" if job["succeeded"] > 0 else "failed")
        job["finished_at"] = time.time()
        self._log_job(job_id, f"🎉 批量找回任务结束！成功: {job['succeeded']}, 失败: {job['failed']} (总共 {total})")
