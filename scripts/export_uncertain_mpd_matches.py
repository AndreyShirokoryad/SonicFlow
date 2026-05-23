from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


DEFAULT_REPORT = Path("data/processed/playlist_analysis/Мне нравится_mpd_coverage.json")
DEFAULT_OUTPUT_DIR = Path("data/processed/playlist_analysis")


def split_input(value: str) -> tuple[str, str]:
    if " - " not in value:
        return "", value
    artist, title = value.split(" - ", 1)
    return artist, title


def main() -> None:
    parser = argparse.ArgumentParser(description="Export uncertain MPD playlist matches.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    rows = []
    for match in report["matches"]:
        mpd = match.get("mpd")
        if not mpd:
            continue
        if match["method"] != "unique_title_only":
            continue

        input_artist, input_title = split_input(match["input"])
        rows.append(
            {
                "input_artist": input_artist,
                "input_title": input_title,
                "recognized_artist": mpd.get("artist_name", ""),
                "recognized_title": mpd.get("track_name", ""),
                "method": match["method"],
                "confidence": match["confidence"],
                "candidate_count": match["candidate_count"],
                "mpd_occurrences": mpd.get("occurrences", 0),
                "track_uri": mpd.get("track_uri", ""),
            }
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "Мне нравится_mpd_uncertain_matches.csv"
    md_path = args.output_dir / "Мне нравится_mpd_uncertain_matches.md"

    columns = [
        "input_artist",
        "input_title",
        "recognized_artist",
        "recognized_title",
        "method",
        "confidence",
        "candidate_count",
        "mpd_occurrences",
        "track_uri",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Неуверенные MPD-распознавания",
        "",
        f"Всего строк: {len(rows)}",
        "",
        "| Песня в плейлисте | Артист в плейлисте | Распознанная песня | Распознанный артист | Вхождений в MPD |",
        "|---|---|---|---|---:|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["input_title"].replace("|", "\\|"),
                    row["input_artist"].replace("|", "\\|"),
                    row["recognized_title"].replace("|", "\\|"),
                    row["recognized_artist"].replace("|", "\\|"),
                    str(row["mpd_occurrences"]),
                ]
            )
            + " |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {csv_path}")
    print(f"Wrote {md_path}")
    print(f"Rows: {len(rows)}")


if __name__ == "__main__":
    main()
