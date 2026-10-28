"""Registration API router for Privatemode accounts."""

from __future__ import annotations

import logging
from typing import Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import verify_api_key
from app.core.dependencies import account_manager, register_service

logger = logging.getLogger(__name__)

router = APIRouter()


class RegisterRequest(BaseModel):
    count: int = Field(default=1, ge=1, le=50, description="Number of accounts to register")
    background: bool = Field(default=True, description="Run registration as a background job")


class ManualAccountRequest(BaseModel):
    email: str = Field(..., description="Outlook or account email address")
    password: str = Field(..., description="Account password")
    api_key: str = Field(..., description="Privatemode license key (starts with pm-)")
    key_id: Optional[str] = Field(default="", description="Privatemode key ID")
    org_id: Optional[str] = Field(default="", description="Clerk organization ID")
    session_id: Optional[str] = Field(default="", description="Clerk session ID")
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")



class RecoverRequest(BaseModel):
    emails: Optional[list[str]] = Field(default=None, description="Specific emails to recover. If None, auto-detects from blacklist.")
    background: bool = Field(default=True, description="Run recovery as background job")


class RecoverSingleRequest(BaseModel):
    email: str = Field(..., description="Outlook email to recover")

@router.post("/register", status_code=status.HTTP_200_OK)
async def register_accounts(
    req: RegisterRequest = RegisterRequest(),
    _auth: str | None = Depends(verify_api_key),
) -> dict[str, Any]:
    """Register one or more Privatemode accounts.

    By default, runs in the background and returns a job_id for status polling.
    If background=False, waits for completion and returns created accounts.
    """
    if req.background:
        job_id = register_service.start_background_job(count=req.count)
        return {
            "job_id": job_id,
            "status": "running",
            "requested": req.count,
            "message": f"Background registration of {req.count} account(s) initiated. Poll /v1/register/status/{job_id} for progress.",
        }

    # Synchronous foreground registration
    created = []
    errors = []
    for idx in range(req.count):
        try:
            acc = await register_service.register_single_account()
            created.append({
                "email": acc.email,
                "api_key_masked": acc.api_key[:8] + "..." + acc.api_key[-4:] if len(acc.api_key) > 12 else "***",
                "key_id": acc.key_id,
                "status": acc.status,
            })
        except Exception as e:
            logger.error("Manual registration %d/%d failed: %s", idx + 1, req.count, e)
            errors.append(str(e))

    return {
        "status": "completed" if not errors else ("partial" if created else "failed"),
        "requested": req.count,
        "succeeded": len(created),
        "failed": len(errors),
        "created": created,
        "errors": errors,
    }


@router.get("/register/status/{job_id}")
async def get_registration_status(
    job_id: str,
    _auth: str | None = Depends(verify_api_key),
) -> dict[str, Any]:
    """Get current status and progress of a background registration job."""
    job = register_service.jobs.get(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registration job '{job_id}' not found",
        )
    return job


@router.get("/register/jobs")
async def list_registration_jobs(
    _auth: str | None = Depends(verify_api_key),
) -> dict[str, Any]:
    """List all background registration jobs in memory."""
    return {
        "total": len(register_service.jobs),
        "jobs": list(register_service.jobs.values()),
    }


@router.post("/register/manual", status_code=status.HTTP_201_CREATED)
async def manual_add_account(
    req: ManualAccountRequest,
    _auth: str | None = Depends(verify_api_key),
) -> dict[str, Any]:
    """Manually add an existing Privatemode account and API key to the active pool."""
    record = await account_manager.add_account(
        email=req.email,
        password=req.password,
        api_key=req.api_key,
        key_id=req.key_id or "",
        org_id=req.org_id or "",
        session_id=req.session_id or "",
        metadata=req.metadata or {},
    )
    return {
        "message": "Account added to pool successfully",
        "account": {
            "email": record.email,
            "api_key_masked": record.api_key[:8] + "..." + record.api_key[-4:] if len(record.api_key) > 12 else "***",
            "key_id": record.key_id,
            "status": record.status,
            "total_accounts": len(account_manager.accounts),
        },
    }


@router.post("/register/recover", status_code=status.HTTP_200_OK)
async def recover_accounts(
    req: RecoverRequest = RecoverRequest(),
    _auth: str | None = Depends(verify_api_key),
) -> dict[str, Any]:
    """Recover accounts that are already registered on Privatemode but not in active pool."""
    target_emails = req.emails
    if not target_emails:
        # Scan blacklist for "already registered"
        bl = register_service.email_service._blacklist
        target_emails = []
        for em, info in bl.items():
            reason = str(info.get("reason", "")).lower()
            if "already registered" in reason or "taken" in reason or "form_identifier_exists" in reason:
                target_emails.append(em)

    if not target_emails:
        return {
            "status": "completed",
            "message": "No recoverable accounts found in blacklist or supplied list",
            "recovered": 0,
            "jobs": [],
        }

    if req.background:
        job_id = register_service.start_recovery_job(emails=target_emails)
        return {
            "job_id": job_id,
            "status": "running",
            "requested": len(target_emails),
            "target_emails": target_emails,
            "message": f"Background recovery of {len(target_emails)} account(s) initiated. Poll /v1/register/status/{job_id}",
        }

    # Synchronous recovery
    succeeded = []
    errors = []
    for em in target_emails:
        try:
            acc = await register_service.recover_single_account(em)
            succeeded.append(acc.email)
        except Exception as e:
            errors.append(f"{em}: {e}")

    return {
        "status": "completed" if not errors else ("partial" if succeeded else "failed"),
        "requested": len(target_emails),
        "succeeded": len(succeeded),
        "failed": len(errors),
        "recovered_accounts": succeeded,
        "errors": errors,
    }


@router.post("/register/recover-single", status_code=status.HTTP_200_OK)
async def recover_single_account_endpoint(
    req: RecoverSingleRequest,
    _auth: str | None = Depends(verify_api_key),
) -> dict[str, Any]:
    """Recover a single specific account by email."""
    try:
        acc = await register_service.recover_single_account(req.email)
        return {
            "status": "success",
            "message": f"Account {req.email} successfully recovered and added to pool",
            "account": {
                "email": acc.email,
                "api_key_masked": acc.api_key[:8] + "..." + acc.api_key[-4:] if len(acc.api_key) > 12 else "***",
                "status": acc.status,
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to recover account {req.email}: {e}",
        )
