from __future__ import annotations

from array import array
from bisect import bisect_left
from collections import OrderedDict, defaultdict
import json
import heapq
from pathlib import Path
from typing import Any

import numpy as np

from src.mpd_corpus import build_metadata_indexes, normalize_text, split_artists


SEARCH_RESULT_CACHE_SIZE = 64
SEARCH_PREFIX_CACHE_SIZE = 512
SEARCH_MIN_CACHED_RESULTS = 500
SEARCH_MAX_CACHED_RESULTS = 5100

try:
    import faiss
except ImportError:  # pragma: no cover - depends on optional deployment package
    faiss = None


class Item2VecModelStore:
    def __init__(self, model_dir: Path, enable_faiss: bool = True) -> None:
        self.model_dir = model_dir
        self.enable_faiss = enable_faiss
        self.vectors: np.ndarray | None = None
        self.vocab: list[dict[str, Any]] = []
        self.uri_to_idx: dict[str, int] = {}
        self.by_artist_title: dict[tuple[str, str], str] = {}
        self.by_title: dict[str, list[str]] = {}
        self.counts: np.ndarray | None = None
        self.popularity_scores: np.ndarray | None = None
        self._search_artist_keys: list[str] = []
        self._search_title_keys: list[str] = []
        self._search_token_index: dict[str, array] = {}
        self._artist_index: dict[str, array] = {}
        self._search_sorted_tokens: list[str] = []
        self._search_prefix_cache: OrderedDict[str, tuple[str, ...]] = OrderedDict()
        self._search_result_cache: OrderedDict[str, tuple[int, ...]] = OrderedDict()
        self.faiss_index: Any | None = None
        self.faiss_error: str | None = None

    @property
    def is_loaded(self) -> bool:
        return self.vectors is not None

    def load(self) -> None:
        vectors_path = self.model_dir / "item_vectors_normalized.npy"
        vocab_path = self.model_dir / "vocab.jsonl"
        missing = [path for path in (vectors_path, vocab_path) if not path.exists()]
        if missing:
            missing_list = ", ".join(str(path) for path in missing)
            raise FileNotFoundError(f"Missing Item2Vec model files: {missing_list}")

        self.vectors = np.load(vectors_path)

        vocab = []
        with vocab_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                vocab.append(json.loads(line))
        if self.vectors.shape[0] != len(vocab):
            raise ValueError(
                "Item2Vec vectors/vocab size mismatch: "
                f"{self.vectors.shape[0]} vectors, {len(vocab)} vocab rows"
            )

        self.vocab = vocab
        self.uri_to_idx = {item["track_uri"]: int(item["idx"]) for item in self.vocab}
        self.by_artist_title, self.by_title = build_metadata_indexes(self.vocab)

        counts = np.asarray([int(item.get("count", 0)) for item in self.vocab], dtype=np.float32)
        self.counts = counts
        max_log_count = float(np.log1p(counts).max()) if counts.size else 1.0
        self.popularity_scores = np.log1p(counts) / max(max_log_count, 1e-12)
        self._build_search_index()
        self._build_faiss_index()

    def metadata(self) -> dict[str, Any]:
        meta_path = self.model_dir / "model_meta.json"
        if not meta_path.exists():
            return {"model_dir": str(self.model_dir), "loaded": self.is_loaded}
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        data["model_dir"] = str(self.model_dir)
        data["loaded"] = self.is_loaded
        data["search_index_loaded"] = bool(self._search_token_index)
        data["search_token_count"] = len(self._search_token_index)
        data["artist_index_artist_count"] = len(self._artist_index)
        data["faiss_enabled"] = self.enable_faiss
        data["faiss_available"] = faiss is not None
        data["faiss_index_loaded"] = self.faiss_index is not None
        data["faiss_error"] = self.faiss_error
        return data

    @property
    def has_faiss_index(self) -> bool:
        return self.faiss_index is not None

    def require_vectors(self) -> np.ndarray:
        if self.vectors is None:
            raise RuntimeError("Item2Vec model is not loaded.")
        return self.vectors

    def require_counts(self) -> np.ndarray:
        if self.counts is None:
            raise RuntimeError("Item2Vec counts are not loaded.")
        return self.counts

    def require_popularity_scores(self) -> np.ndarray:
        if self.popularity_scores is None:
            raise RuntimeError("Item2Vec popularity scores are not loaded.")
        return self.popularity_scores

    def nearest_indices(self, query: np.ndarray, k: int) -> np.ndarray | None:
        if self.faiss_index is None or k <= 0:
            return None
        query_matrix = np.ascontiguousarray(query.reshape(1, -1), dtype=np.float32)
        _scores, indices = self.faiss_index.search(query_matrix, min(k, len(self.vocab)))
        return indices[0][indices[0] >= 0].astype(np.int64, copy=False)

    def artist_indices(self, artist_key: str):
        return self._artist_index.get(artist_key, ())

    def get_track(self, track_uri: str) -> dict[str, Any] | None:
        idx = self.uri_to_idx.get(track_uri)
        if idx is None:
            return None
        return self.vocab[idx]

    def get_tracks(self, track_uris: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
        tracks = []
        missing_uris = []
        for track_uri in track_uris:
            track = self.get_track(track_uri)
            if track is None:
                missing_uris.append(track_uri)
            else:
                tracks.append(track)
        return tracks, missing_uris

    def search_tracks(self, query: str, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        query_key = normalize_text(query)
        if not query_key:
            return []
        query_tokens = [token for token in query_key.split() if token]
        keep = max(1, offset + limit)
        ordered_indices = self._cached_search_indices(query_key, query_tokens, keep)
        return [self.vocab[idx] for idx in ordered_indices[offset : offset + limit]]

    def _build_search_index(self) -> None:
        token_index: dict[str, list[int]] = defaultdict(list)
        artist_index: dict[str, list[int]] = defaultdict(list)
        artist_keys: list[str] = []
        title_keys: list[str] = []

        for idx, item in enumerate(self.vocab):
            artist_name = item.get("artist_name", "")
            artist_key = normalize_text(artist_name)
            title_key = normalize_text(item.get("track_name", ""))
            artist_keys.append(artist_key)
            title_keys.append(title_key)

            for token in set(artist_key.split()) | set(title_key.split()):
                token_index[token].append(idx)
            for artist in split_artists(artist_name):
                artist_index[artist].append(idx)

        self._search_artist_keys = artist_keys
        self._search_title_keys = title_keys
        self._search_token_index = {
            token: array("I", indices) for token, indices in token_index.items()
        }
        self._artist_index = {
            artist: array("I", indices) for artist, indices in artist_index.items()
        }
        self._search_sorted_tokens = sorted(self._search_token_index)
        self._search_prefix_cache.clear()
        self._search_result_cache.clear()

    def _build_faiss_index(self) -> None:
        self.faiss_index = None
        self.faiss_error = None
        if not self.enable_faiss:
            self.faiss_error = "FAISS disabled by configuration."
            return
        if faiss is None:
            self.faiss_error = "faiss-cpu is not installed."
            return
        vectors = self.require_vectors()
        if vectors.ndim != 2 or vectors.shape[0] == 0:
            self.faiss_error = "No vectors available for FAISS index."
            return

        index_vectors = np.ascontiguousarray(vectors, dtype=np.float32)
        index = faiss.IndexFlatIP(int(index_vectors.shape[1]))
        index.add(index_vectors)
        self.faiss_index = index

    def _cached_search_indices(
        self,
        query_key: str,
        query_tokens: list[str],
        keep: int,
    ) -> tuple[int, ...]:
        cached = self._search_result_cache.get(query_key)
        if cached is not None and len(cached) >= keep:
            self._search_result_cache.move_to_end(query_key)
            return cached

        cache_keep = min(
            max(keep, SEARCH_MIN_CACHED_RESULTS),
            SEARCH_MAX_CACHED_RESULTS,
        )
        ranked = self._rank_search_indices(query_key, query_tokens, cache_keep)
        self._search_result_cache[query_key] = ranked
        self._search_result_cache.move_to_end(query_key)
        while len(self._search_result_cache) > SEARCH_RESULT_CACHE_SIZE:
            self._search_result_cache.popitem(last=False)
        return ranked

    def _rank_search_indices(
        self,
        query_key: str,
        query_tokens: list[str],
        keep: int,
    ) -> tuple[int, ...]:
        candidate_indices = self._candidate_indices_for_search(query_tokens)
        ranked = self._score_search_indices(query_key, query_tokens, keep, candidate_indices)

        # Rare substring-only searches such as "rld" cannot be found by the token index.
        # If the index did not produce enough results, fall back to all normalized rows.
        if candidate_indices is not None and len(ranked) < keep:
            return self._score_search_indices(query_key, query_tokens, keep, None)
        return ranked

    def _candidate_indices_for_search(self, query_tokens: list[str]) -> set[int] | None:
        if not query_tokens or not self._search_token_index:
            return None

        candidate_indices: set[int] = set()
        for token in query_tokens:
            for matching_token in self._matching_search_tokens(token):
                candidate_indices.update(self._search_token_index[matching_token])

        return candidate_indices or None

    def _matching_search_tokens(self, token: str) -> tuple[str, ...]:
        cached = self._search_prefix_cache.get(token)
        if cached is not None:
            self._search_prefix_cache.move_to_end(token)
            return cached

        matches: list[str] = []
        start = bisect_left(self._search_sorted_tokens, token)
        for index in range(start, len(self._search_sorted_tokens)):
            candidate = self._search_sorted_tokens[index]
            if not candidate.startswith(token):
                break
            matches.append(candidate)

        result = tuple(matches)
        self._search_prefix_cache[token] = result
        self._search_prefix_cache.move_to_end(token)
        while len(self._search_prefix_cache) > SEARCH_PREFIX_CACHE_SIZE:
            self._search_prefix_cache.popitem(last=False)
        return result

    def _score_search_indices(
        self,
        query_key: str,
        query_tokens: list[str],
        keep: int,
        candidate_indices: set[int] | None,
    ) -> tuple[int, ...]:
        heap: list[tuple[int, int, int, int]] = []
        indices = candidate_indices if candidate_indices is not None else range(len(self.vocab))

        for idx in indices:
            item = self.vocab[idx]
            artist_key = self._search_artist_keys[idx]
            title_key = self._search_title_keys[idx]
            score = self._search_score(query_key, query_tokens, artist_key, title_key)
            if score <= 0:
                continue
            count = int(item.get("count", 0))
            row = (score, count, -idx, idx)
            if len(heap) < keep:
                heapq.heappush(heap, row)
            elif row > heap[0]:
                heapq.heapreplace(heap, row)

        ordered = sorted(heap, reverse=True)
        return tuple(idx for *_rest, idx in ordered)

    def _search_score(
        self,
        query_key: str,
        query_tokens: list[str],
        artist_key: str,
        title_key: str,
    ) -> int:
        if not query_key:
            return 0
        if artist_key == query_key or title_key == query_key:
            return 100
        if artist_key.startswith(query_key):
            return 92
        if title_key.startswith(query_key):
            return 88
        if query_key in artist_key:
            return 82
        if query_key in title_key:
            return 78
        haystack = f"{artist_key} {title_key}".strip()
        if query_key in haystack:
            return 70
        if query_tokens and all(token in artist_key or token in title_key for token in query_tokens):
            return 60
        if len(query_tokens) > 1:
            matched_tokens = sum(
                1 for token in query_tokens if token in artist_key or token in title_key
            )
            if matched_tokens:
                return 10 + matched_tokens
        return 0
