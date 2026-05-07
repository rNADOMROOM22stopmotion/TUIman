import asyncio
from pathlib import Path
from rich_pixels import Pixels
from textual import work
from textual.app import ComposeResult, RenderResult
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Input, OptionList, RadioSet, RadioButton, Markdown, LoadingIndicator
from ..utils.caching import Cache
from ..utils.library_manager import search_function, load_library
from ..utils.lyrics import extract_lyrics
from ..utils.models import ReversibleIterator
from ..utils.player import get_progress, play_song

cache = Cache()
UNKNOWN_COVER_PATH = str(Path(__file__).resolve().parent.parent / "media" / "unknown.png")

class AlbumCover(Widget):
    """using rich renderable to render ascii album cover"""
    path: reactive[str] = reactive(UNKNOWN_COVER_PATH)

    def __init__(self):
        super().__init__()
        self._album_cover = None

    def on_mount(self) -> None:
        self._album_cover = Pixels.from_image_path(UNKNOWN_COVER_PATH, resize=(20, 15))

    def watch_path(self, new_path: str) -> None:
        self._album_cover = Pixels.from_image_path(new_path or UNKNOWN_COVER_PATH, resize=(20, 15))
        self.refresh()

    def render(self) -> RenderResult:
        return self._album_cover

class AlbumList(Widget):
    """Lists user albums"""

    data: reactive[dict] = reactive({}, init=False)
    def __init__(self, data: dict) -> None:
        super().__init__()
        self.albums = [*data.keys()]

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search album name", type="text")
        yield LoadingIndicator()
        yield OptionList(
            *self.albums
        )

    def on_mount(self) -> None:
        self.border_title = "Albums"

    def on_input_changed(self, event: Input.Changed) -> None:
        search_function(self, event, self.albums)

    def watch_data(self, data: dict) -> None:
        """"""
        self.albums = [*data.keys()]
        option_list = self.query_one(OptionList)
        option_list.clear_options()
        for album in self.albums:
            option_list.add_option(album)


class SongList(Widget):
    """Lists album songs"""

    def __init__(self, song_data: dict) -> None:
        super().__init__()
        self.song_data = song_data
        self.current_songs: list = [] # these are songs in currently selected album

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search song name", type="text")
        yield LoadingIndicator()
        yield OptionList(
        )

    def on_mount(self) -> None:
        self.border_title = "Songs"

    def on_input_changed(self, event: Input.Changed) -> None:
        all_songs = self.current_songs
        search_function(self, event, all_songs)

    def update_song_list(self, album_name: str) -> None:
        """
        updates the SongList Ui when album is selected
        :param album_name: passed by event handler
        """
        songs = self.song_data.get(album_name, {}).get("songs", [])
        # clear and repopulate the OptionList
        option_list = self.query_one(OptionList)
        option_list.clear_options()
        self.current_songs = []
        for song in sorted(songs):
            self.current_songs.append(song)
            option_list.add_option(song)

class RightPane(Widget):
    pass
class LyricBox(Widget):
    """Display song lyrics"""

    current_index: reactive[int] = reactive(-1)
    current_song_path: reactive[str] = reactive("")
    def __init__(self):
        super().__init__()
        self.parsed_lyrics = []

    def watch_current_song_path(self, path: str) -> None:
        self.current_index = -1
        self.parsed_lyrics = []
        self.query_one(Markdown).update("")

        if path:
            self.load_lyrics(path)

    @work(exclusive=True, group="lyrics", exit_on_error=False)
    async def load_lyrics(self, path: str) -> None:
        try:
            cached_lyrics = await cache.find_cache(song_path=path)
            if cached_lyrics is not None:
                lyrics = cached_lyrics
            else:
                lyrics = (await extract_lyrics(path=path)).get("lyrics", [])

        except Exception:
            lyrics = []
        if path != self.current_song_path:
            return

        self.parsed_lyrics = lyrics

    def compose(self) -> ComposeResult:
        yield Markdown("")

    def on_mount(self) -> None:
        self.border_title = "Lyrics"
        # Poll every 1/30ms
        self.set_interval(1/30, self.update_lyrics)

    def update_lyrics(self) -> None:
        if not self.parsed_lyrics:
            return

        progress = get_progress()

        if progress[2]: # song ended
            return

        now = progress[0]  # how much the song has finished

        # Find the latest lyric whose time <= now
        idx = -1
        for i, (t, _) in enumerate(self.parsed_lyrics):
            if t <= now:
                idx = i
            else:
                break

        if idx != self.current_index:
            self.current_index = idx

    def watch_current_index(self, idx: int) -> None:
        """Called automatically when current_index changes"""
        if not self.parsed_lyrics or idx == -1:
            self.query_one(Markdown).update("")
            return

        lyrics = self.parsed_lyrics

        prev_text = f"*{lyrics[idx - 1][1]}*  " if idx > 0 else ""
        curr_text = f"**{lyrics[idx][1]}**  "
        next_text = f"*{lyrics[idx + 1][1]}*  " if idx < len(lyrics) - 1 else ""

        content = "\n".join(filter(bool, [prev_text, curr_text, next_text]))
        self.query_one(Markdown).update(content)

class LeftPane(Widget):
    pass
class QueueBox(VerticalScroll):
    """View the current song queue"""
    def compose(self) -> ComposeResult:
        yield RadioSet(disabled=True)

    def on_mount(self) -> None:
        self.border_title = "Queue"
        # self.query_one(RadioSet).mount(RadioButton("Hello"))

class TopBox(Widget):
    """Class containing album and song list"""

    song_over: reactive = reactive(False, init=False)
    def __init__(self, path: str) -> None:
        super().__init__()
        self.path = path
        self.current_album: str = ""
        self.queue_iterator: ReversibleIterator = None
        self.data_dict: dict = {}
        self.song_queue = []

    def compose(self) -> ComposeResult:
        with LeftPane():
            yield AlbumList(self.data_dict)
            yield QueueBox()
        with RightPane():
            yield SongList(self.data_dict)
            yield LyricBox()
        yield AlbumCover()

    def on_mount(self) -> None:
        # worker that loads library
        self.load_library_data()
        self.set_interval(1/30, self.song_status)

    @work(thread=True, exit_on_error=False)
    def load_library_data(self) -> None:
        """runs load_library() asynchronously, calls finish_loading() at end."""
        library = asyncio.run(load_library(self.path, cache=cache))
        self.app.call_from_thread(
            self.finish_loading,
            library
        )

    def finish_loading(self, library: dict) -> None:
        self.data_dict = library
        album_data = list(self.data_dict.values())
        if album_data:
            self.query_one(AlbumCover).path = album_data[0]["album_art"]
        else:
            self.query_one(AlbumCover).path = UNKNOWN_COVER_PATH
        album_list = self.query_one(AlbumList)
        song_list = self.query_one(SongList)
        album_list.query_one(LoadingIndicator).remove()
        song_list.query_one(LoadingIndicator).remove()
        album_list.data = library
        song_list.song_data = library

    ## HELPER FUNCTIONS ##

    def update_queue_box(self, song_name:str):
        qb = self.query_one(QueueBox).query_one(RadioSet)
        qb.remove_children()
        for song in self.song_queue:
            if song == song_name:
                qb.mount(RadioButton(f"{song}", value=True))
            else:
                qb.mount(RadioButton(f"{song}"))

    def song_manager(self, song_name: str) -> None:
        """ plays song, updates queue, loads lyrics"""
        # play song using player
        if not play_song(data_dict=self.data_dict, song_name=song_name):
            return
        # load song lyrics
        path = self.data_dict.get(self.current_album, {}).get("songs", {}).get(song_name, "")
        self.query_one(LyricBox).current_song_path = path
        # update queue box
        self.update_queue_box(song_name=song_name)

    def set_album_queue(self, song_name: str):
        album = self.data_dict.get(self.current_album)
        if not album:
            return
        songs = album.get("songs", {})
        if song_name not in songs:
            return
        song_list = sorted(songs.keys())
        idx = song_list.index(song_name)
        self.song_queue = song_list[idx:] + song_list[:idx]

## HELPER FUNCTIONS END ##


    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        # Make sure the event came from AlbumList, not SongList's OptionList
        if event.control in self.query_one(AlbumList).query(OptionList):
            album_name = str(event.option.prompt)
            self.current_album = album_name
            # Update SongList UI
            song_list_obj = self.query_one(SongList)
            song_list_obj.update_song_list(album_name)
            song_list_obj.query_one(Input).clear()
            # Update Album Cover Display
            self.query_one(AlbumCover).path = self.data_dict.get(album_name).get('album_art')

        # If SongList option, selected, play song
        if event.control in self.query_one(SongList).query(OptionList):
            song_name = str(event.option.prompt)
            # generating song queue
            self.set_album_queue(song_name=song_name)
            self.queue_iterator = ReversibleIterator(lst=self.song_queue)
            self.song_manager(song_name=next(self.queue_iterator))

    def song_status(self):
        """checks if song is over"""
        progress = get_progress()
        if progress[2] and progress[1] != 0.0:
            self.song_over = True

    def watch_song_over(self)->None:
        """watches song_over flag, if changed, plays next song in queue"""
        if not self.song_over:
            return

        self.song_over = False
        if self.queue_iterator is None:
            return

        self.song_manager(song_name=next(self.queue_iterator))
