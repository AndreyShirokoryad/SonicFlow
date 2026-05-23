from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from backend.app.services.model_store import Item2VecModelStore
from backend.app.services.playlist_matcher import PlaylistMatcher
from backend.app.services.recommender import Item2VecRecommender


class Item2VecService:
    def __init__(self, model_dir: Path, enable_faiss: bool = True) -> None:
        self.model_store = Item2VecModelStore(model_dir, enable_faiss=enable_faiss)
        self.playlist_matcher = PlaylistMatcher(self.model_store)
        self.recommender = Item2VecRecommender(self.model_store)

    @property
    def model_dir(self) -> Path:
        return self.model_store.model_dir

    @property
    def vectors(self) -> np.ndarray | None:
        return self.model_store.vectors

    @property
    def vocab(self) -> list[dict[str, Any]]:
        return self.model_store.vocab

    @property
    def uri_to_idx(self) -> dict[str, int]:
        return self.model_store.uri_to_idx

    @property
    def is_loaded(self) -> bool:
        return self.model_store.is_loaded

    def load(self) -> None:
        self.model_store.load()

    def metadata(self) -> dict[str, Any]:
        return self.model_store.metadata()

    def search_tracks(self, query: str, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        return self.model_store.search_tracks(query, limit=limit, offset=offset)

    def get_track(self, track_uri: str) -> dict[str, Any] | None:
        return self.model_store.get_track(track_uri)

    def get_tracks(self, track_uris: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
        return self.model_store.get_tracks(track_uris)

    def match_text_tracks(self, tracks: list[dict[str, str]]) -> list[str]:
        return self.playlist_matcher.match_text_tracks(tracks)

    def match_text_tracks_detailed(self, tracks: list[dict[str, str]]) -> list[dict[str, Any]]:
        return self.playlist_matcher.match_text_tracks_detailed(tracks)

    def recommend(
        self,
        seed_uris: list[str],
        top_n: int,
        recent_k: int,
        min_count: int,
        candidate_pool: int,
        recent_weight: float,
        whole_weight: float,
        multi_seed_weight: float,
        popularity_weight: float,
        favorite_artist_weight: float = 0.0,
        chunk_size: int = 200_000,
    ) -> tuple[int, list[dict[str, Any]]]:
        return self.recommender.recommend(
            seed_uris=seed_uris,
            top_n=top_n,
            recent_k=recent_k,
            min_count=min_count,
            candidate_pool=candidate_pool,
            recent_weight=recent_weight,
            whole_weight=whole_weight,
            multi_seed_weight=multi_seed_weight,
            popularity_weight=popularity_weight,
            favorite_artist_weight=favorite_artist_weight,
            chunk_size=chunk_size,
        )
