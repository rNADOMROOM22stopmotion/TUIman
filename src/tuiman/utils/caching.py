import hashlib
import os
from json import JSONDecodeError

from platformdirs import PlatformDirs
import json
import aiofiles


DIRS = PlatformDirs("lyric_cache", "TUIman")

class Cache:
    def __init__(self):
        self.lyric_cache_path = DIRS.user_cache_path / "lyrics.json"
        self.album_cache_path = DIRS.user_cache_path / "last_used_path.txt"
        self.album_art_path = DIRS.user_cache_path / "album_art"
        self.init_cache()

    def init_cache(self):
        """Ensure cache directories exist."""
        DIRS.user_cache_path.mkdir(parents=True, exist_ok=True)
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

    async def create_cache(self, song_path: str, lyrics: list) -> None:
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