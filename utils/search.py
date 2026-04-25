import os
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
        songs = {
            os.path.splitext(song.name)[0]: song.path
            for song in sorted(os.scandir(album.path), key=lambda e: e.name)
            if song.is_file() and song.name.lower().endswith(".mp3")
        }
        if songs:
            library[album.name] = songs
    return library


if "__main__" == __name__:
    library = load_library(r"F:\koding\PythonProject\data")
    print(*library.get("album2", []).keys())
    # print([*library.keys()])
    # for album in library:
    #     print(album)
