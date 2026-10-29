"""Authenticated OpenAI-compatible embeddings endpoint."""

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.auth import verify_api_key
from app.core.dependencies import privatemode_client

router = APIRouter()


@router.post("/embeddings")
async def embeddings(request: Request, _auth=Depends(verify_api_key)) -> dict:
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON request body")
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Request body must be an object")
    if not isinstance(body.get("model"), str) or not body["model"].strip():
        raise HTTPException(status_code=400, detail="Field 'model' is required")
    value = body.get("input")
    # Privatemode documents text input only, unlike OpenAI's token-array input.
    valid = isinstance(value, str) and bool(value.strip())
    if isinstance(value, list) and value:
        valid = all(isinstance(x, str) and x.strip() for x in value)
    if not valid:
        raise HTTPException(status_code=400, detail="Field 'input' must be a nonempty string or list of nonempty strings")
    if body.get("encoding_format", "float") not in ("float", "base64"):
        raise HTTPException(status_code=400, detail="Invalid encoding_format")
    if "dimensions" in body and (type(body["dimensions"]) is not int or body["dimensions"] <= 0):
        raise HTTPException(status_code=400, detail="dimensions must be a positive integer")
    return await privatemode_client.embeddings(body)
