"""AI Copilot API router — chat, model management, feedback, status."""

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.rate_limiter import limiter
from app.services.copilot.copilot_service import (
    ask_copilot,
    delete_model,
    get_active_model,
    get_conversation_starters,
    get_model_recommendations,
    get_ollama_status,
    get_suggested_questions,
    list_models,
    pull_model,
    set_active_model,
    warmup_model,
)
from app.services.copilot.feedback_service import (
    get_feedback_stats,
    store_feedback,
)

router = APIRouter(prefix="/copilot", tags=["copilot"])
logger = logging.getLogger(__name__)


# ── Request models ──────────────────────────────────────────────

class AskRequest(BaseModel):
    store_id: str
    question: str
    conversation_history: list[dict] | None = None


class ModelActionRequest(BaseModel):
    model_id: str


class FeedbackRequest(BaseModel):
    store_id: str
    message_id: str
    question: str
    answer: str
    source: str
    model: str | None = None
    rating: int = Field(..., ge=-1, le=1)
    correction: str | None = None


# ── Chat endpoints ──────────────────────────────────────────────

@router.post("/ask")
@limiter.limit("20/minute")
def copilot_ask(request: Request, req: AskRequest):
    """Ask the AI copilot a business question."""
    try:
        result = ask_copilot(req.store_id, req.question, req.conversation_history)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error("Copilot ask failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process your question. Please try again.")


@router.get("/suggestions")
def copilot_suggestions():
    """Get a list of suggested questions."""
    return {"success": True, "data": get_suggested_questions()}


@router.get("/starters")
def copilot_starters():
    """Get categorized conversation starters for the welcome screen."""
    return {"success": True, "data": get_conversation_starters()}


@router.post("/warmup")
def copilot_warmup():
    """Pre-load the active model into GPU/RAM to eliminate cold-start delay."""
    result = warmup_model()
    return {"success": result["success"], "data": result}


# ── Model management endpoints ──────────────────────────────────

@router.get("/status")
def copilot_status():
    """Check Ollama availability and connection status."""
    status = get_ollama_status()
    return {"success": True, "data": status}


@router.get("/models")
def copilot_models():
    """List available models with install status."""
    return {"success": True, "data": list_models()}


@router.get("/models/recommendations")
def copilot_recommendations():
    """Get install/upgrade recommendations based on current model setup."""
    return {"success": True, "data": get_model_recommendations()}


@router.get("/models/active")
def copilot_active_model():
    """Get the currently active model."""
    return {"success": True, "data": {"model": get_active_model()}}


@router.put("/models/active")
def copilot_set_active_model(req: ModelActionRequest):
    """Set the active model."""
    result = set_active_model(req.model_id)
    return {"success": True, "data": result}


@router.post("/models/install")
def copilot_install_model(req: ModelActionRequest):
    """Download and install a model via Ollama."""
    result = pull_model(req.model_id)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return {"success": True, "data": result}


@router.delete("/models/{model_id:path}")
def copilot_delete_model(model_id: str):
    """Delete an installed model."""
    result = delete_model(model_id)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return {"success": True, "data": result}


# ── Feedback endpoints ──────────────────────────────────────────

@router.post("/feedback")
def copilot_feedback(req: FeedbackRequest):
    """Submit feedback (thumbs up/down) for a copilot answer."""
    try:
        result = store_feedback(
            store_id=req.store_id,
            message_id=req.message_id,
            question=req.question,
            answer=req.answer,
            source=req.source,
            model=req.model,
            rating=req.rating,
            correction=req.correction,
        )
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        return {"success": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback/stats/{store_id}")
def copilot_feedback_stats(store_id: str):
    """Get feedback statistics for a store."""
    try:
        stats = get_feedback_stats(store_id)
        return {"success": True, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
