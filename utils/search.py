from pathlib import Path
from pprint import pprint

from textual.widgets import Input, OptionList

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

def _load_album(album_path: Path) -> dict | None:
    songs = {}
    album_art = ""

    for entry in sorted(album_path.iterdir(), key=lambda e: e.name.casefold()):
        if not entry.is_file():
            continue

        extension = entry.suffix.casefold()
        if extension in SUPPORTED_IMAGE_EXTENSIONS and not album_art:
            album_art = str(entry)
            continue

        if extension not in SUPPORTED_AUDIO_EXTENSIONS:
            continue

        songs[entry.stem] = str(entry)

    if not songs:
        return None

    return {
        "songs": songs,
        "album_art": album_art,
    }


def load_library(root_dir: str) -> dict:
    library = {}
    root_path = Path(root_dir).expanduser().resolve()

    album_paths = [entry for entry in root_path.iterdir() if entry.is_dir()]
    if not album_paths:
        album_paths = [root_path]

    for album_path in sorted(album_paths, key=lambda e: e.name.casefold()):
        album = _load_album(album_path)
        if album is None:
            continue
        library[album_path.name] = album
    return library


if "__main__" == __name__:
    library = load_library(r"F:\koding\PythonProject\data")
    # print(*library.get("album2", []).keys())
    # print(library)
    # print(list(library.values())[0]['album_art'])
    # print([*library.keys()])
    # for album in library:
    #     print(album)
    print(next((songs["Chic 'N' Stu_spotdown.org.mp3"] for album in library.values() for songs in [album['songs']] if "Chic 'N' Stu_spotdown.org.mp3" in songs), ""))
