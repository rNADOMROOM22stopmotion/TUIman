import hashlib
import os
from json import JSONDecodeError
from typing import Any

from platformdirs import PlatformDirs
import json
import aiofiles


DIRS = PlatformDirs("tuiman", "TUIman")
PLAYLIST_SCHEMA_VERSION = 1

class Cache:
    def __init__(self):
        self.lyric_cache_path = DIRS.user_cache_path / "lyrics.json"
        self.album_cache_path = DIRS.user_cache_path / "last_used_path.txt"
        self.album_art_path = DIRS.user_cache_path / "album_art"
        self.playlist_config_path = DIRS.user_config_path / "playlists.json"
        self.init_cache()

    def init_cache(self):
        """Ensure cache directories exist."""
        DIRS.user_cache_path.mkdir(parents=True, exist_ok=True)
        DIRS.user_config_path.mkdir(parents=True, exist_ok=True)
        self.album_art_path.mkdir(parents=True, exist_ok=True)

    async def _load(self) -> dict:
        if not self.lyric_cache_path.exists():
            return {}

        try:
            async with aiofiles.open(self.lyric_cache_path, "r") as f:
                raw = await f.read()
            return json.loads(raw) if raw.strip() else {}
        except (JSONDecodeError, OSError):
            return {}

    async def create_cache(self, song_path: str, lyrics: dict) -> None:
        data = await self._load()
        data[song_path] = lyrics

        self.lyric_cache_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.lyric_cache_path.with_suffix(".json.tmp")

        async with aiofiles.open(temp_path, "w") as f:
            await f.write(json.dumps(data, indent=2))

        os.replace(temp_path, self.lyric_cache_path)

    def create_path_cache(self, path: str):
        with open(self.album_cache_path, "w") as f:
            f.write(path)

    def find_path_cache(self):
        try:
            with open(self.album_cache_path, "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            return ""

    async def find_cache(self, song_path: str) -> list | None:
        return (await self._load()).get(song_path)

    @staticmethod
    def _empty_playlist_payload() -> dict[str, Any]:
        return {
            "version": PLAYLIST_SCHEMA_VERSION,
            "playlists": {},
        }

    @staticmethod
    def _normalize_playlist_songs(raw_songs: Any) -> list[dict[str, str]]:
        if isinstance(raw_songs, dict):
            raw_songs = raw_songs.get("songs", raw_songs)

        if isinstance(raw_songs, dict):
            raw_songs = [
                {"name": name, "path": path}
                for name, path in raw_songs.items()
            ]

        if not isinstance(raw_songs, list):
            return []

        songs = []
        seen_paths = set()
        for raw_song in raw_songs:
            if not isinstance(raw_song, dict):
                continue

            song_name = raw_song.get("name")
            song_path = raw_song.get("path")
            if not isinstance(song_name, str) or not isinstance(song_path, str):
                continue

            song_name = song_name.strip()
            song_path = song_path.strip()
            if not song_name or not song_path or song_path in seen_paths:
                continue

            songs.append({"name": song_name, "path": song_path})
            seen_paths.add(song_path)

        return songs

    def _load_playlist_payload(self) -> dict[str, Any]:
        if not self.playlist_config_path.exists():
            return self._empty_playlist_payload()

        try:
            raw = self.playlist_config_path.read_text(encoding="utf-8")
            payload = json.loads(raw) if raw.strip() else {}
        except (JSONDecodeError, OSError):
            return self._empty_playlist_payload()

        playlists = payload.get("playlists") if isinstance(payload, dict) else None
        if not isinstance(playlists, dict):
            return self._empty_playlist_payload()

        normalized = self._empty_playlist_payload()
        for playlist_name, songs in playlists.items():
            if not isinstance(playlist_name, str):
                continue

            playlist_name = playlist_name.strip()
            if not playlist_name:
                continue

            normalized["playlists"][playlist_name] = self._normalize_playlist_songs(songs)

        return normalized

    def _save_playlist_payload(self, payload: dict[str, Any]) -> None:
        self.playlist_config_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.playlist_config_path.with_suffix(".json.tmp")
        temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(temp_path, self.playlist_config_path)

    def load_playlists(self) -> dict[str, list[dict[str, str]]]:
        return self._load_playlist_payload()["playlists"]

    def list_playlists(self) -> list[str]:
        return list(self.load_playlists())

    def add_song_to_playlist(
        self,
        playlist_name: str,
        song_name: str,
        song_path: str,
    ) -> bool:
        playlist_name = playlist_name.strip()
        song_name = song_name.strip()
        song_path = song_path.strip()
        if not playlist_name or not song_name or not song_path:
            return False

        payload = self._load_playlist_payload()
        playlist = payload["playlists"].setdefault(playlist_name, [])
        if any(song["path"] == song_path for song in playlist):
            return False

        playlist.append({"name": song_name, "path": song_path})
        self._save_playlist_payload(payload)
        return True

    def playlists_as_library(self) -> dict[str, dict]:
        library = {}
        for playlist_name, songs in self.load_playlists().items():
            display_songs = {}
            seen_names = {}

            for song in songs:
                base_name = song["name"]
                count = seen_names.get(base_name, 0) + 1
                seen_names[base_name] = count
                display_name = base_name if count == 1 else f"{base_name} ({count})"

                while display_name in display_songs:
                    count += 1
                    seen_names[base_name] = count
                    display_name = f"{base_name} ({count})"

                display_songs[display_name] = song["path"]

            library[playlist_name] = {
                "songs": display_songs,
                "album_art": "",
                "is_playlist": True,
            }

        return library

    async def find_album_art_cache(self, album_path: str) -> str | None:
        """Return cached image path if it exists on disk, else None."""
        cache_dir = self.album_art_path
        # Use a hash of the album path as the filename to avoid collisions
        key = hashlib.md5(album_path.encode()).hexdigest()
        cached = cache_dir / f"{key}.jpg"
        return str(cached) if cached.exists() else None

    async def create_album_art_cache(self, album_path: str, image_data: bytes) -> str:
        """Write image bytes to cache and return the cached file path."""
        cache_dir = self.album_art_path
        cache_dir.mkdir(parents=True, exist_ok=True)
        key = hashlib.md5(album_path.encode()).hexdigest()
        cached = cache_dir / f"{key}.jpg"
        async with aiofiles.open(cached, "wb") as f:
            await f.write(image_data)
        return str(cached)
