from itertools import cycle

from httpcore import ReadTimeout
from rich_pixels import Pixels
from textual.app import ComposeResult, RenderResult
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Input, OptionList, RadioSet, RadioButton, Markdown
from utils.caching import LyricsCache
from utils.library_manager import search_function, load_library
from utils.lyrics import extract_lyrics
from utils.player import get_progress, play_song

lyrics_cache = LyricsCache()

class AlbumCover(Widget):
    """using rich renderable to render ascii album cover"""
    path: reactive[str] = reactive("./media/unknown.png") #default album art
    def render(self) -> RenderResult:
        """load album art and display album cover"""
        album_cover = Pixels.from_image_path(self.path or "./media/unknown.png", resize=(20, 15))
        return album_cover

class AlbumList(Widget):
    """Lists user albums"""

    def __init__(self, data: dict) -> None:
        super().__init__()
        self.data = data
        self.albums = [*data.keys()]

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search album name", type="text")
        yield OptionList(
            *self.albums
        )

    def on_mount(self) -> None:
        self.border_title = "Albums"

    def on_input_changed(self, event: Input.Changed) -> None:
        search_function(self, event, self.albums)


class SongList(Widget):
    """Lists album songs"""

    def __init__(self, song_data: dict) -> None:
        super().__init__()
        self.song_data = song_data
        self.current_songs: list = [] # these are songs in currently selected album

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search song name", type="text")
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

    async def watch_current_song_path(self, path: str) -> None:
        """Re-parse lyrics whenever the song changes"""
        self.current_index = -1  # reset index for new song
        if path:
            # Check .cache for lyrics, if found, skip extract_lyrics
            cached_lyrics = await lyrics_cache.find_cache(song_path=self.current_song_path)
            if cached_lyrics:
                self.parsed_lyrics = cached_lyrics
            else:
                try:
                    self.parsed_lyrics = (await extract_lyrics(path=path))['lyrics']
                except ReadTimeout:
                    self.parsed_lyrics = []
        else:
            self.parsed_lyrics = []

    def compose(self) -> ComposeResult:
        yield Markdown("")

    def on_mount(self) -> None:
        self.border_title = "Lyrics"
        # Poll every 1/30ms
        self.set_interval(1/60, self.update_lyrics)

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
        with RadioSet(disabled=True):
            yield RadioButton("Battlestar Galactica")
            yield RadioButton("Dune 1984")
            yield RadioButton("Serenity", value=True)
            yield RadioButton("Star Trek: The Motion Picture")
            yield RadioButton("Star Trek: The Motion Picture")
            yield RadioButton("Star Trek: The Motion Picture")


    def on_mount(self) -> None:
        self.border_title = "Queue"
        # self.query_one(RadioSet).mount(RadioButton("Hello"))

class TopBox(Widget):
    """Class containing album and song list"""

    song_over: reactive = reactive(False, init=False)
    def __init__(self, path: str) -> None:
        super().__init__()
        self.queue_gen = None
        self.data_dict = load_library(path)
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
        album_data = list(self.data_dict.values())
        if album_data:
            self.query_one(AlbumCover).path = album_data[0]['album_art']
        self.set_interval(1/60, self.song_status)

## HELPER FUNCTIONS ##

    def song_manager(self, song_name: str) -> None:
        """ plays song, updates queue, loads lyrics"""
        # play song using player
        play_song(data_dict=self.data_dict, song_name=song_name)
        # load song lyrics
        path = next(
            (songs[song_name] for album in self.data_dict.values() for songs in [album['songs']] if song_name in songs), "")
        self.query_one(LyricBox).current_song_path = path

    def set_album_queue(self, song_name: str):
        for album in self.data_dict.values():
            songs = album.get('songs', {})
            if song_name in songs:
                song_list = sorted(songs.keys())
                idx = song_list.index(song_name)
                self.song_queue = song_list[idx:] + song_list[:idx]
                return

    @staticmethod
    def cycle_queue(lst):
        for value in cycle(lst):
            yield value

    @staticmethod
    def logger(text) -> None:
        with open("log.txt", "w") as f:
            f.write(f"{text}\n")
## HELPER FUNCTIONS END ##


    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        # Make sure the event came from AlbumList, not SongList's OptionList
        if event.control in self.query_one(AlbumList).query(OptionList):
            album_name = str(event.option.prompt)
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
            self.queue_gen = self.cycle_queue(self.song_queue)
            self.logger(self.song_queue)
            self.song_manager(song_name=next(self.queue_gen))

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
        if self.queue_gen is None:
            return

        self.song_manager(song_name=next(self.queue_gen))

