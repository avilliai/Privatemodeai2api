"""Admin and Account Pool management router with full dashboard compatibility."""

from __future__ import annotations

import logging
import time
from typing import Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status, Header

from app.core.auth import verify_api_key
from app.core.config import settings
from app.core.dependencies import account_manager, register_service

logger = logging.getLogger(__name__)

router = APIRouter()


class BatchRegisterPayload(BaseModel):
    count: int = Field(default=1, ge=1, le=1000)
    register_all: bool = Field(default=False)
    concurrency: int = Field(default=1)
    rate_per_minute: float = Field(default=20.0)
    mode: str = Field(default="outlook")
    backend: str = Field(default="turnstile")


# ==================== Dashboard API Endpoints ====================

@router.get("/admin/accounts/detail")
async def get_accounts_detail(
    _auth: str | None = Depends(verify_api_key),
) -> dict[str, Any]:
    """Return full accounts detail formatted for the dashboard UI with official token quotas."""
    accounts = await account_manager.list_accounts()
    ui_accounts = []
    for acc in accounts:
        email = acc.get("email", "")
        status_val = acc.get("status", "active")
        is_alive = (status_val == "active")
        disabled = (status_val == "disabled")
        
        # Monthly limit per Privatemode Free Tier: 1,000,000 tokens/month
        monthly_limit = acc.get("monthly_limit", 1_000_000)
        daily_usage = acc.get("daily_token_usage") or {}
        
        # Calculate today tokens & recent 7 days tokens
        today_key = time.strftime("%Y-%m-%d")
        today_tokens = daily_usage.get(today_key, 0)
        
        # Last 7 days tokens
        seven_days_ago_key = time.strftime("%Y-%m-%d", time.localtime(time.time() - 7 * 86400))
        last_7d_tokens = sum(v for k, v in daily_usage.items() if k >= seven_days_ago_key)

        req_count = acc.get("total_requests", 0)
        total_tokens = acc.get("total_tokens", 0)
        prompt_tokens = acc.get("prompt_tokens", 0)
        completion_tokens = acc.get("completion_tokens", 0)

        ui_accounts.append({
            "id": email,
            "email": email,
            "is_alive": is_alive,
            "disabled": disabled,
            "status": status_val,
            "total_requests": req_count,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "today_tokens": today_tokens,
            "last_7d_tokens": last_7d_tokens,
            "monthly_limit": monthly_limit,
            "daily_token_usage": daily_usage,
            "last_checked": acc.get("last_used_at") or time.time(),
            "error": f"失败重试 {acc.get('consecutive_failures', 0)}" if acc.get("consecutive_failures", 0) > 0 else None,
            "api_key_masked": acc.get("api_key_masked", "***"),
            "key_id": acc.get("key_id", ""),
        })
    return {
        "accounts": ui_accounts,
        "total": len(ui_accounts),
    }


@router.get("/admin/register/pool-info")
async def get_register_pool_info(
    _auth: str | None = Depends(verify_api_key),
) -> dict[str, Any]:
    """Return Outlook account pool remaining & total count."""
    email_svc = register_service.email_service
    total = len(email_svc._accounts)
    blacklisted = len(email_svc._blacklist)
    remaining = max(0, total - blacklisted)
    return {
        "total_outlook_count": total,
        "remaining_outlook_count": remaining,
        "blacklisted_count": blacklisted,
    }


@router.post("/admin/register/outlook/batch")
async def batch_register_outlook(
    payload: BatchRegisterPayload,
    _auth: str | None = Depends(verify_api_key),
) -> dict[str, Any]:
    """Start a background batch registration job compatible with Monica dashboard."""
    count = payload.count
    if payload.register_all:
        email_svc = register_service.email_service
        count = max(1, len(email_svc._accounts) - len(email_svc._blacklist))

    job_id = register_service.start_background_job(count=count, concurrency=payload.concurrency)
    return {
        "job_id": job_id,
        "status": "running",
        "requested": count,
        "message": f"Background registration of {count} account(s) initiated",
    }


@router.get("/admin/register/outlook/status")
async def get_register_outlook_status(
    _auth: str | None = Depends(verify_api_key),
) -> dict[str, Any]:
    """Return latest active job status or idle state for dashboard polling."""
    if not register_service.jobs:
        return {
            "status": "IDLE",
            "progress": 0,
            "total": 0,
            "success_count": 0,
            "failed_count": 0,
            "recent_logs": ["[IDLE] 暂无正在运行的任务，可随时启动批量注册或找回"],
        }

    latest_job = list(register_service.jobs.values())[-1]
    status_str = latest_job.get("status", "idle").upper()
    total = latest_job.get("requested", 0)
    succeeded = latest_job.get("succeeded", 0)
    failed = latest_job.get("failed", 0)
    progress = succeeded + failed

    return {
        "job_id": latest_job.get("job_id"),
        "status": status_str,
        "progress": progress,
        "total": total,
        "success_count": succeeded,
        "failed_count": failed,
        "concurrency": latest_job.get("concurrency", 1),
        "job": latest_job,
        "recent_logs": latest_job.get("logs", []),
    }


@router.post("/admin/register/outlook/cancel")
async def cancel_register_job(
    _auth: str | None = Depends(verify_api_key),
) -> dict[str, Any]:
    """Cancel any running background registration task or clean up hung jobs."""
    cancelled = 0
    for jid, task in list(register_service.tasks.items()):
        if not task.done():
            task.cancel()
            cancelled += 1
        if jid in register_service.jobs:
            register_service.jobs[jid]["status"] = "cancelled"
            register_service.jobs[jid]["logs"].append({
                "time": __import__("time").strftime("%H:%M:%S"),
                "level": "warning",
                "message": "[CANCEL] 任务已被管理员手动终止",
            })
    # Also mark any lingering running jobs without active tasks as cancelled
    for jid, j in register_service.jobs.items():
        if j.get("status") == "running":
            j["status"] = "cancelled"
            j["logs"].append({
                "time": __import__("time").strftime("%H:%M:%S"),
                "level": "warning",
                "message": "[CANCEL] 任务已清理终止",
            })
            cancelled += 1
    return {"message": f"Cancelled {cancelled} active background task(s)"}


@router.post("/admin/accounts/probe")
async def probe_all_accounts(
    _auth: str | None = Depends(verify_api_key),
) -> dict[str, Any]:
    """Check connectivity / validity of all accounts in the pool."""
    accounts = await account_manager.list_accounts()
    alive_count = 0
    now = time.time()
    for acc in accounts:
        if acc.get("status") == "active":
            alive_count += 1
    return {
        "status": "ok",
        "alive_count": alive_count,
        "total_count": len(accounts),
    }


@router.post("/admin/accounts/{acc_id}/probe")
async def probe_single_account(
    acc_id: str,
    _auth: str | None = Depends(verify_api_key),
) -> dict[str, Any]:
    """Probe a single account's license key and status."""
    acc = await account_manager.get_account_by_email(acc_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    now = time.time()
    is_alive = acc.is_usable(now)
    return {
        "id": acc_id,
        "status": "active" if is_alive else acc.status,
        "is_alive": is_alive,
        "message": "Account operational" if is_alive else "Account unavailable",
    }


@router.post("/admin/accounts/{acc_id}/toggle")
async def toggle_single_account(
    acc_id: str,
    _auth: str | None = Depends(verify_api_key),
) -> dict[str, Any]:
    """Toggle enable / disable status for a specific account."""
    acc = await account_manager.get_account_by_email(acc_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    if acc.status == "disabled":
        acc.status = "active"
        acc.consecutive_failures = 0
        new_status = "active"
    else:
        acc.status = "disabled"
        new_status = "disabled"
    account_manager.save_accounts()
    return {
        "id": acc_id,
        "status": new_status,
        "disabled": (new_status == "disabled"),
    }


@router.delete("/admin/accounts/{acc_id}")
async def delete_single_account(
    acc_id: str,
    _auth: str | None = Depends(verify_api_key),
) -> dict[str, Any]:
    """Delete an account from the pool by ID/email."""
    success = await account_manager.remove_account(acc_id)
    if not success:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"status": "ok", "message": f"Account {acc_id} deleted"}


@router.post("/admin/accounts/reset-quota")
async def reset_all_quota(
    _auth: str | None = Depends(verify_api_key),
) -> dict[str, Any]:
    """Reset failure and cooldown for all accounts in pool."""
    count = 0
    for acc in account_manager.accounts:
        acc.status = "active"
        acc.consecutive_failures = 0
        acc.rate_limited_until = 0.0
        count += 1
    account_manager.save_accounts()
    return {"message": f"Reset {count} accounts to active"}


# ==================== Standard /v1/admin Endpoints ====================

@router.get("/v1/admin/pool")
async def get_pool_stats(
    _auth: str | None = Depends(verify_api_key),
) -> dict[str, Any]:
    """Retrieve summary metrics and status breakdown of the account pool."""
    stats = await account_manager.get_stats()
    stats["email_pool_total"] = len(register_service.email_service._accounts)
    stats["email_pool_blacklist"] = len(register_service.email_service._blacklist)
    stats["email_pool_available"] = max(0, stats["email_pool_total"] - stats["email_pool_blacklist"])
    return stats


@router.get("/v1/admin/accounts")
async def list_accounts_endpoint(
    _auth: str | None = Depends(verify_api_key),
) -> dict[str, Any]:
    """List all accounts in the pool with masked API keys and usage statistics."""
    accounts = await account_manager.list_accounts()
    return {
        "total": len(accounts),
        "accounts": accounts,
    }


@router.post("/v1/admin/accounts/{email}/reset")
async def reset_account_endpoint(
    email: str,
    _auth: str | None = Depends(verify_api_key),
) -> dict[str, Any]:
    """Reset failure counts and rate-limit cooldown for a specific account."""
    success = await account_manager.reset_account(email)
    if not success:
        raise HTTPException(status_code=404, detail=f"Account '{email}' not found in pool")
    return {"message": f"Account '{email}' has been reset to active"}


@router.delete("/v1/admin/accounts/{email}")
async def delete_account_endpoint(
    email: str,
    _auth: str | None = Depends(verify_api_key),
) -> dict[str, Any]:
    """Remove an account permanently from the active pool."""
    success = await account_manager.remove_account(email)
    if not success:
        raise HTTPException(status_code=404, detail=f"Account '{email}' not found in pool")
    return {"message": f"Account '{email}' removed from pool"}


@router.post("/v1/admin/purge-dead")
async def purge_dead_accounts_endpoint(
    _auth: str | None = Depends(verify_api_key),
) -> dict[str, Any]:
    """Purge all exhausted and disabled accounts from active pool."""
    purged = await account_manager.purge_dead_accounts()
    return {
        "message": f"Purged {purged} dead/exhausted accounts from pool",
        "purged_count": purged,
    }


@router.get("/v1/admin/config")
async def get_system_config(
    _auth: str | None = Depends(verify_api_key),
) -> dict[str, Any]:
    """Inspect safe runtime configurations."""
    return {
        "host": settings.HOST,
        "port": settings.PORT,
        "default_model": settings.DEFAULT_MODEL,
        "supported_models": settings.models_list,
        "model_aliases": settings.model_aliases,
        "turnstile_solver_url": settings.TURNSTILE_SOLVER_URL,
        "outlook_accounts_total": len(register_service.email_service._accounts),
        "outlook_blacklist_count": len(register_service.email_service._blacklist),
        "auto_disable_exhausted": settings.AUTO_DISABLE_EXHAUSTED,
        "request_timeout": settings.REQUEST_TIMEOUT,
    }