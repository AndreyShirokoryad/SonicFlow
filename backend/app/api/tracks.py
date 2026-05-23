from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Query, Request

from backend.app.api.deps import get_recommender
from backend.app.schemas import (
    TrackBatchLookupRequest,
    TrackBatchLookupResponse,
    TrackLookupResponse,
    TrackSearchResult,
)


router = APIRouter(prefix="/tracks", tags=["tracks"])


@router.get("/search", response_model=List[TrackSearchResult])
def search_tracks(
    request: Request,
    q: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=5000),
) -> list[dict]:
    service = get_recommender(request)
    return service.search_tracks(q, limit=limit, offset=offset)


@router.post("/batch", response_model=TrackBatchLookupResponse)
def batch_lookup_tracks(request: Request, payload: TrackBatchLookupRequest) -> dict:
    service = get_recommender(request)
    tracks, missing_uris = service.get_tracks(payload.track_uris)
    return {"tracks": tracks, "missing_uris": missing_uris}


@router.get("/{track_uri:path}", response_model=TrackLookupResponse)
def get_track(request: Request, track_uri: str) -> dict:
    service = get_recommender(request)
    track = service.get_track(track_uri)
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")
    return {"track": track}
