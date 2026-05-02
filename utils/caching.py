from platformdirs import PlatformDirs
import json
import aiofiles


DIRS = PlatformDirs("lyric_cache", "TUIman")

class LyricsCache:
    def __init__(self):
        self.cache_path = DIRS.user_cache_path / "lyrics.json"

    async def _load(self) -> dict:
        if not self.cache_path.exists():
            return {}
        async with aiofiles.open(self.cache_path, "r") as f:
            return json.loads(await f.read())

    async def create_cache(self, song_path: str, lyrics: list) -> None:
        data = await self._load()
        data[song_path] = lyrics
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(self.cache_path, "w") as f:
            await f.write(json.dumps(data, indent=2))

    async def find_cache(self, song_path: str) -> list | None:
        return (await self._load()).get(song_path)