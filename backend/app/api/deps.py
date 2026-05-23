from __future__ import annotations

from fastapi import HTTPException, Request, status

from backend.app.services.item2vec_service import Item2VecService


def get_recommender(request: Request) -> Item2VecService:
    service = getattr(request.app.state, "recommender", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendation service is not initialized.",
        )
    if not service.is_loaded:
        startup_error = getattr(request.app.state, "startup_error", None)
        detail = startup_error or "Item2Vec model is not loaded."
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )
    return service
