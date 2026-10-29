"""Privatemode upstream client for forwarding OpenAI-compatible chat completions."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, AsyncGenerator

import httpx

from app.core.config import Settings, settings as app_settings
from app.core.exceptions import (
    AccountPoolError,
    PrivatemodeError,
    QuotaExceededError,
    UpstreamError,
)
from app.services.account_manager import AccountManager, AccountRecord

logger = logging.getLogger(__name__)



# Model rate limit and quota multipliers per Privatemode official docs:
# GLM-5.3 is baseline (1.0). Effective Usage = Token Count x Model Multiplier
MODEL_MULTIPLIERS: dict[str, float] = {
    "deepseek-ocr-2": 1.0,
    "glm-5.3": 1.0,
    "glm-latest": 1.0,
    "glm-5.3-flash": 1.0,
    "glm-flash-latest": 1.0,
    "gpt-oss-120b": 2.0,
    "qwen3-embedding-4b": 0.5,
    "voxtral-mini-3b": 1.0,
    "whisper-large-v3": 1.0,
}

def get_model_multiplier(model_name: str) -> float:
    m = model_name.lower().strip()
    return MODEL_MULTIPLIERS.get(m, 1.0)


class PrivatemodeClient:
    def __init__(
        self,
        settings: Settings | None = None,
        account_manager: AccountManager | None = None,
        register_service: Any | None = None,
    ):
        self.settings = settings or app_settings
        self.account_manager = account_manager or AccountManager(self.settings)
        self._register_service = register_service

    
    def _trigger_auto_recovery(self, email: str) -> None:
        try:
            if self._register_service is None:
                from app.services.privatemode_register import RegisterService
                self._register_service = RegisterService(self.settings, self.account_manager)
            import asyncio
            asyncio.create_task(self._register_service.trigger_background_recovery(email))
        except Exception as exc:
            logger.warning("Could not spawn auto recovery for %s: %s", email, exc)

    def resolve_model(self, requested_model: str) -> str:
        """Resolve model aliases to Privatemode supported models."""
        aliases = self.settings.model_aliases
        if requested_model in aliases:
            return aliases[requested_model]
        if requested_model in self.settings.models_list:
            return requested_model
        # Default fallback
        return self.settings.DEFAULT_MODEL

    async def chat_completion(
        self,
        payload: dict[str, Any],
        max_account_retries: int = 3,
    ) -> dict[str, Any]:
        """Non-streaming chat completion with automatic account failover."""
        return await self._non_streaming(payload, "chat/completions", max_account_retries)

    async def embeddings(
        self, payload: dict[str, Any], max_account_retries: int = 3,
    ) -> dict[str, Any]:
        """Forward embeddings through the same account pool and usage accounting."""
        model = payload["model"]
        resolved = self.settings.model_aliases.get(model, model)
        # Never silently substitute a chat model for an embedding model.
        if resolved not in self.settings.models_list or "embedding" not in resolved:
            raise UpstreamError("Unsupported embedding model", status_code=400)
        return await self._non_streaming(dict(payload), "embeddings", max_account_retries)

    async def _non_streaming(
        self, payload: dict[str, Any], endpoint_path: str, max_account_retries: int,
    ) -> dict[str, Any]:
        # Normalize model
        model = payload.get("model", self.settings.DEFAULT_MODEL)
        payload["model"] = self.resolve_model(model)
        if endpoint_path == "chat/completions":
            payload["stream"] = False

        endpoint = f"{self.settings.PRIVATEMODE_PROXYLESS_URL.rstrip('/')}/{endpoint_path}"

        last_error: Exception | None = None
        for attempt in range(max_account_retries):
            account: AccountRecord = await self.account_manager.get_next_account()
            headers = {
                "Authorization": f"Bearer {account.api_key}",
                "Content-Type": "application/json",
            }

            try:
                async with httpx.AsyncClient(timeout=self.settings.REQUEST_TIMEOUT) as client:
                    response = await client.post(endpoint, json=payload, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    # Ensure requested model name is returned in response
                    data["model"] = model

                    # Calculate token usage and multiplier
                    usage = data.get("usage") or {}
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
                    multiplier = get_model_multiplier(payload.get("model", model))
                    effective_tokens = int(total_tokens * multiplier)

                    if hasattr(self.account_manager, "record_usage"):
                        await self.account_manager.record_usage(
                            account=account,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            effective_tokens=effective_tokens,
                        )
                    else:
                        await self.account_manager.mark_success(account)
                    return data

                # Handle errors
                status_code = response.status_code
                error_body = response.text[:500]
                if endpoint_path == "embeddings" and status_code in (400, 404, 422):
                    # Input/route errors say nothing about account health.
                    raise UpstreamError(
                        f"Privatemode upstream returned HTTP {status_code}: {error_body}",
                        status_code=status_code,
                    )
                logger.warning(
                    "Upstream error HTTP %d for account %s: %s",
                    status_code,
                    account.email,
                    error_body,
                )

                if status_code in (429,):
                    await self.account_manager.mark_failure(account, "rate_limit", error_body)
                elif status_code in (401, 403):
                    await self.account_manager.mark_failure(account, "auth", error_body)
                    if "invalid api key" in error_body.lower() or status_code == 401:
                        self._trigger_auto_recovery(account.email)
                elif "quota" in error_body.lower() or "balance" in error_body.lower() or "credit" in error_body.lower():
                    await self.account_manager.mark_failure(account, "quota_exceeded", error_body)
                else:
                    await self.account_manager.mark_failure(account, "upstream_error", error_body)

                last_error = UpstreamError(
                    f"Privatemode upstream returned HTTP {status_code}: {error_body}",
                    status_code=status_code,
                )

            except httpx.RequestError as exc:
                logger.warning("Network error calling upstream with account %s: %s", account.email, exc)
                await self.account_manager.mark_failure(account, "network_error", str(exc))
                last_error = UpstreamError(f"Network error communicating with Privatemode: {exc}")

        raise last_error or UpstreamError("Failed to get response after trying available accounts")

    async def stream_chat_completion(
        self,
        payload: dict[str, Any],
        max_account_retries: int = 3,
    ) -> AsyncGenerator[bytes, None]:
        """Streaming chat completion yielding SSE chunks directly."""
        model = payload.get("model", self.settings.DEFAULT_MODEL)
        payload["model"] = self.resolve_model(model)
        payload["stream"] = True

        endpoint = f"{self.settings.PRIVATEMODE_PROXYLESS_URL.rstrip('/')}/chat/completions"

        for attempt in range(max_account_retries):
            account: AccountRecord = await self.account_manager.get_next_account()
            headers = {
                "Authorization": f"Bearer {account.api_key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            }

            try:
                client = httpx.AsyncClient(timeout=self.settings.REQUEST_TIMEOUT)
                req = client.build_request("POST", endpoint, json=payload, headers=headers)
                response = await client.send(req, stream=True)

                if response.status_code == 200:
                    # In streaming mode, track tokens through SSE chunks or completion
                    multiplier = get_model_multiplier(payload.get("model", model))
                    recorded_usage = False
                    prompt_tokens_est = 0
                    completion_tokens_est = 0

                    try:
                        async for chunk in response.aiter_raw():
                            yield chunk
                            # Attempt to parse usage from stream chunks if provided by upstream
                            try:
                                chunk_str = chunk.decode("utf-8", "ignore")
                                for line in chunk_str.splitlines():
                                    line = line.strip()
                                    if line.startswith("data: ") and line != "data: [DONE]":
                                        cdata = json.loads(line[6:])
                                        if "usage" in cdata and cdata["usage"]:
                                            u = cdata["usage"]
                                            p_tok = u.get("prompt_tokens", 0)
                                            c_tok = u.get("completion_tokens", 0)
                                            eff_tok = int(u.get("total_tokens", p_tok + c_tok) * multiplier)
                                            if hasattr(self.account_manager, "record_usage"):
                                                await self.account_manager.record_usage(
                                                    account=account,
                                                    prompt_tokens=p_tok,
                                                    completion_tokens=c_tok,
                                                    effective_tokens=eff_tok,
                                                )
                                                recorded_usage = True
                                        elif "choices" in cdata:
                                            # Estimate output tokens roughly by completion deltas
                                            for ch in cdata["choices"]:
                                                delta = ch.get("delta", {})
                                                if delta.get("content"):
                                                    completion_tokens_est += max(1, len(delta["content"]) // 3)
                            except Exception:
                                pass
                    finally:
                        await response.aclose()
                        await client.aclose()

                    if not recorded_usage:
                        # Fallback approximate usage if upstream SSE didn't send usage block
                        # Prompt tokens roughly estimated from messages
                        msgs = payload.get("messages", [])
                        prompt_tokens_est = sum(len(m.get("content", "")) // 3 + 4 for m in msgs)
                        total_est = prompt_tokens_est + max(1, completion_tokens_est)
                        eff_est = int(total_est * multiplier)
                        if hasattr(self.account_manager, "record_usage"):
                            await self.account_manager.record_usage(
                                account=account,
                                prompt_tokens=prompt_tokens_est,
                                completion_tokens=completion_tokens_est,
                                effective_tokens=eff_est,
                            )
                        else:
                            await self.account_manager.mark_success(account)
                    return

                # If status is not 200, consume error body
                error_body = (await response.aread()).decode("utf-8", "replace")[:500]
                await response.aclose()
                await client.aclose()

                status_code = response.status_code
                logger.warning(
                    "Stream upstream error HTTP %d for account %s: %s",
                    status_code,
                    account.email,
                    error_body,
                )

                if status_code in (429,):
                    await self.account_manager.mark_failure(account, "rate_limit", error_body)
                elif status_code in (401, 403):
                    await self.account_manager.mark_failure(account, "auth", error_body)
                    if "invalid api key" in error_body.lower() or status_code == 401:
                        self._trigger_auto_recovery(account.email)
                elif "quota" in error_body.lower() or "balance" in error_body.lower() or "credit" in error_body.lower():
                    await self.account_manager.mark_failure(account, "quota_exceeded", error_body)
                else:
                    await self.account_manager.mark_failure(account, "upstream_error", error_body)

            except httpx.RequestError as exc:
                logger.warning("Stream network error with account %s: %s", account.email, exc)
                await self.account_manager.mark_failure(account, "network_error", str(exc))

        # If all accounts failed, yield OpenAI error chunk
        err_msg = json.dumps({
            "error": {
                "message": "All available Privatemode accounts failed or are exhausted",
                "type": "server_error",
                "param": None,
                "code": 502,
            }
        })
        yield f"data: {err_msg}\n\n".encode("utf-8")
        yield b"data: [DONE]\n\n"
