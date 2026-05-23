from __future__ import annotations

import argparse
import csv
import json
import math
import re
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

import numpy as np


ARTIST_SPLIT_RE = re.compile(r"\s*(?:,|&| feat\.? | ft\.? | featuring | x |х|\+|/)\s*", re.I)
NON_WORD_RE = re.compile(r"[^0-9a-zа-я]+", re.I)


@dataclass(frozen=True)
class Item2VecConfig:
    vector_size: int = 64
    window: int = 5
    negative: int = 5
    min_count: int = 2
    epochs: int = 1
    learning_rate: float = 0.025
    seed: int = 42
    max_pairs_per_playlist: int = 2_000


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = value.casefold().replace("ё", "е")
    value = value.replace("’", "'").replace("`", "'")
    value = NON_WORD_RE.sub(" ", value)
    return " ".join(value.split())


def split_artists(value: str) -> set[str]:
    return {normalize_text(part) for part in ARTIST_SPLIT_RE.split(value) if normalize_text(part)}


def sigmoid(values: np.ndarray) -> np.ndarray:
    return np.where(
        values >= 0,
        1.0 / (1.0 + np.exp(-values)),
        np.exp(values) / (1.0 + np.exp(values)),
    )


def iter_mpd_files(mpd_data_dir: Path, max_files: int | None = None) -> list[Path]:
    files = sorted(mpd_data_dir.glob("mpd.slice.*.json"))
    if max_files is not None:
        files = files[:max_files]
    if not files:
        raise FileNotFoundError(f"No MPD slice files found in {mpd_data_dir}")
    return files


def iter_mpd_playlists(
    mpd_data_dir: Path,
    max_files: int | None = None,
    max_playlists: int | None = None,
) -> Iterator[list[dict[str, Any]]]:
    seen_playlists = 0
    for path in iter_mpd_files(mpd_data_dir, max_files=max_files):
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        for playlist in payload.get("playlists", []):
            yield playlist.get("tracks", [])
            seen_playlists += 1
            if max_playlists is not None and seen_playlists >= max_playlists:
                return


def build_vocab(
    mpd_data_dir: Path,
    min_count: int,
    max_files: int | None = None,
    max_playlists: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    counts: Counter[str] = Counter()
    metadata: dict[str, dict[str, Any]] = {}

    for tracks in iter_mpd_playlists(
        mpd_data_dir,
        max_files=max_files,
        max_playlists=max_playlists,
    ):
        for track in tracks:
            uri = track.get("track_uri")
            if not uri:
                continue
            counts[uri] += 1
            if uri not in metadata:
                metadata[uri] = {
                    "track_uri": uri,
                    "track_name": track.get("track_name", ""),
                    "artist_name": track.get("artist_name", ""),
                    "artist_uri": track.get("artist_uri", ""),
                    "album_name": track.get("album_name", ""),
                    "album_uri": track.get("album_uri", ""),
                    "duration_ms": track.get("duration_ms", ""),
                }

    kept = [
        uri
        for uri, count in counts.most_common()
        if count >= min_count
    ]
    vocab = []
    uri_to_idx = {}
    for idx, uri in enumerate(kept):
        item = dict(metadata[uri])
        item["idx"] = idx
        item["count"] = counts[uri]
        vocab.append(item)
        uri_to_idx[uri] = idx
    return vocab, uri_to_idx


def playlist_to_indices(tracks: list[dict[str, Any]], uri_to_idx: dict[str, int]) -> list[int]:
    indices = []
    for track in tracks:
        idx = uri_to_idx.get(track.get("track_uri", ""))
        if idx is not None:
            indices.append(idx)
    return indices


def generate_skipgram_pairs(
    indices: list[int],
    window: int,
    max_pairs: int,
    rng: np.random.Generator,
) -> list[tuple[int, int]]:
    pairs = []
    for center_pos, center_idx in enumerate(indices):
        left = max(0, center_pos - window)
        right = min(len(indices), center_pos + window + 1)
        for context_pos in range(left, right):
            if context_pos == center_pos:
                continue
            pairs.append((center_idx, indices[context_pos]))

    if max_pairs > 0 and len(pairs) > max_pairs:
        selected = rng.choice(len(pairs), size=max_pairs, replace=False)
        pairs = [pairs[int(i)] for i in selected]
    return pairs


class Item2VecModel:
    def __init__(
        self,
        input_vectors: np.ndarray,
        output_vectors: np.ndarray,
        vocab: list[dict[str, Any]],
        config: Item2VecConfig,
    ) -> None:
        self.input_vectors = input_vectors
        self.output_vectors = output_vectors
        self.vocab = vocab
        self.config = config
        self.uri_to_idx = {item["track_uri"]: int(item["idx"]) for item in vocab}

    @classmethod
    def initialize(
        cls,
        vocab: list[dict[str, Any]],
        config: Item2VecConfig,
        rng: np.random.Generator,
    ) -> "Item2VecModel":
        vocab_size = len(vocab)
        scale = 0.5 / config.vector_size
        input_vectors = rng.uniform(
            low=-scale,
            high=scale,
            size=(vocab_size, config.vector_size),
        ).astype(np.float32)
        output_vectors = np.zeros((vocab_size, config.vector_size), dtype=np.float32)
        return cls(input_vectors, output_vectors, vocab, config)

    def train_pair(
        self,
        center_idx: int,
        context_idx: int,
        negatives: np.ndarray,
        learning_rate: float,
    ) -> float:
        sampled = np.concatenate(([context_idx], negatives.astype(np.int64)))
        labels = np.zeros(sampled.shape[0], dtype=np.float32)
        labels[0] = 1.0

        center_vector = self.input_vectors[center_idx].copy()
        sampled_vectors = self.output_vectors[sampled].copy()
        scores = sampled_vectors @ center_vector
        probabilities = sigmoid(scores).astype(np.float32)
        gradients = (labels - probabilities) * learning_rate

        self.input_vectors[center_idx] += gradients @ sampled_vectors
        np.add.at(self.output_vectors, sampled, gradients[:, None] * center_vector[None, :])

        eps = 1e-7
        loss = -float(
            labels @ np.log(probabilities + eps)
            + (1.0 - labels) @ np.log(1.0 - probabilities + eps)
        )
        return loss

    def normalized_vectors(self) -> np.ndarray:
        norms = np.linalg.norm(self.input_vectors, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-12)
        return (self.input_vectors / norms).astype(np.float32)

    def save(self, output_dir: Path, stats: dict[str, Any]) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        np.save(output_dir / "item_vectors.npy", self.input_vectors)
        np.save(output_dir / "item_vectors_normalized.npy", self.normalized_vectors())
        np.save(output_dir / "output_vectors.npy", self.output_vectors)
        with (output_dir / "vocab.jsonl").open("w", encoding="utf-8") as handle:
            for item in self.vocab:
                handle.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")
        metadata = {
            "config": asdict(self.config),
            "stats": stats,
            "files": {
                "item_vectors": "item_vectors.npy",
                "item_vectors_normalized": "item_vectors_normalized.npy",
                "output_vectors": "output_vectors.npy",
                "vocab": "vocab.jsonl",
            },
        }
        (output_dir / "model_meta.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, model_dir: Path, normalized: bool = False) -> "Item2VecModel":
        metadata = json.loads((model_dir / "model_meta.json").read_text(encoding="utf-8"))
        config = Item2VecConfig(**metadata["config"])
        vector_file = "item_vectors_normalized.npy" if normalized else "item_vectors.npy"
        input_vectors = np.load(model_dir / vector_file)
        output_vectors_path = model_dir / "output_vectors.npy"
        if output_vectors_path.exists():
            output_vectors = np.load(output_vectors_path)
        else:
            output_vectors = np.empty((0, config.vector_size), dtype=np.float32)
        vocab = []
        with (model_dir / "vocab.jsonl").open("r", encoding="utf-8") as handle:
            for line in handle:
                vocab.append(json.loads(line))
        return cls(input_vectors, output_vectors, vocab, config)

    def recommend(
        self,
        seed_uris: list[str],
        top_n: int,
        exclude_seed: bool = True,
        chunk_size: int = 200_000,
    ) -> list[dict[str, Any]]:
        normalized = self.normalized_vectors()
        seed_indices = [self.uri_to_idx[uri] for uri in seed_uris if uri in self.uri_to_idx]
        if not seed_indices:
            raise ValueError("None of the seed track URIs are present in the model vocabulary.")

        query = normalized[seed_indices].mean(axis=0)
        query_norm = np.linalg.norm(query)
        if query_norm == 0:
            raise ValueError("Seed query vector has zero norm.")
        query = (query / query_norm).astype(np.float32)

        best_indices: list[int] = []
        best_scores: list[float] = []
        seed_set = set(seed_indices)
        keep = top_n + len(seed_set) + 100
        for start in range(0, normalized.shape[0], chunk_size):
            end = min(start + chunk_size, normalized.shape[0])
            scores = normalized[start:end] @ query
            if scores.shape[0] > keep:
                local = np.argpartition(scores, -keep)[-keep:]
            else:
                local = np.arange(scores.shape[0])
            for local_idx in local:
                idx = start + int(local_idx)
                if exclude_seed and idx in seed_set:
                    continue
                best_indices.append(idx)
                best_scores.append(float(scores[local_idx]))

        order = np.argsort(np.asarray(best_scores))[::-1][:top_n]
        recommendations = []
        for pos in order:
            idx = best_indices[int(pos)]
            item = dict(self.vocab[idx])
            item["score"] = best_scores[int(pos)]
            recommendations.append(item)
        return recommendations


def train_item2vec(
    mpd_data_dir: Path,
    output_dir: Path,
    config: Item2VecConfig,
    max_files: int | None = None,
    max_playlists: int | None = None,
    progress_every: int = 100,
) -> dict[str, Any]:
    rng = np.random.default_rng(config.seed)
    print("Building MPD vocabulary...", flush=True)
    vocab, uri_to_idx = build_vocab(
        mpd_data_dir,
        min_count=config.min_count,
        max_files=max_files,
        max_playlists=max_playlists,
    )
    if not vocab:
        raise ValueError("Vocabulary is empty. Lower min_count or check MPD input path.")

    model = Item2VecModel.initialize(vocab, config, rng)
    counts = np.asarray([item["count"] for item in vocab], dtype=np.float64)
    negative_probs = np.power(counts, 0.75)
    negative_probs /= negative_probs.sum()

    total_pairs = 0
    total_loss = 0.0
    total_playlists = 0
    files_count = len(iter_mpd_files(mpd_data_dir, max_files=max_files))

    for epoch in range(config.epochs):
        learning_rate = config.learning_rate * (1.0 - (epoch / max(config.epochs, 1)) * 0.75)
        for playlist_idx, tracks in enumerate(
            iter_mpd_playlists(
                mpd_data_dir,
                max_files=max_files,
                max_playlists=max_playlists,
            ),
            start=1,
        ):
            indices = playlist_to_indices(tracks, uri_to_idx)
            if len(indices) < 2:
                continue

            pairs = generate_skipgram_pairs(
                indices,
                window=config.window,
                max_pairs=config.max_pairs_per_playlist,
                rng=rng,
            )
            for center_idx, context_idx in pairs:
                negatives = rng.choice(
                    len(vocab),
                    size=config.negative,
                    replace=True,
                    p=negative_probs,
                )
                total_loss += model.train_pair(
                    center_idx=center_idx,
                    context_idx=context_idx,
                    negatives=negatives,
                    learning_rate=learning_rate,
                )
                total_pairs += 1

            total_playlists += 1
            if progress_every and playlist_idx % progress_every == 0:
                avg_loss = total_loss / max(total_pairs, 1)
                print(
                    f"epoch={epoch + 1}/{config.epochs} "
                    f"playlists={playlist_idx} files={files_count} "
                    f"pairs={total_pairs} avg_loss={avg_loss:.4f}",
                    flush=True,
                )

    stats = {
        "vocab_size": len(vocab),
        "trained_pairs": total_pairs,
        "trained_playlists": total_playlists,
        "average_loss": total_loss / max(total_pairs, 1),
        "max_files": max_files,
        "max_playlists": max_playlists,
    }
    model.save(output_dir, stats=stats)
    return stats


def parse_playlist_file(path: Path) -> list[tuple[str, str, str]]:
    parsed = []
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        if " - " not in raw:
            parsed.append((raw, "", raw))
        else:
            artist, title = raw.split(" - ", 1)
            parsed.append((raw, artist.strip(), title.strip()))
    return parsed


def build_metadata_indexes(vocab: list[dict[str, Any]]) -> tuple[dict[tuple[str, str], str], dict[str, list[str]]]:
    by_artist_title: dict[tuple[str, str], str] = {}
    by_title: dict[str, list[str]] = {}
    for item in vocab:
        title_key = normalize_text(item["track_name"])
        artist_key = normalize_text(item["artist_name"])
        by_artist_title.setdefault((artist_key, title_key), item["track_uri"])
        by_title.setdefault(title_key, []).append(item["track_uri"])
    return by_artist_title, by_title


def match_playlist_to_model(model: Item2VecModel, playlist_path: Path) -> list[str]:
    by_artist_title, by_title = build_metadata_indexes(model.vocab)
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
            item = model.vocab[model.uri_to_idx[uri]]
            if artist_tokens & split_artists(item["artist_name"]):
                seed_uris.append(uri)
                break
    return seed_uris


def write_recommendations(rows: list[dict[str, Any]], output_path: Path | None) -> None:
    if output_path is None:
        for idx, row in enumerate(rows, start=1):
            print(
                f"{idx}. {row['artist_name']} - {row['track_name']} "
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
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for rank, row in enumerate(rows, start=1):
            writer.writerow(
                {
                    "rank": rank,
                    "score": row["score"],
                    "track_uri": row["track_uri"],
                    "track_name": row["track_name"],
                    "artist_name": row["artist_name"],
                    "album_name": row["album_name"],
                    "duration_ms": row["duration_ms"],
                    "count": row.get("count", ""),
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Item2Vec recommender for Spotify MPD.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    train_parser = subparsers.add_parser("train", help="Train Item2Vec on MPD playlists.")
    train_parser.add_argument("--mpd-data-dir", type=Path, default=Path("data/MPD/archive/data"))
    train_parser.add_argument("--output-dir", type=Path, default=Path("data/models/item2vec_mpd"))
    train_parser.add_argument("--vector-size", type=int, default=64)
    train_parser.add_argument("--window", type=int, default=5)
    train_parser.add_argument("--negative", type=int, default=5)
    train_parser.add_argument("--min-count", type=int, default=2)
    train_parser.add_argument("--epochs", type=int, default=1)
    train_parser.add_argument("--learning-rate", type=float, default=0.025)
    train_parser.add_argument("--seed", type=int, default=42)
    train_parser.add_argument("--max-pairs-per-playlist", type=int, default=2_000)
    train_parser.add_argument("--max-files", type=int, default=None)
    train_parser.add_argument("--max-playlists", type=int, default=None)
    train_parser.add_argument("--progress-every", type=int, default=100)

    recommend_parser = subparsers.add_parser("recommend", help="Recommend by seed track URIs.")
    recommend_parser.add_argument("--model-dir", type=Path, default=Path("data/models/item2vec_mpd"))
    recommend_parser.add_argument("--seed-uri", action="append", required=True)
    recommend_parser.add_argument("--top-n", type=int, default=20)
    recommend_parser.add_argument("--output", type=Path, default=None)

    playlist_parser = subparsers.add_parser(
        "recommend-playlist",
        help="Match an artist-title playlist file against the model and recommend tracks.",
    )
    playlist_parser.add_argument("--model-dir", type=Path, default=Path("data/models/item2vec_mpd"))
    playlist_parser.add_argument("--playlist", type=Path, required=True)
    playlist_parser.add_argument("--top-n", type=int, default=20)
    playlist_parser.add_argument("--output", type=Path, default=None)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "train":
        config = Item2VecConfig(
            vector_size=args.vector_size,
            window=args.window,
            negative=args.negative,
            min_count=args.min_count,
            epochs=args.epochs,
            learning_rate=args.learning_rate,
            seed=args.seed,
            max_pairs_per_playlist=args.max_pairs_per_playlist,
        )
        stats = train_item2vec(
            mpd_data_dir=args.mpd_data_dir,
            output_dir=args.output_dir,
            config=config,
            max_files=args.max_files,
            max_playlists=args.max_playlists,
            progress_every=args.progress_every,
        )
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    elif args.command == "recommend":
        model = Item2VecModel.load(args.model_dir)
        rows = model.recommend(seed_uris=args.seed_uri, top_n=args.top_n)
        write_recommendations(rows, args.output)
    elif args.command == "recommend-playlist":
        model = Item2VecModel.load(args.model_dir)
        seed_uris = match_playlist_to_model(model, args.playlist)
        print(f"Matched {len(seed_uris)} seed tracks from {args.playlist}")
        rows = model.recommend(seed_uris=seed_uris, top_n=args.top_n)
        write_recommendations(rows, args.output)


if __name__ == "__main__":
    main()
