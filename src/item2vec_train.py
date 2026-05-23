from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from src.mpd_corpus import MPDPlaylistCorpus, collect_metadata_for_keys


@dataclass(frozen=True)
class GensimItem2VecConfig:
    vector_size: int = 64
    window: int = 5
    negative: int = 5
    min_count: int = 2
    epochs: int = 5
    workers: int = 4
    sample: float = 1e-3
    seed: int = 42
    sg: int = 1


def require_gensim():
    try:
        from gensim.models import Word2Vec
        from gensim.models.callbacks import CallbackAny2Vec
    except ImportError as exc:
        raise SystemExit(
            "gensim is not installed. Install dependencies first, for example:\n"
            ".venv/bin/pip install gensim scipy"
        ) from exc
    return Word2Vec, CallbackAny2Vec


def build_epoch_logger(callback_base):
    class EpochLogger(callback_base):
        def __init__(self) -> None:
            self.epoch = 0

        def on_epoch_begin(self, model) -> None:  # type: ignore[no-untyped-def]
            print(f"Starting epoch {self.epoch + 1}", flush=True)

        def on_epoch_end(self, model) -> None:  # type: ignore[no-untyped-def]
            loss = model.get_latest_training_loss()
            print(f"Finished epoch {self.epoch + 1}; latest_loss={loss}", flush=True)
            self.epoch += 1

    return EpochLogger


def export_gensim_model(
    model: Any,
    output_dir: Path,
    mpd_data_dir: Path,
    config: GensimItem2VecConfig,
    max_files: int | None,
    max_playlists: int | None,
    progress_every_files: int,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    model.save(str(output_dir / "gensim_word2vec.model"))
    model.wv.save(str(output_dir / "gensim_keyed_vectors.kv"))

    keys = list(model.wv.index_to_key)
    vectors = model.wv.vectors.astype(np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    normalized = vectors / np.maximum(norms, 1e-12)

    np.save(output_dir / "item_vectors.npy", vectors)
    np.save(output_dir / "item_vectors_normalized.npy", normalized.astype(np.float32))

    metadata = collect_metadata_for_keys(
        mpd_data_dir=mpd_data_dir,
        keys=set(keys),
        max_files=max_files,
        max_playlists=max_playlists,
        progress_every_files=progress_every_files,
    )
    with (output_dir / "vocab.jsonl").open("w", encoding="utf-8") as handle:
        for idx, uri in enumerate(keys):
            item = dict(metadata.get(uri, {"track_uri": uri}))
            item["idx"] = idx
            item["count"] = int(model.wv.get_vecattr(uri, "count"))
            handle.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")

    model_meta = {
        "backend": "gensim.Word2Vec",
        "config": asdict(config),
        "stats": {
            "vocab_size": len(keys),
            "corpus_count": int(model.corpus_count),
            "corpus_total_words": int(model.corpus_total_words),
            "max_files": max_files,
            "max_playlists": max_playlists,
        },
        "files": {
            "gensim_model": "gensim_word2vec.model",
            "gensim_keyed_vectors": "gensim_keyed_vectors.kv",
            "item_vectors": "item_vectors.npy",
            "item_vectors_normalized": "item_vectors_normalized.npy",
            "vocab": "vocab.jsonl",
        },
    }
    (output_dir / "model_meta.json").write_text(
        json.dumps(model_meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def train_gensim_item2vec(
    mpd_data_dir: Path,
    output_dir: Path,
    config: GensimItem2VecConfig,
    max_files: int | None = None,
    max_playlists: int | None = None,
    progress_every_files: int = 50,
) -> None:
    Word2Vec, CallbackAny2Vec = require_gensim()
    EpochLogger = build_epoch_logger(CallbackAny2Vec)
    corpus = MPDPlaylistCorpus(
        mpd_data_dir=mpd_data_dir,
        max_files=max_files,
        max_playlists=max_playlists,
        progress_every_files=progress_every_files,
        total_passes_hint=config.epochs + 1,
    )
    model = Word2Vec(
        sentences=corpus,
        vector_size=config.vector_size,
        window=config.window,
        min_count=config.min_count,
        sg=config.sg,
        negative=config.negative,
        hs=0,
        sample=config.sample,
        workers=config.workers,
        epochs=config.epochs,
        seed=config.seed,
        compute_loss=True,
        callbacks=[EpochLogger()],
    )
    export_gensim_model(
        model=model,
        output_dir=output_dir,
        mpd_data_dir=mpd_data_dir,
        config=config,
        max_files=max_files,
        max_playlists=max_playlists,
        progress_every_files=progress_every_files,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train Item2Vec with gensim Word2Vec on Spotify MPD.")
    parser.add_argument("--mpd-data-dir", type=Path, default=Path("data/MPD/archive/data"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/models/item2vec_mpd_gensim"))
    parser.add_argument("--vector-size", type=int, default=64)
    parser.add_argument("--window", type=int, default=5)
    parser.add_argument("--negative", type=int, default=5)
    parser.add_argument("--min-count", type=int, default=2)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--sample", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-files", type=int, default=None)
    parser.add_argument("--max-playlists", type=int, default=None)
    parser.add_argument("--progress-every-files", type=int, default=50)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = GensimItem2VecConfig(
        vector_size=args.vector_size,
        window=args.window,
        negative=args.negative,
        min_count=args.min_count,
        epochs=args.epochs,
        workers=args.workers,
        sample=args.sample,
        seed=args.seed,
    )
    train_gensim_item2vec(
        mpd_data_dir=args.mpd_data_dir,
        output_dir=args.output_dir,
        config=config,
        max_files=args.max_files,
        max_playlists=args.max_playlists,
        progress_every_files=args.progress_every_files,
    )
    print(f"Wrote model to {args.output_dir}")


if __name__ == "__main__":
    main()
