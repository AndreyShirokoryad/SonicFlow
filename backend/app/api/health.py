from __future__ import annotations

from fastapi import APIRouter, Request


router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request) -> dict:
    service = getattr(request.app.state, "recommender", None)
    startup_error = getattr(request.app.state, "startup_error", None)
    if service is None:
        return {
            "status": "error",
            "model_loaded": False,
            "model_dir": None,
            "vocab_size": 0,
            "error": "Recommendation service is not initialized.",
        }
    return {
        "status": "ok" if service.is_loaded else "degraded",
        "model_loaded": service.is_loaded,
        "model_dir": str(service.model_dir),
        "vocab_size": len(service.vocab),
        "error": startup_error,
    }


@router.get("/model")
def model_info(request: Request) -> dict:
    service = getattr(request.app.state, "recommender", None)
    if service is None:
        return {"loaded": False, "error": "Recommendation service is not initialized."}
    data = service.metadata()
    data["error"] = getattr(request.app.state, "startup_error", None)
    return data
