from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_MPD_DATA_DIR = Path("data/MPD/archive/data")
DEFAULT_OUTPUT_DIR = Path("data/processed/mpd")
CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")


def has_cyrillic(*values: str) -> bool:
    return any(CYRILLIC_RE.search(value or "") for value in values)


def scan_cyrillic_tracks(
    mpd_data_dir: Path,
    progress_every: int,
) -> dict[str, dict[str, Any]]:
    tracks: dict[str, dict[str, Any]] = {}
    files = sorted(mpd_data_dir.glob("mpd.slice.*.json"))

    for index, path in enumerate(files, start=1):
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        for playlist in payload.get("playlists", []):
            pid = playlist.get("pid")
            for track in playlist.get("tracks", []):
                if not has_cyrillic(
                    track.get("track_name", ""),
                    track.get("artist_name", ""),
                    track.get("album_name", ""),
                ):
                    continue

                track_uri = track.get("track_uri", "")
                if not track_uri:
                    continue

                item = tracks.get(track_uri)
                if item is None:
                    item = {
                        "track_uri": track_uri,
                        "track_name": track.get("track_name", ""),
                        "artist_name": track.get("artist_name", ""),
                        "artist_uri": track.get("artist_uri", ""),
                        "album_name": track.get("album_name", ""),
                        "album_uri": track.get("album_uri", ""),
                        "duration_ms": track.get("duration_ms"),
                        "occurrences": 0,
                        "example_pids": [],
                    }
                    tracks[track_uri] = item

                item["occurrences"] += 1
                if len(item["example_pids"]) < 5:
                    item["example_pids"].append(pid)

        if progress_every and index % progress_every == 0:
            print(f"Scanned {index}/{len(files)} MPD slice files", flush=True)

    return tracks


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a unique Cyrillic track table from Spotify MPD."
    )
    parser.add_argument("--mpd-data-dir", type=Path, default=DEFAULT_MPD_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--progress-every", type=int, default=100)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / "mpd_cyrillic_tracks.csv"
    manifest_path = args.output_dir / "mpd_cyrillic_tracks_manifest.json"

    tracks = scan_cyrillic_tracks(args.mpd_data_dir, args.progress_every)
    rows = sorted(tracks.values(), key=lambda item: item["occurrences"], reverse=True)

    columns = [
        "track_uri",
        "track_name",
        "artist_name",
        "artist_uri",
        "album_name",
        "album_uri",
        "duration_ms",
        "occurrences",
        "example_pids",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            out = dict(row)
            out["example_pids"] = json.dumps(out["example_pids"], ensure_ascii=False)
            writer.writerow(out)

    manifest = {
        "mpd_data_dir": str(args.mpd_data_dir),
        "output": str(output_path),
        "unique_cyrillic_tracks": len(rows),
        "total_occurrences": sum(row["occurrences"] for row in rows),
        "filter": "Cyrillic characters in track_name, artist_name, or album_name.",
        "top_tracks": [
            {
                "track_name": row["track_name"],
                "artist_name": row["artist_name"],
                "occurrences": row["occurrences"],
            }
            for row in rows[:30]
        ],
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {output_path}")
    print(f"Wrote {manifest_path}")
    print(
        f"Unique Cyrillic tracks: {manifest['unique_cyrillic_tracks']}; "
        f"occurrences: {manifest['total_occurrences']}"
    )


if __name__ == "__main__":
    main()
