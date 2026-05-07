import asyncio
import os
import re
import httpx
import mutagen.id3
from httpx import ReadTimeout
from .caching import Cache

BASE_URL = "https://lrclib.net/api/search"
lyrics_cache = Cache()

async def lrclib(**kwargs)->str:
    params = {
    "track_name": kwargs.get("title", None),
    "artist_name": kwargs.get("artist", None),
    "album_name": kwargs.get("album", None)
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=15.0)) as client:
        response = await client.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        first_match = data[0].get("syncedLyrics") if data else None
        return first_match

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
        return {"lyrics": []}

    # synced lyrics — stores (text, timestamp_in_ms) tuples
    song_meta = {}
    for key in tags.keys():
        # synced lyrics found
        if key.startswith("SYLT"):
            sylt = tags[key]
            lyrics = [
                (round(ms / 1000.0, 3), text.strip())
                for text, ms in sylt.text
                if text.strip()
            ]
            lyrics.sort(key=lambda x: x[0])
            # caching those lyrics
            await lyrics_cache.create_cache(song_path=path, lyrics=lyrics)
            return {"lyrics": lyrics}
        else:
            #track name
            if key.startswith("TIT2"):
                song_meta["title"] = tags[key].text
            #artist name
            if key.startswith("TPE1"):
                song_meta["artist"] = tags[key].text
            #album name
            if key.startswith("TALB"):
                song_meta["album"] = tags[key].text

    # Try to fetch lyrics from LRCLIB
    try:
        synced_lyrics = await lrclib(**song_meta)
    except ReadTimeout:
        synced_lyrics = []
    if synced_lyrics:
        lyrics = await parse_lrc_lyrics(lrc_text=synced_lyrics)
        # caching those lyrics
        await lyrics_cache.create_cache(song_path=path, lyrics=lyrics)
        return {"lyrics": lyrics}

    # nothing found, store empty list
    await lyrics_cache.create_cache(song_path=path, lyrics=[])
    return {"lyrics": []}

if "__main__" == __name__:
    # pprint(extract_lyrics("../data/album2/Human Nature - lyrics.mp3"))
    # {'lyrics': [(10.72, 'Looking out'),
    #             (13.35, 'Across the nighttime'),
    # pprint(extract_lyrics(""))
    lyrics = asyncio.run(lrclib(
            title="",
            artist="",
            album=""
        ))
    print(lyrics)
    # print(asyncio.run(extract_lyrics(path= "../data/exeter/IMAGINARY.mp3")))
