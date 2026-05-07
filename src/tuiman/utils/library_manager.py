from pprint import pprint
from textual.widgets import Input, OptionList
from mutagen.id3 import ID3, APIC
from pathlib import Path
from src.tuiman.utils.caching import Cache

SUPPORTED_AUDIO_EXTENSIONS = {".mp3"}
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def search_function(object, event: Input.Changed, iterables) -> None:
    """search helper function
        :param object: self instance of class Input
        :param event: event of class Input
        :param iterables: the song/ album list
    """
    query = event.value.lower()

    filtered = [a for a in iterables if query in a.lower()]

    option_list = object.query_one(OptionList)
    option_list.clear_options()
    for song_or_album in filtered:
        option_list.add_option(song_or_album)

async def _extract_album_art(album_path: Path, songs: dict, cache: Cache) -> str:
    """Try cache first, then extract from ID3 tags, store result in cache."""
    cached = await cache.find_album_art_cache(str(album_path))
    if cached:
        return cached

    for song_path in songs.values():
        try:
            tags = ID3(song_path)
            for tag in tags.values():
                if isinstance(tag, APIC):
                    return await cache.create_album_art_cache(str(album_path), tag.data)
        except Exception:
            continue

    return ""


def _load_album(album_path: Path) -> dict | None:
    songs = {}

    for extension in SUPPORTED_AUDIO_EXTENSIONS:
        for entry in album_path.glob(f"*{extension}"):
            songs[entry.stem] = str(entry)

    if not songs:
        return None

    # Sort by filename for consistent ordering
    songs = dict(sorted(songs.items(), key=lambda kv: kv[0].casefold()))
    return {"songs": songs, "album_art": ""}


async def load_library(root_dir: str, cache: Cache) -> dict:
    library = {}
    seen_names = {}  # name -> count of times seen
    root_path = Path(root_dir).expanduser().resolve()

    album_paths = set()
    for extension in SUPPORTED_AUDIO_EXTENSIONS:
        for match in root_path.rglob(f"*{extension}"):
            album_paths.add(match.parent)

    if not album_paths:
        album_paths = {root_path}

    for album_path in sorted(album_paths, key=lambda e: e.name.casefold()):
        album = _load_album(album_path)
        if album is None:
            continue

        album["album_art"] = await _extract_album_art(album_path, album["songs"], cache)

        name = album_path.name
        if name not in seen_names:
            seen_names[name] = 0
            library[name] = album
        else:
            seen_names[name] += 1
            library[f"{name} ({seen_names[name]})"] = album

    return library


if "__main__" == __name__:
    library = load_library("../../../data")
    # print(*library.get("album2", []).keys())
    pprint(library)
    # print(list(library.values())[0]['album_art'])
    # print([*library.keys()])
    # for album in library:
    #     print(album)
    #print(next((songs["Chic 'N' Stu.mp3"] for album in library.values() for songs in [album['songs']] if "Chic 'N' Stu.mp3" in songs), ""))
