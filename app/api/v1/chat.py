"""OpenAI-compatible Chat Completions router."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from app.core.auth import verify_api_key
from app.core.dependencies import account_manager, privatemode_client
from app.core.exceptions import AccountPoolError, UpstreamError

router = APIRouter()


@router.post("/chat/completions")
async def chat_completions(
    request: Request,
    _auth: str | None = Depends(verify_api_key),
) -> Response:
    """OpenAI-compatible /v1/chat/completions endpoint supporting both streaming and non-streaming."""
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON request body: {exc}")

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Request body must be a JSON object")

    messages = body.get("messages")
    if not messages or not isinstance(messages, list):
        raise HTTPException(status_code=400, detail="Field 'messages' is required and must be a list")

    stream = body.get("stream", False)

    if stream:
        return StreamingResponse(
            privatemode_client.stream_chat_completion(body),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            },
        )

    try:
        result = await privatemode_client.chat_completion(body)
        return Response(
            content=json.dumps(result, ensure_ascii=False),
            media_type="application/json",
            status_code=200,
        )
    except AccountPoolError as pool_err:
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "message": str(pool_err),
                    "type": "insufficient_quota",
                    "code": 503,
                }
            },
        )
    except UpstreamError as up_err:
        raise HTTPException(
            status_code=up_err.status_code or 502,
            detail={
                "error": {
                    "message": str(up_err),
                    "type": "upstream_error",
                    "code": up_err.status_code,
                }
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": f"Internal server error: {exc}",
                    "type": "server_error",
                    "code": 500,
                }
            },
        )
