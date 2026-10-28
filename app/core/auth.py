"""API Key authentication middleware and dependency."""

from __future__ import annotations

from typing import Optional
from fastapi import Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

security = HTTPBearer(auto_error=False)


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> str | None:
    """Validate Bearer token or X-API-Key header against settings.API_KEY."""
    expected_key = (settings.API_KEY or "").strip()
    if not expected_key:
        return None

    received_key = None
    if credentials and credentials.credentials:
        received_key = credentials.credentials.strip()
    elif x_api_key:
        received_key = x_api_key.strip()

    if not received_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header or X-API-Key header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if received_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return received_key
