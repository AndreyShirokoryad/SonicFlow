from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from backend.app.api.deps import get_recommender
from backend.app.schemas import (
    PlaylistRecommendRequest,
    RecommendResponse,
    TrackMatchRequest,
    TrackMatchResponse,
    UriRecommendRequest,
)


router = APIRouter(prefix="/recommend", tags=["recommendations"])


PRESET_WEIGHTS = {
    "balance": {
        "recent_weight": 0.45,
        "whole_weight": 0.25,
        "multi_seed_weight": 0.20,
        "popularity_weight": 0.10,
        "favorite_artist_weight": 0.0,
    },
    "balanced": {
        "recent_weight": 0.45,
        "whole_weight": 0.25,
        "multi_seed_weight": 0.20,
        "popularity_weight": 0.10,
        "favorite_artist_weight": 0.0,
    },
    "more_recent": {
        "recent_weight": 0.65,
        "whole_weight": 0.15,
        "multi_seed_weight": 0.15,
        "popularity_weight": 0.05,
        "favorite_artist_weight": 0.0,
    },
    "favorite": {
        "recent_weight": 0.25,
        "whole_weight": 0.20,
        "multi_seed_weight": 0.15,
        "popularity_weight": 0.05,
        "favorite_artist_weight": 0.35,
    },
    "more_popular": {
        "recent_weight": 0.35,
        "whole_weight": 0.20,
        "multi_seed_weight": 0.20,
        "popularity_weight": 0.25,
        "favorite_artist_weight": 0.0,
    },
}


def _weights(payload) -> dict[str, float]:
    if payload.preset in PRESET_WEIGHTS:
        return PRESET_WEIGHTS[payload.preset]
    return {
        "recent_weight": payload.recent_weight,
        "whole_weight": payload.whole_weight,
        "multi_seed_weight": payload.multi_seed_weight,
        "popularity_weight": payload.popularity_weight,
        "favorite_artist_weight": 0.0,
    }


@router.post("/uris", response_model=RecommendResponse)
def recommend_by_uris(request: Request, payload: UriRecommendRequest) -> dict:
    service = get_recommender(request)
    weights = _weights(payload)
    matched_count, rows = service.recommend(
        seed_uris=payload.seed_uris,
        top_n=payload.top_n,
        recent_k=payload.recent_k,
        min_count=payload.min_count,
        candidate_pool=payload.candidate_pool,
        **weights,
    )
    if matched_count == 0:
        raise HTTPException(
            status_code=422,
            detail="None of the seed track URIs are present in the model vocabulary.",
        )
    return {"matched_seed_count": matched_count, "recommendations": rows}


@router.post("/playlist", response_model=RecommendResponse)
def recommend_by_playlist(request: Request, payload: PlaylistRecommendRequest) -> dict:
    service = get_recommender(request)
    seed_uris = service.match_text_tracks(
        [track.model_dump() for track in payload.tracks]
    )
    weights = _weights(payload)
    matched_count, rows = service.recommend(
        seed_uris=seed_uris,
        top_n=payload.top_n,
        recent_k=payload.recent_k,
        min_count=payload.min_count,
        candidate_pool=payload.candidate_pool,
        **weights,
    )
    if matched_count == 0:
        raise HTTPException(
            status_code=422,
            detail="No playlist tracks matched the Item2Vec model vocabulary.",
        )
    return {"matched_seed_count": matched_count, "recommendations": rows}


@router.post("/match", response_model=TrackMatchResponse)
def match_playlist_tracks(request: Request, payload: TrackMatchRequest) -> dict:
    service = get_recommender(request)
    matches = service.match_text_tracks_detailed(
        [track.model_dump() for track in payload.tracks]
    )
    matched_count = sum(1 for match in matches if match["matched"])
    return {"matched_count": matched_count, "matches": matches}
