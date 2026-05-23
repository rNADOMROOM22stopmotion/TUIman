import asyncio
import os
import re
from pprint import pprint
import httpx
import mutagen.id3
from httpx import ReadTimeout
from .caching import Cache

BASE_URL = "https://lrclib.net/api/search"
lyrics_cache = Cache()

async def lrclib(**kwargs)->tuple[str, str | None]:
    params = {
    "track_name": kwargs.get("title", None),
    "artist_name": kwargs.get("artist", None),
    "album_name": kwargs.get("album", None)
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=15.0)) as client:
        response = await client.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        if data:
            synced_lyrics = data[0].get("syncedLyrics") if data else None
            plain_lyrics = data[0].get("plainLyrics") if data else None
        else:
            synced_lyrics = plain_lyrics = None
        return synced_lyrics, plain_lyrics

async def parse_lrc_lyrics(lrc_text: str) -> list[tuple[float, str]]:
    pattern = re.compile(r'\[(\d+):(\d+\.\d+)\]\s*(.*)')
    results = []

    for line in lrc_text.splitlines():
        m = pattern.match(line.strip())
        if not m:
            continue
        minutes, seconds, text = int(m.group(1)), float(m.group(2)), m.group(3).strip()
        if text:
            ts = round(minutes * 60 + seconds, 2)
            results.append((ts, text))

    return sorted(results, key=lambda x: x[0])


async def extract_lyrics(path: str) -> dict:
    """
    Extracts synced lyrics from an mp3's ID3 tags (SYLT frame).
    Falls back to LRCLIB
    Stores lyrics in .cache
    Returns {"lyrics": [(time_ms: float, "text": str), ...]}
    """
    if not os.path.exists(path):
        return {"lyrics": []}

    try:
        tags = mutagen.id3.ID3(path)
    except mutagen.id3.ID3NoHeaderError:
        return {"lyrics": {}}

    song_meta = {}
    lyrics = {
        "synced_lyrics": [],
        "plain_lyrics": "",
    }

    for key in tags.keys():
        if key.startswith("SYLT"):
            sylt = tags[key]
            lyrics["synced_lyrics"].extend(
                (round(ms / 1000.0, 3), text.strip())
                for text, ms in sylt.text
                if text.strip()
            )

        if key.startswith("USLT"):
            uslt = tags[key]
            plain_text = uslt.text.strip()

            if plain_text:
                if lyrics["plain_lyrics"]:
                    lyrics["plain_lyrics"] += "\n" + plain_text
                else:
                    lyrics["plain_lyrics"] = plain_text

        if key.startswith("TIT2"):
            song_meta["title"] = " ".join(tags[key].text)

        if key.startswith("TPE1"):
            song_meta["artist"] = " ".join(tags[key].text)

        if key.startswith("TALB"):
            song_meta["album"] = " ".join(tags[key].text)

    lyrics["synced_lyrics"].sort(key=lambda x: x[0])

    metadata_has_synced = bool(lyrics["synced_lyrics"])
    metadata_has_plain = bool(lyrics["plain_lyrics"])

    if metadata_has_synced and metadata_has_plain:
        await lyrics_cache.create_cache(song_path=path, lyrics=lyrics)
        return {"lyrics": lyrics}

    try:
        lrclib_synced, lrclib_plain = await lrclib(**song_meta)
    except ReadTimeout:
        lrclib_synced = None
        lrclib_plain = None

    if not metadata_has_synced and lrclib_synced:
        lyrics["synced_lyrics"] = await parse_lrc_lyrics(lrc_text=lrclib_synced)

    if not metadata_has_plain and lrclib_plain:
        lyrics["plain_lyrics"] = lrclib_plain.strip()

    if lyrics["synced_lyrics"] or lyrics["plain_lyrics"]:
        await lyrics_cache.create_cache(song_path=path, lyrics=lyrics)
        return {"lyrics": lyrics}

    await lyrics_cache.create_cache(song_path=path, lyrics={})
    return {"lyrics": {}}

if "__main__" == __name__:
    print(asyncio.run(extract_lyrics(r'''F:\koding\PythonProject\data\album2\Human Nature - lyrics3.mp3''')))
    # {'lyrics': [(10.72, 'Looking out'),
    #             (13.35, 'Across the nighttime'),
    # pprint(extract_lyrics(""))
    # lyrics = asyncio.run(lrclib(
    #         title="Heart-Shaped Box",
    #         artist="Nirvana",
    #         album="In Utero"
    #     ))