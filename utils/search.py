import os
from pprint import pprint

from textual.widgets import Input, OptionList


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

def load_library(root_dir: str) -> dict:
    library = {}
    for album in sorted(os.scandir(root_dir), key=lambda e: e.name):
        if not album.is_dir():
            continue
        songs = {}
        album_art = ""

        # Scan through all entries in the album directory, sorted by name
        entries = sorted(os.scandir(album.path), key=lambda e: e.name)
        for entry in entries:
            if not entry.is_file():
                continue
            filename = entry.name.lower()
            if filename.endswith(".jpg") or filename.endswith(".png"):
                album_art = entry.path
            if not filename.endswith(".mp3"):
                continue
            song_name = os.path.splitext(entry.name)[0]
            # Store in dictionary: {song_name: full_path}
            songs[song_name] = entry.path
        if songs:
            library[album.name] = {
                "songs": songs,
                "album_art": album_art
            }
    return library


if "__main__" == __name__:
    library = load_library(r"F:\koding\PythonProject\data")
    print(*library.get("album2", []).keys())
    print(library)
    print(list(library.values())[0]['album_art'])
    # print([*library.keys()])
    # for album in library:
    #     print(album)
