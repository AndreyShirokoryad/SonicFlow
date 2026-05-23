from __future__ import annotations

from src.mpd_corpus import normalize_text, split_artists

from backend.app.services.model_store import Item2VecModelStore


class PlaylistMatcher:
    def __init__(self, model_store: Item2VecModelStore) -> None:
        self.model_store = model_store

    def match_text_tracks(self, tracks: list[dict[str, str]]) -> list[str]:
        return [
            match["track_uri"]
            for match in self.match_text_tracks_detailed(tracks)
            if match["matched"] and match["track_uri"]
        ]

    def match_text_tracks_detailed(self, tracks: list[dict[str, str]]) -> list[dict]:
        matches = []
        for track in tracks:
            artist = track.get("artist", "")
            title = track.get("title", "")
            artist_key = normalize_text(artist)
            title_key = normalize_text(title)

            exact = self.model_store.by_artist_title.get((artist_key, title_key))
            if exact:
                matches.append(
                    self._build_match(
                        artist,
                        title,
                        exact,
                        status="exact",
                        confidence=1.0,
                        matched=True,
                    )
                )
                continue

            artist_tokens = split_artists(artist)
            fallback_uri = None
            for uri in self.model_store.by_title.get(title_key, []):
                item = self.model_store.vocab[self.model_store.uri_to_idx[uri]]
                if artist_tokens & split_artists(item.get("artist_name", "")):
                    fallback_uri = uri
                    break
            if fallback_uri:
                matches.append(
                    self._build_match(
                        artist,
                        title,
                        fallback_uri,
                        status="artist_title_fallback",
                        confidence=0.85,
                        matched=True,
                    )
                )
                continue

            title_candidates = self.model_store.by_title.get(title_key, [])
            if title_candidates:
                matches.append(
                    self._build_match(
                        artist,
                        title,
                        title_candidates[0],
                        status="title_only_uncertain",
                        confidence=0.45,
                        matched=False,
                    )
                )
                continue

            matches.append(
                {
                    "input_artist": artist,
                    "input_title": title,
                    "status": "not_found",
                    "confidence": 0.0,
                    "matched": False,
                    "track_uri": None,
                    "track_name": "",
                    "artist_name": "",
                    "album_name": "",
                    "count": 0,
                }
            )
        return matches

    def _build_match(
        self,
        input_artist: str,
        input_title: str,
        track_uri: str,
        status: str,
        confidence: float,
        matched: bool,
    ) -> dict:
        item = self.model_store.vocab[self.model_store.uri_to_idx[track_uri]]
        return {
            "input_artist": input_artist,
            "input_title": input_title,
            "status": status,
            "confidence": confidence,
            "matched": matched,
            "track_uri": item.get("track_uri"),
            "track_name": item.get("track_name", ""),
            "artist_name": item.get("artist_name", ""),
            "album_name": item.get("album_name", ""),
            "count": int(item.get("count", 0)),
        }
