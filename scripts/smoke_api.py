from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.main import app


async def request(method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, Any]:
    body_bytes = b"" if body is None else json.dumps(body).encode("utf-8")
    messages: list[dict[str, Any]] = []
    received = False

    async def receive() -> dict[str, Any]:
        nonlocal received
        if received:
            return {"type": "http.disconnect"}
        received = True
        return {"type": "http.request", "body": body_bytes, "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    if "?" in path:
        raw_path, query = path.split("?", 1)
    else:
        raw_path, query = path, ""

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": raw_path,
        "raw_path": raw_path.encode("utf-8"),
        "query_string": query.encode("utf-8"),
        "headers": [(b"host", b"testserver"), (b"content-type", b"application/json")],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }

    await app(scope, receive, send)
    status = next(message["status"] for message in messages if message["type"] == "http.response.start")
    response_body = b"".join(
        message.get("body", b"") for message in messages if message["type"] == "http.response.body"
    )
    try:
        payload = json.loads(response_body.decode("utf-8"))
    except json.JSONDecodeError:
        payload = response_body.decode("utf-8")
    return status, payload


async def run() -> None:
    async with app.router.lifespan_context(app):
        status, payload = await request("GET", "/health")
        assert status == 200, payload
        assert payload["model_loaded"], payload
        print(f"health ok: vocab_size={payload['vocab_size']}")

        for path in ("/", "/documentation", "/robots.txt", "/sitemap.xml"):
            status, _payload = await request("GET", path)
            assert status == 200, path
            print(f"{path} ok")

        status, rows = await request("GET", "/tracks/search?q=Best%20Day&limit=3&min_count=1")
        assert status == 200, rows
        assert rows, rows
        track_uri = rows[0]["track_uri"]
        print(f"search ok: {len(rows)} result(s)")

        status, payload = await request(
            "POST",
            "/tracks/batch",
            {"track_uris": [track_uri, "spotify:track:missing"]},
        )
        assert status == 200, payload
        assert len(payload["tracks"]) == 1, payload
        assert len(payload["missing_uris"]) == 1, payload
        print("batch ok")

        status, payload = await request(
            "POST",
            "/recommend/match",
            {"tracks": [{"artist": "American Authors", "title": "Best Day Of My Life"}]},
        )
        assert status == 200, payload
        assert payload["matched_count"] == 1, payload
        print("match ok")

        status, payload = await request(
            "POST",
            "/recommend/playlist",
            {
                "tracks": [
                    {"artist": "American Authors", "title": "Best Day Of My Life"},
                    {"artist": "The Verve", "title": "Bitter Sweet Symphony"},
                ],
                "top_n": 3,
                "recent_k": 2,
                "min_count": 1,
                "candidate_pool": 100,
                "preset": "balance",
            },
        )
        assert status == 200, payload
        assert payload["recommendations"], payload
        print(f"recommend ok: {len(payload['recommendations'])} result(s)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run API smoke checks without binding a port.")
    parser.parse_args()
    asyncio.run(run())


if __name__ == "__main__":
    main()
