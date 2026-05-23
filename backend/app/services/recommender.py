from __future__ import annotations

import heapq
from typing import Any

import numpy as np

from backend.app.services.model_store import Item2VecModelStore
from src.mpd_corpus import normalize_text, split_artists


VARIANT_WORDS = {
    "acoustic",
    "anniversary",
    "bonus",
    "demo",
    "edit",
    "explicit",
    "instrumental",
    "karaoke",
    "live",
    "mono",
    "radio",
    "remaster",
    "remastered",
    "remix",
    "single",
    "stereo",
    "version",
}


def canonical_track_name(value: str) -> str:
    tokens = [token for token in normalize_text(value).split() if token not in VARIANT_WORDS]
    return " ".join(tokens)


class Item2VecRecommender:
    def __init__(self, model_store: Item2VecModelStore) -> None:
        self.model_store = model_store

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
        vectors = self.model_store.require_vectors()
        counts = self.model_store.require_counts()
        popularity_scores = self.model_store.require_popularity_scores()
        seed_indices = [
            self.model_store.uri_to_idx[uri]
            for uri in seed_uris
            if uri in self.model_store.uri_to_idx
        ]
        if not seed_indices:
            return 0, []

        whole_query = vectors[seed_indices].mean(axis=0)
        whole_query = whole_query / max(float(np.linalg.norm(whole_query)), 1e-12)

        recent_indices = seed_indices[:recent_k] if recent_k > 0 else seed_indices
        recent_query = vectors[recent_indices].mean(axis=0)
        recent_query = recent_query / max(float(np.linalg.norm(recent_query)), 1e-12)

        seed_set = set(seed_indices)
        seed_fingerprints = self._seed_fingerprints(seed_indices)
        artist_weights = self._favorite_artist_weights(seed_indices)
        keep = max(candidate_pool, top_n + len(seed_set) + 100)
        candidate_indices: set[int] = set()
        for query in (recent_query, whole_query):
            faiss_indices = self.model_store.nearest_indices(
                query,
                k=self._faiss_candidate_search_k(vectors.shape[0], keep),
            )
            if faiss_indices is None:
                self._add_chunked_vector_candidates(
                    candidate_indices=candidate_indices,
                    query=query,
                    vectors=vectors,
                    counts=counts,
                    keep=keep,
                    chunk_size=chunk_size,
                    min_count=min_count,
                    seed_set=seed_set,
                    seed_fingerprints=seed_fingerprints,
                    artist_weights=artist_weights,
                    favorite_artist_weight=favorite_artist_weight,
                )
            else:
                self._add_vector_candidates(
                    candidate_indices=candidate_indices,
                    indices=faiss_indices,
                    counts=counts,
                    min_count=min_count,
                    seed_set=seed_set,
                    seed_fingerprints=seed_fingerprints,
                    artist_weights=artist_weights,
                    favorite_artist_weight=favorite_artist_weight,
                )

        if favorite_artist_weight > 0.0 and artist_weights:
            self._add_favorite_artist_candidates(
                candidate_indices=candidate_indices,
                seed_set=seed_set,
                seed_fingerprints=seed_fingerprints,
                artist_weights=artist_weights,
                counts=counts,
                keep=max(candidate_pool, top_n + 100),
            )

        if not candidate_indices:
            return len(seed_indices), []

        candidate_array = np.fromiter(candidate_indices, dtype=np.int64)
        candidate_vectors = vectors[candidate_array]
        recent_scores = candidate_vectors @ recent_query
        whole_scores = candidate_vectors @ whole_query

        seed_matrix = vectors[seed_indices]
        support_top_k = min(5, len(seed_indices))
        support_scores = np.empty(candidate_array.shape[0], dtype=np.float32)
        support_chunk = 10_000
        for start in range(0, candidate_array.shape[0], support_chunk):
            end = min(start + support_chunk, candidate_array.shape[0])
            sims = candidate_vectors[start:end] @ seed_matrix.T
            if support_top_k == 1:
                support_scores[start:end] = sims.max(axis=1)
            else:
                top = np.partition(sims, -support_top_k, axis=1)[:, -support_top_k:]
                support_scores[start:end] = top.mean(axis=1)

        favorite_scores = np.asarray(
            [
                self._favorite_artist_affinity_for_item(int(idx), artist_weights)
                for idx in candidate_array
            ],
            dtype=np.float32,
        )

        final_scores = (
            recent_weight * recent_scores
            + whole_weight * whole_scores
            + multi_seed_weight * support_scores
            + popularity_weight * popularity_scores[candidate_array]
            + favorite_artist_weight * favorite_scores
        )

        order = np.argsort(final_scores)[::-1][:top_n]
        rows = []
        for rank, pos in enumerate(order, start=1):
            idx = int(candidate_array[int(pos)])
            item = dict(self.model_store.vocab[idx])
            item["rank"] = rank
            item["score"] = float(final_scores[int(pos)])
            item["recent_similarity"] = float(recent_scores[int(pos)])
            item["whole_playlist_similarity"] = float(whole_scores[int(pos)])
            item["multi_seed_support"] = float(support_scores[int(pos)])
            item["popularity_prior"] = float(popularity_scores[idx])
            item["favorite_artist_affinity"] = float(favorite_scores[int(pos)])
            item["explanation"] = self._explain(
                item["recent_similarity"],
                item["whole_playlist_similarity"],
                item["multi_seed_support"],
                item["popularity_prior"],
                item["favorite_artist_affinity"],
            )
            rows.append(item)
        return len(seed_indices), rows

    def _faiss_candidate_search_k(self, vocab_size: int, keep: int) -> int:
        return min(vocab_size, max(keep * 2, keep + 1000))

    def _add_chunked_vector_candidates(
        self,
        candidate_indices: set[int],
        query: np.ndarray,
        vectors: np.ndarray,
        counts: np.ndarray,
        keep: int,
        chunk_size: int,
        min_count: int,
        seed_set: set[int],
        seed_fingerprints: list[tuple[str, set[str]]],
        artist_weights: dict[str, float],
        favorite_artist_weight: float,
    ) -> None:
        for start in range(0, vectors.shape[0], chunk_size):
            end = min(start + chunk_size, vectors.shape[0])
            scores = vectors[start:end] @ query
            if scores.shape[0] > keep:
                local = np.argpartition(scores, -keep)[-keep:]
            else:
                local = np.arange(scores.shape[0])
            self._add_vector_candidates(
                candidate_indices=candidate_indices,
                indices=(start + int(local_idx) for local_idx in local),
                counts=counts,
                min_count=min_count,
                seed_set=seed_set,
                seed_fingerprints=seed_fingerprints,
                artist_weights=artist_weights,
                favorite_artist_weight=favorite_artist_weight,
            )

    def _add_vector_candidates(
        self,
        candidate_indices: set[int],
        indices,
        counts: np.ndarray,
        min_count: int,
        seed_set: set[int],
        seed_fingerprints: list[tuple[str, set[str]]],
        artist_weights: dict[str, float],
        favorite_artist_weight: float,
    ) -> None:
        for raw_idx in indices:
            idx = int(raw_idx)
            if idx in seed_set:
                continue
            if favorite_artist_weight > 0.0:
                favorite_affinity = self._favorite_artist_affinity_for_item(idx, artist_weights)
            else:
                favorite_affinity = 0.0
            if counts[idx] < min_count and not (
                favorite_artist_weight > 0.0 and favorite_affinity > 0.0
            ):
                continue
            if self._looks_like_seed_duplicate(idx, seed_fingerprints):
                continue
            candidate_indices.add(idx)

    def _favorite_artist_weights(self, seed_indices: list[int]) -> dict[str, float]:
        counts: dict[str, int] = {}
        for idx in seed_indices:
            item = self.model_store.vocab[idx]
            for artist in split_artists(item.get("artist_name", "")):
                counts[artist] = counts.get(artist, 0) + 1
        if not counts:
            return {}
        max_count = max(counts.values())
        return {artist: count / max_count for artist, count in counts.items()}

    def _favorite_artist_affinity_for_item(
        self,
        idx: int,
        artist_weights: dict[str, float],
    ) -> float:
        if not artist_weights:
            return 0.0
        item = self.model_store.vocab[idx]
        artist_tokens = split_artists(item.get("artist_name", ""))
        if not artist_tokens:
            return 0.0
        return max((artist_weights.get(artist, 0.0) for artist in artist_tokens), default=0.0)

    def _add_favorite_artist_candidates(
        self,
        candidate_indices: set[int],
        seed_set: set[int],
        seed_fingerprints: list[tuple[str, set[str]]],
        artist_weights: dict[str, float],
        counts: np.ndarray,
        keep: int,
    ) -> None:
        heap: list[tuple[float, float, int]] = []
        favorite_indices: set[int] = set()
        for artist in artist_weights:
            favorite_indices.update(self.model_store.artist_indices(artist))

        for idx in favorite_indices:
            if idx in seed_set:
                continue
            affinity = self._favorite_artist_affinity_for_item(idx, artist_weights)
            if affinity <= 0.0:
                continue
            if self._looks_like_seed_duplicate(idx, seed_fingerprints):
                continue
            row = (affinity, float(counts[idx]), idx)
            if len(heap) < keep:
                heapq.heappush(heap, row)
            elif row > heap[0]:
                heapq.heapreplace(heap, row)
        for _affinity, _count, idx in heap:
            candidate_indices.add(idx)

    def _seed_fingerprints(self, seed_indices: list[int]) -> list[tuple[str, set[str]]]:
        fingerprints = []
        for idx in seed_indices:
            item = self.model_store.vocab[idx]
            fingerprints.append(
                (
                    canonical_track_name(item.get("track_name", "")),
                    split_artists(item.get("artist_name", "")),
                )
            )
        return fingerprints

    def _looks_like_seed_duplicate(
        self,
        candidate_idx: int,
        seed_fingerprints: list[tuple[str, set[str]]],
    ) -> bool:
        item = self.model_store.vocab[candidate_idx]
        candidate_title = canonical_track_name(item.get("track_name", ""))
        candidate_artists = split_artists(item.get("artist_name", ""))
        if not candidate_title:
            return False
        for seed_title, seed_artists in seed_fingerprints:
            if candidate_title != seed_title:
                continue
            if not seed_artists or not candidate_artists or seed_artists & candidate_artists:
                return True
        return False

    def _explain(
        self,
        recent_similarity: float,
        whole_similarity: float,
        support: float,
        popularity: float,
        favorite_affinity: float,
    ) -> str:
        reasons = []
        if favorite_affinity >= 0.5:
            reasons.append("совпадает с любимыми артистами плейлиста")
        if recent_similarity >= whole_similarity and recent_similarity >= 0.35:
            reasons.append("похож на последние треки")
        if whole_similarity >= 0.35:
            reasons.append("попадает в общий стиль плейлиста")
        if support >= 0.35:
            reasons.append("поддержан несколькими seed-треками")
        if popularity >= 0.55:
            reasons.append("часто встречается в MPD-плейлистах")
        if not reasons:
            reasons.append("имеет близкий playlist-context в MPD")
        return "; ".join(reasons)
