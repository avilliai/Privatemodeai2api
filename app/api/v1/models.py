"""OpenAI-compatible Models list and retrieve router."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import verify_api_key
from app.core.config import settings

router = APIRouter()


def make_model_card(model_id: str) -> dict[str, Any]:
    return {
        "id": model_id,
        "object": "model",
        "created": int(time.time()),
        "owned_by": "privatemode",
        "permission": [
            {
                "id": f"modelperm-{model_id}",
                "object": "model_permission",
                "created": int(time.time()),
                "allow_create_engine": False,
                "allow_sampling": True,
                "allow_logprobs": True,
                "allow_search_indices": False,
                "allow_view": True,
                "allow_fine_tuning": False,
                "organization": "*",
                "group": None,
                "is_blocking": False,
            }
        ],
        "root": model_id,
        "parent": None,
    }


@router.get("/models")
async def list_models(_auth: str | None = Depends(verify_api_key)) -> dict[str, Any]:
    """List all available models including native Privatemode models and aliases."""
    all_models = list(settings.models_list)
    for alias in settings.model_aliases:
        if alias not in all_models:
            all_models.append(alias)

    cards = [make_model_card(m) for m in all_models]
    return {
        "object": "list",
        "data": cards,
    }


@router.get("/models/{model_id}")
async def get_model(model_id: str, _auth: str | None = Depends(verify_api_key)) -> dict[str, Any]:
    """Retrieve a single model card."""
    all_models = set(settings.models_list).union(settings.model_aliases.keys())
    if model_id not in all_models:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' does not exist")
    return make_model_card(model_id)
