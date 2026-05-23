from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _csv_env(name: str, default: str) -> tuple[str, ...]:
    value = os.getenv(name, default)
    return tuple(part.strip() for part in value.split(",") if part.strip())


@dataclass(frozen=True)
class Settings:
    model_dir: Path = Path(os.getenv("MODEL_DIR", "data/models/item2vec_mpd_gensim"))
    default_top_n: int = int(os.getenv("DEFAULT_TOP_N", "20"))
    default_recent_k: int = int(os.getenv("DEFAULT_RECENT_K", "5"))
    default_min_count: int = int(os.getenv("DEFAULT_MIN_COUNT", "10"))
    default_candidate_pool: int = int(os.getenv("DEFAULT_CANDIDATE_POOL", "10000"))
    max_playlist_tracks: int = int(os.getenv("MAX_PLAYLIST_TRACKS", "500"))
    cors_origins: tuple[str, ...] = _csv_env("CORS_ORIGINS", "*")
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "http://localhost")
    github_url: str = os.getenv(
        "GITHUB_URL",
        "https://github.com/AndreyShirokoryad/SonicFlow",
    )
    enable_faiss: bool = os.getenv("ENABLE_FAISS", "1") == "1"
    require_model_on_startup: bool = os.getenv("REQUIRE_MODEL_ON_STARTUP", "0") == "1"


settings = Settings()
