import os
from pprint import pprint
import mutagen.id3


def extract_lyrics(path: str) -> dict:
    """
    Extracts synced lyrics from an mp3's ID3 tags (SYLT frame).
    Falls back to unsynced lyrics (USLT) with timestamp 0.0 if no SYLT found.
    Returns {"lyrics": [{"time": float, "text": str}, ...]}
    """
    if not os.path.exists(path):
        return {"lyrics": []}

    try:
        tags = mutagen.id3.ID3(path)
    except mutagen.id3.ID3NoHeaderError:
        return {"lyrics": []}

    # synced lyrics — SYLT stores (text, timestamp_in_ms) tuples
    for key in tags.keys():
        if key.startswith("SYLT"):
            sylt = tags[key]
            lyrics = [
                (round(ms / 1000.0, 3), text.strip())
                for text, ms in sylt.text
                if text.strip()
            ]
            lyrics.sort(key=lambda x: x[0])
            return {"lyrics": lyrics}

    # fallback: unsynced lyrics (USLT) — no timestamps available
    for key in tags.keys():
        if key.startswith("USLT"):
            uslt = tags[key]
            lines = [line.strip() for line in uslt.text.splitlines() if line.strip()]
            lyrics = [{"time": 0.0, "text": line} for line in lines]
            return {"lyrics": lyrics}

    return {"lyrics": []}

if "__main__" == __name__:
    # pprint(extract_lyrics("../data/album2/Human Nature - lyrics.mp3"))
    # {'lyrics': [(10.72, 'Looking out'),
    #             (13.35, 'Across the nighttime'),
    #             (16.06, 'The city winks a sleepless eye'),
    #             (21.01, 'Hear her voice'),
    #             (24.05, 'Shake my window'),
    #             (26.55, 'Sweet seducing sighs'),
    #             (31.33, 'Get me out'),
    #             (34.29, 'Into the nighttime'),
    pprint(extract_lyrics(""))