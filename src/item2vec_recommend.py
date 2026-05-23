from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from src.mpd_corpus import (
    build_metadata_indexes,
    normalize_text,
    parse_playlist_file,
    split_artists,
)


def load_exported_model(model_dir: Path) -> tuple[np.ndarray, list[dict[str, Any]], dict[str, int]]:
    vectors = np.load(model_dir / "item_vectors_normalized.npy")
    vocab = []
    with (model_dir / "vocab.jsonl").open("r", encoding="utf-8") as handle:
        for line in handle:
            vocab.append(json.loads(line))
    uri_to_idx = {item["track_uri"]: int(item["idx"]) for item in vocab}
    return vectors, vocab, uri_to_idx


def recommend_by_uris(
    model_dir: Path,
    seed_uris: list[str],
    top_n: int,
    chunk_size: int = 200_000,
    recent_k: int = 5,
    min_count: int = 5,
    recent_weight: float = 0.45,
    whole_weight: float = 0.25,
    multi_seed_weight: float = 0.20,
    popularity_weight: float = 0.10,
    candidate_pool: int = 5_000,
) -> list[dict[str, Any]]:
    vectors, vocab, uri_to_idx = load_exported_model(model_dir)
    seed_indices = [uri_to_idx[uri] for uri in seed_uris if uri in uri_to_idx]
    if not seed_indices:
        raise ValueError("None of the seed track URIs are present in the model vocabulary.")

    whole_query = vectors[seed_indices].mean(axis=0)
    whole_query = whole_query / max(float(np.linalg.norm(whole_query)), 1e-12)

    recent_indices = seed_indices[-recent_k:] if recent_k > 0 else seed_indices
    recent_query = vectors[recent_indices].mean(axis=0)
    recent_query = recent_query / max(float(np.linalg.norm(recent_query)), 1e-12)

    counts = np.asarray([int(item.get("count", 0)) for item in vocab], dtype=np.float32)
    max_log_count = float(np.log1p(counts).max()) if counts.size else 1.0
    popularity_scores = np.log1p(counts) / max(max_log_count, 1e-12)

    seed_set = set(seed_indices)
    keep = max(candidate_pool, top_n + len(seed_set) + 100)
    candidate_indices: set[int] = set()
    for query in (recent_query, whole_query):
        for start in range(0, vectors.shape[0], chunk_size):
            end = min(start + chunk_size, vectors.shape[0])
            scores = vectors[start:end] @ query
            if scores.shape[0] > keep:
                local = np.argpartition(scores, -keep)[-keep:]
            else:
                local = np.arange(scores.shape[0])
            for local_idx in local:
                idx = start + int(local_idx)
                if idx in seed_set:
                    continue
                if counts[idx] < min_count:
                    continue
                candidate_indices.add(idx)

    if not candidate_indices:
        return []

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

    final_scores = (
        recent_weight * recent_scores
        + whole_weight * whole_scores
        + multi_seed_weight * support_scores
        + popularity_weight * popularity_scores[candidate_array]
    )

    order = np.argsort(final_scores)[::-1][:top_n]
    rows = []
    for pos in order:
        idx = int(candidate_array[int(pos)])
        item = dict(vocab[idx])
        item["score"] = float(final_scores[int(pos)])
        item["recent_similarity"] = float(recent_scores[int(pos)])
        item["whole_playlist_similarity"] = float(whole_scores[int(pos)])
        item["multi_seed_support"] = float(support_scores[int(pos)])
        item["popularity_prior"] = float(popularity_scores[idx])
        rows.append(item)
    return rows


def recommend_by_uris_simple(
    model_dir: Path,
    seed_uris: list[str],
    top_n: int,
    chunk_size: int = 200_000,
) -> list[dict[str, Any]]:
    vectors, vocab, uri_to_idx = load_exported_model(model_dir)
    seed_indices = [uri_to_idx[uri] for uri in seed_uris if uri in uri_to_idx]
    if not seed_indices:
        raise ValueError("None of the seed track URIs are present in the model vocabulary.")

    query = vectors[seed_indices].mean(axis=0)
    query = query / max(float(np.linalg.norm(query)), 1e-12)
    seed_set = set(seed_indices)
    keep = top_n + len(seed_set) + 100
    best_indices: list[int] = []
    best_scores: list[float] = []

    for start in range(0, vectors.shape[0], chunk_size):
        end = min(start + chunk_size, vectors.shape[0])
        scores = vectors[start:end] @ query
        if scores.shape[0] > keep:
            local = np.argpartition(scores, -keep)[-keep:]
        else:
            local = np.arange(scores.shape[0])
        for local_idx in local:
            idx = start + int(local_idx)
            if idx in seed_set:
                continue
            best_indices.append(idx)
            best_scores.append(float(scores[local_idx]))

    order = np.argsort(np.asarray(best_scores))[::-1][:top_n]
    rows = []
    for pos in order:
        idx = best_indices[int(pos)]
        item = dict(vocab[idx])
        item["score"] = best_scores[int(pos)]
        rows.append(item)
    return rows


def match_playlist_to_model(model_dir: Path, playlist_path: Path) -> list[str]:
    _vectors, vocab, uri_to_idx = load_exported_model(model_dir)
    by_artist_title, by_title = build_metadata_indexes(vocab)
    seed_uris = []
    for _raw, artist, title in parse_playlist_file(playlist_path):
        artist_key = normalize_text(artist)
        title_key = normalize_text(title)
        exact = by_artist_title.get((artist_key, title_key))
        if exact:
            seed_uris.append(exact)
            continue

        artist_tokens = split_artists(artist)
        for uri in by_title.get(title_key, []):
            item = vocab[uri_to_idx[uri]]
            if artist_tokens & split_artists(item.get("artist_name", "")):
                seed_uris.append(uri)
                break
    return seed_uris


def write_recommendations(rows: list[dict[str, Any]], output_path: Path | None) -> None:
    if output_path is None:
        for idx, row in enumerate(rows, start=1):
            print(
                f"{idx}. {row.get('artist_name', '')} - {row.get('track_name', '')} "
                f"score={row['score']:.4f} count={row.get('count', '')}"
            )
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "rank",
        "score",
        "track_uri",
        "track_name",
        "artist_name",
        "album_name",
        "duration_ms",
        "count",
        "recent_similarity",
        "whole_playlist_similarity",
        "multi_seed_support",
        "popularity_prior",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for rank, row in enumerate(rows, start=1):
            writer.writerow(
                {
                    "rank": rank,
                    "score": row["score"],
                    "track_uri": row.get("track_uri", ""),
                    "track_name": row.get("track_name", ""),
                    "artist_name": row.get("artist_name", ""),
                    "album_name": row.get("album_name", ""),
                    "duration_ms": row.get("duration_ms", ""),
                    "count": row.get("count", ""),
                    "recent_similarity": row.get("recent_similarity", ""),
                    "whole_playlist_similarity": row.get("whole_playlist_similarity", ""),
                    "multi_seed_support": row.get("multi_seed_support", ""),
                    "popularity_prior": row.get("popularity_prior", ""),
                }
            )


def add_common_recommend_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model-dir", type=Path, default=Path("data/models/item2vec_mpd_gensim"))
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--simple", action="store_true")
    parser.add_argument("--recent-k", type=int, default=5)
    parser.add_argument("--min-count", type=int, default=5)
    parser.add_argument("--candidate-pool", type=int, default=5_000)
    parser.add_argument("--recent-weight", type=float, default=0.45)
    parser.add_argument("--whole-weight", type=float, default=0.25)
    parser.add_argument("--multi-seed-weight", type=float, default=0.20)
    parser.add_argument("--popularity-weight", type=float, default=0.10)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recommend tracks from an exported MPD Item2Vec model.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    uri_parser = subparsers.add_parser("uris", help="Recommend by seed track URIs.")
    uri_parser.add_argument("--seed-uri", action="append", required=True)
    add_common_recommend_args(uri_parser)

    playlist_parser = subparsers.add_parser("playlist", help="Recommend by artist-title playlist file.")
    playlist_parser.add_argument("--playlist", type=Path, required=True)
    add_common_recommend_args(playlist_parser)
    return parser.parse_args()


def run_recommendation(args: argparse.Namespace, seed_uris: list[str]) -> None:
    if args.simple:
        rows = recommend_by_uris_simple(args.model_dir, seed_uris=seed_uris, top_n=args.top_n)
    else:
        rows = recommend_by_uris(
            args.model_dir,
            seed_uris=seed_uris,
            top_n=args.top_n,
            recent_k=args.recent_k,
            min_count=args.min_count,
            recent_weight=args.recent_weight,
            whole_weight=args.whole_weight,
            multi_seed_weight=args.multi_seed_weight,
            popularity_weight=args.popularity_weight,
            candidate_pool=args.candidate_pool,
        )
    write_recommendations(rows, args.output)


def main() -> None:
    args = parse_args()
    if args.command == "uris":
        run_recommendation(args, args.seed_uri)
    elif args.command == "playlist":
        seed_uris = match_playlist_to_model(args.model_dir, args.playlist)
        print(f"Matched {len(seed_uris)} seed tracks from {args.playlist}")
        run_recommendation(args, seed_uris)


if __name__ == "__main__":
    main()
