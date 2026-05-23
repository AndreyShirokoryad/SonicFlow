from __future__ import annotations

import json
import re
import time
import unicodedata
from pathlib import Path
from typing import Any, Iterator


ARTIST_SPLIT_RE = re.compile(r"\s*(?:,|&| feat\.? | ft\.? | featuring | x |х|\+|/)\s*", re.I)
NON_WORD_RE = re.compile(r"[^0-9a-zа-я]+", re.I)


def format_seconds(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = value.casefold().replace("ё", "е")
    value = value.replace("’", "'").replace("`", "'")
    value = NON_WORD_RE.sub(" ", value)
    return " ".join(value.split())


def split_artists(value: str) -> set[str]:
    return {normalize_text(part) for part in ARTIST_SPLIT_RE.split(value) if normalize_text(part)}


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
        title_key = normalize_text(item.get("track_name", ""))
        artist_key = normalize_text(item.get("artist_name", ""))
        by_artist_title.setdefault((artist_key, title_key), item["track_uri"])
        by_title.setdefault(title_key, []).append(item["track_uri"])
    return by_artist_title, by_title


def iter_mpd_files(mpd_data_dir: Path, max_files: int | None = None) -> list[Path]:
    files = sorted(mpd_data_dir.glob("mpd.slice.*.json"))
    if max_files is not None:
        files = files[:max_files]
    if not files:
        raise FileNotFoundError(f"No MPD slice files found in {mpd_data_dir}")
    return files


class MPDPlaylistCorpus:
    def __init__(
        self,
        mpd_data_dir: Path,
        max_files: int | None = None,
        max_playlists: int | None = None,
        progress_every_files: int = 50,
        total_passes_hint: int | None = None,
    ) -> None:
        self.mpd_data_dir = mpd_data_dir
        self.max_files = max_files
        self.max_playlists = max_playlists
        self.progress_every_files = progress_every_files
        self.total_passes_hint = total_passes_hint
        self.pass_number = 0

    def __iter__(self) -> Iterator[list[str]]:
        yielded = 0
        self.pass_number += 1
        files = iter_mpd_files(self.mpd_data_dir, max_files=self.max_files)
        total_files = len(files)
        started_at = time.monotonic()
        total_label = f"/{self.total_passes_hint}" if self.total_passes_hint else ""
        print(
            f"Corpus pass {self.pass_number}{total_label}: "
            f"starting {total_files} MPD slice files",
            flush=True,
        )

        for file_index, path in enumerate(files, start=1):
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            for playlist in payload.get("playlists", []):
                sentence = [
                    track["track_uri"]
                    for track in playlist.get("tracks", [])
                    if track.get("track_uri")
                ]
                if len(sentence) >= 2:
                    yield sentence
                yielded += 1
                if self.max_playlists is not None and yielded >= self.max_playlists:
                    print(
                        f"Corpus pass {self.pass_number}{total_label}: "
                        f"stopped at max_playlists={self.max_playlists}",
                        flush=True,
                    )
                    return

            if self.progress_every_files and file_index % self.progress_every_files == 0:
                elapsed = time.monotonic() - started_at
                files_per_second = file_index / max(elapsed, 1e-9)
                eta_seconds = (total_files - file_index) / max(files_per_second, 1e-9)
                percent = 100.0 * file_index / total_files
                print(
                    f"Corpus pass {self.pass_number}{total_label}: "
                    f"{file_index}/{total_files} files ({percent:.1f}%), "
                    f"playlists={yielded}, elapsed={format_seconds(elapsed)}, "
                    f"eta={format_seconds(eta_seconds)}",
                    flush=True,
                )

        elapsed = time.monotonic() - started_at
        print(
            f"Corpus pass {self.pass_number}{total_label}: completed "
            f"{total_files}/{total_files} files, playlists={yielded}, "
            f"elapsed={format_seconds(elapsed)}",
            flush=True,
        )


def collect_metadata_for_keys(
    mpd_data_dir: Path,
    keys: set[str],
    max_files: int | None = None,
    max_playlists: int | None = None,
    progress_every_files: int = 50,
) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}
    seen_playlists = 0
    files = iter_mpd_files(mpd_data_dir, max_files=max_files)
    total_files = len(files)
    started_at = time.monotonic()
    print(
        f"Metadata export: scanning up to {total_files} MPD slice files "
        f"for {len(keys)} vocab tracks",
        flush=True,
    )
    for file_index, path in enumerate(files, start=1):
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        for playlist in payload.get("playlists", []):
            for track in playlist.get("tracks", []):
                uri = track.get("track_uri")
                if not uri or uri not in keys or uri in metadata:
                    continue
                metadata[uri] = {
                    "track_uri": uri,
                    "track_name": track.get("track_name", ""),
                    "artist_name": track.get("artist_name", ""),
                    "artist_uri": track.get("artist_uri", ""),
                    "album_name": track.get("album_name", ""),
                    "album_uri": track.get("album_uri", ""),
                    "duration_ms": track.get("duration_ms", ""),
                }
                if len(metadata) == len(keys):
                    elapsed = time.monotonic() - started_at
                    print(
                        f"Metadata export: found all {len(keys)} tracks, "
                        f"elapsed={format_seconds(elapsed)}",
                        flush=True,
                    )
                    return metadata
            seen_playlists += 1
            if max_playlists is not None and seen_playlists >= max_playlists:
                return metadata

        if progress_every_files and file_index % progress_every_files == 0:
            elapsed = time.monotonic() - started_at
            files_per_second = file_index / max(elapsed, 1e-9)
            eta_seconds = (total_files - file_index) / max(files_per_second, 1e-9)
            percent = 100.0 * file_index / total_files
            print(
                f"Metadata export: {file_index}/{total_files} files ({percent:.1f}%), "
                f"found={len(metadata)}/{len(keys)}, elapsed={format_seconds(elapsed)}, "
                f"eta={format_seconds(eta_seconds)}",
                flush=True,
            )

    elapsed = time.monotonic() - started_at
    print(
        f"Metadata export: completed, found={len(metadata)}/{len(keys)}, "
        f"elapsed={format_seconds(elapsed)}",
        flush=True,
    )
    return metadata
