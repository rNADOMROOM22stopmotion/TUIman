from platformdirs import PlatformDirs
import json
import aiofiles


DIRS = PlatformDirs("lyric_cache", "TUIman")

class Cache:
    def __init__(self):
        self.lyric_cache_path = DIRS.user_cache_path / "lyrics.json"
        self.album_cache_path = DIRS.user_cache_path / "last_used_path.txt"

    async def _load(self) -> dict:
        if not self.lyric_cache_path.exists():
            return {}
        async with aiofiles.open(self.lyric_cache_path, "r") as f:
            return json.loads(await f.read())

    async def create_cache(self, song_path: str, lyrics: list) -> None:
        data = await self._load()
        data[song_path] = lyrics
        self.lyric_cache_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(self.lyric_cache_path, "w") as f:
            await f.write(json.dumps(data, indent=2))

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