from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class TrackText(BaseModel):
    artist: str = ""
    title: str = ""


class RecommendOptions(BaseModel):
    top_n: int = Field(default=20, ge=1, le=200)
    recent_k: int = Field(default=5, ge=1, le=100)
    min_count: int = Field(default=10, ge=1)
    candidate_pool: int = Field(default=10000, ge=100, le=100000)
    preset: Optional[Literal["balance", "balanced", "more_recent", "favorite", "more_popular"]] = None
    recent_weight: float = Field(default=0.45, ge=0.0, le=1.0)
    whole_weight: float = Field(default=0.25, ge=0.0, le=1.0)
    multi_seed_weight: float = Field(default=0.20, ge=0.0, le=1.0)
    popularity_weight: float = Field(default=0.10, ge=0.0, le=1.0)


class UriRecommendRequest(RecommendOptions):
    seed_uris: List[str] = Field(..., min_length=1, max_length=5000)


class PlaylistRecommendRequest(RecommendOptions):
    tracks: List[TrackText] = Field(..., min_length=1, max_length=5000)


class TrackMatchRequest(BaseModel):
    tracks: List[TrackText] = Field(..., min_length=1, max_length=5000)


class Recommendation(BaseModel):
    rank: int
    score: float
    track_uri: str
    track_name: str = ""
    artist_name: str = ""
    album_name: str = ""
    duration_ms: Optional[Union[int, str]] = None
    count: int = 0
    recent_similarity: Optional[float] = None
    whole_playlist_similarity: Optional[float] = None
    multi_seed_support: Optional[float] = None
    popularity_prior: Optional[float] = None
    favorite_artist_affinity: Optional[float] = None
    explanation: str = ""


class RecommendResponse(BaseModel):
    matched_seed_count: int
    recommendations: List[Recommendation]


class TrackSearchResult(BaseModel):
    track_uri: str
    track_name: str = ""
    artist_name: str = ""
    album_name: str = ""
    duration_ms: Optional[Union[int, str]] = None
    count: int = 0


class TrackLookupResponse(BaseModel):
    track: Dict[str, Any]


class TrackBatchLookupRequest(BaseModel):
    track_uris: List[str] = Field(..., min_length=1, max_length=5000)


class TrackBatchLookupResponse(BaseModel):
    tracks: List[TrackSearchResult]
    missing_uris: List[str]


class TrackMatchResult(BaseModel):
    input_artist: str = ""
    input_title: str = ""
    status: str
    confidence: float
    matched: bool
    track_uri: Optional[str] = None
    track_name: str = ""
    artist_name: str = ""
    album_name: str = ""
    count: int = 0


class TrackMatchResponse(BaseModel):
    matched_count: int
    matches: List[TrackMatchResult]
