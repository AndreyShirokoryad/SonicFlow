from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_PLAYLIST = Path("data/playlist_examples/Мне нравится.txt")
DEFAULT_MPD_DATA_DIR = Path("data/MPD/archive/data")
DEFAULT_OUTPUT_DIR = Path("data/processed/playlist_analysis")


ARTIST_SPLIT_RE = re.compile(r"\s*(?:,|&| feat\.? | ft\.? | featuring | x |х|\+|/)\s*", re.I)
CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
NON_WORD_RE = re.compile(r"[^0-9a-zа-я]+", re.I)


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = value.casefold().replace("ё", "е")
    value = value.replace("’", "'").replace("`", "'")
    value = NON_WORD_RE.sub(" ", value)
    return " ".join(value.split())


def split_artists(value: str) -> set[str]:
    return {normalize(part) for part in ARTIST_SPLIT_RE.split(value) if normalize(part)}


def parse_playlist_line(line: str) -> dict[str, Any] | None:
    line = line.strip()
    if not line:
        return None
    if " - " not in line:
        artist = ""
        title = line
    else:
        artist, title = line.split(" - ", 1)
    return {
        "raw": line,
        "artist": artist.strip(),
        "title": title.strip(),
        "artist_tokens": sorted(split_artists(artist)),
        "title_key": normalize(title),
        "has_cyrillic": bool(CYRILLIC_RE.search(line)),
    }


def load_playlist(path: Path) -> list[dict[str, Any]]:
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = parse_playlist_line(line)
        if entry:
            entries.append(entry)
    return entries


def scan_mpd_candidates(
    mpd_data_dir: Path,
    wanted_titles: set[str],
    progress_every: int = 100,
) -> dict[str, dict[str, dict[str, Any]]]:
    candidates: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    files = sorted(mpd_data_dir.glob("mpd.slice.*.json"))
    for index, path in enumerate(files, start=1):
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        for playlist in payload.get("playlists", []):
            pid = playlist.get("pid")
            for track in playlist.get("tracks", []):
                title_key = normalize(track.get("track_name", ""))
                if title_key not in wanted_titles:
                    continue

                track_uri = track.get("track_uri", "")
                if not track_uri:
                    continue

                title_candidates = candidates[title_key]
                item = title_candidates.get(track_uri)
                if item is None:
                    item = {
                        "track_uri": track_uri,
                        "track_name": track.get("track_name", ""),
                        "artist_name": track.get("artist_name", ""),
                        "artist_uri": track.get("artist_uri", ""),
                        "album_name": track.get("album_name", ""),
                        "album_uri": track.get("album_uri", ""),
                        "duration_ms": track.get("duration_ms"),
                        "artist_tokens": sorted(split_artists(track.get("artist_name", ""))),
                        "occurrences": 0,
                        "playlist_count": 0,
                        "example_pids": [],
                    }
                    title_candidates[track_uri] = item

                item["occurrences"] += 1
                item["playlist_count"] += 1
                if len(item["example_pids"]) < 5:
                    item["example_pids"].append(pid)

        if progress_every and index % progress_every == 0:
            print(f"Scanned {index}/{len(files)} MPD slice files", flush=True)

    return candidates


def choose_match(entry: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    if not candidates:
        return {
            "input": entry["raw"],
            "mpd": None,
            "method": "unmatched",
            "confidence": 0.0,
            "candidate_count": 0,
        }

    entry_artist_tokens = set(entry["artist_tokens"])
    sorted_candidates = sorted(candidates, key=lambda item: item["occurrences"], reverse=True)
    equal_artist_matches = []
    overlap_matches = []
    for candidate in sorted_candidates:
        candidate_tokens = set(candidate["artist_tokens"])
        if entry_artist_tokens and entry_artist_tokens == candidate_tokens:
            equal_artist_matches.append(candidate)
        if entry_artist_tokens and entry_artist_tokens & candidate_tokens:
            overlap_matches.append(candidate)

    if equal_artist_matches:
        return {
            "input": entry["raw"],
            "mpd": equal_artist_matches[0],
            "method": "exact_title_same_artist_set",
            "confidence": 1.0,
            "candidate_count": len(candidates),
        }

    if overlap_matches:
        return {
            "input": entry["raw"],
            "mpd": overlap_matches[0],
            "method": "exact_title_artist_overlap",
            "confidence": 0.92,
            "candidate_count": len(candidates),
        }

    if len(candidates) == 1:
        return {
            "input": entry["raw"],
            "mpd": sorted_candidates[0],
            "method": "unique_title_only",
            "confidence": 0.55,
            "candidate_count": 1,
        }

    return {
        "input": entry["raw"],
        "mpd": None,
        "method": "ambiguous_title",
        "confidence": 0.0,
        "candidate_count": len(candidates),
    }


def summarize(entries: list[dict[str, Any]], matches: list[dict[str, Any]]) -> dict[str, Any]:
    matched = [match for match in matches if match["mpd"]]
    confident = [
        match
        for match in matched
        if match["method"] in {"exact_title_same_artist_set", "exact_title_artist_overlap"}
    ]
    return {
        "entries": len(entries),
        "unique_entries": len({entry["raw"] for entry in entries}),
        "matched_entries": len(matched),
        "matched_unique_track_uris": len({match["mpd"]["track_uri"] for match in matched}),
        "confident_matched_entries": len(confident),
        "unmatched_or_ambiguous_entries": len(entries) - len(matched),
        "match_rate": round(len(matched) / len(entries), 4) if entries else 0,
        "confident_match_rate": round(len(confident) / len(entries), 4) if entries else 0,
        "methods": dict(Counter(match["method"] for match in matches)),
        "total_mpd_occurrences_for_matched": sum(
            match["mpd"]["occurrences"] for match in matched
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Check playlist coverage in Spotify MPD.")
    parser.add_argument("--playlist", type=Path, default=DEFAULT_PLAYLIST)
    parser.add_argument("--mpd-data-dir", type=Path, default=DEFAULT_MPD_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--progress-every", type=int, default=100)
    args = parser.parse_args()

    entries = load_playlist(args.playlist)
    russian_entries = [entry for entry in entries if entry["has_cyrillic"]]
    candidates_by_title = scan_mpd_candidates(
        args.mpd_data_dir,
        {entry["title_key"] for entry in entries},
        progress_every=args.progress_every,
    )

    matches = [
        choose_match(entry, list(candidates_by_title.get(entry["title_key"], {}).values()))
        for entry in entries
    ]
    russian_matches = [
        match for entry, match in zip(entries, matches, strict=True) if entry["has_cyrillic"]
    ]

    report = {
        "playlist": str(args.playlist),
        "mpd_data_dir": str(args.mpd_data_dir),
        "all": summarize(entries, matches),
        "cyrillic_subset": summarize(russian_entries, russian_matches),
        "top_playlist_artists": Counter(entry["artist"] for entry in entries if entry["artist"]).most_common(20),
        "top_cyrillic_playlist_artists": Counter(
            entry["artist"] for entry in russian_entries if entry["artist"]
        ).most_common(30),
        "matches": matches,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = args.playlist.stem
    json_path = args.output_dir / f"{stem}_mpd_coverage.json"
    summary_path = args.output_dir / f"{stem}_mpd_coverage_summary.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    unmatched_examples = [match["input"] for match in matches if not match["mpd"]][:30]
    russian_unmatched_examples = [
        match["input"] for match in russian_matches if not match["mpd"]
    ][:30]
    matched_examples = [
        {
            "input": match["input"],
            "track_name": match["mpd"]["track_name"],
            "artist_name": match["mpd"]["artist_name"],
            "occurrences": match["mpd"]["occurrences"],
            "method": match["method"],
        }
        for match in matches
        if match["mpd"]
    ][:30]

    summary_lines = [
        f"# MPD coverage for {stem}",
        "",
        "## All tracks",
        json.dumps(report["all"], ensure_ascii=False, indent=2),
        "",
        "## Cyrillic subset",
        json.dumps(report["cyrillic_subset"], ensure_ascii=False, indent=2),
        "",
        "## Matched examples",
        json.dumps(matched_examples, ensure_ascii=False, indent=2),
        "",
        "## Unmatched examples",
        "\n".join(f"- {item}" for item in unmatched_examples),
        "",
        "## Cyrillic unmatched examples",
        "\n".join(f"- {item}" for item in russian_unmatched_examples),
        "",
    ]
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")

    print(f"Wrote {json_path}")
    print(f"Wrote {summary_path}")
    print(
        f"All: matched {report['all']['matched_entries']}/{report['all']['entries']} "
        f"({report['all']['match_rate']:.1%}), confident "
        f"{report['all']['confident_matched_entries']}/{report['all']['entries']} "
        f"({report['all']['confident_match_rate']:.1%})"
    )
    print(
        f"Cyrillic: matched {report['cyrillic_subset']['matched_entries']}/"
        f"{report['cyrillic_subset']['entries']} "
        f"({report['cyrillic_subset']['match_rate']:.1%}), confident "
        f"{report['cyrillic_subset']['confident_matched_entries']}/"
        f"{report['cyrillic_subset']['entries']} "
        f"({report['cyrillic_subset']['confident_match_rate']:.1%})"
    )


if __name__ == "__main__":
    main()
