import os
from rich_pixels import Pixels
from textual.app import App, ComposeResult, RenderResult
from textual.color import Gradient
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Header, Footer, Input, OptionList, Button, ProgressBar, Label, Markdown
from utils.lyrics import extract_lyrics
from utils.search import search_function, load_library
from utils.player import init_player, play_song, pause, resume, get_progress

init_player()

def logger(text)->None:
    with open("log.txt", "w") as f:
        f.write(f"{text}\n")

class AlbumList(VerticalScroll):
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


class AlbumCover(Widget):
    """using rich renderable to render ascii album cover"""
    path: reactive[str] = reactive("./media/unknown.png") #default album art
    def render(self) -> RenderResult:
        """load album art and display album cover"""
        album_cover = Pixels.from_image_path(self.path or "./media/unknown.png", resize=(20, 15))
        return album_cover


class SongList(VerticalScroll):
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
        updates the SongList Ui
        :param album_name: passed by event handler
        """
        songs = self.song_data.get(album_name, {}).get("songs", [])
        # clear and repopulate the OptionList
        option_list = self.query_one(OptionList)
        option_list.clear_options()
        self.current_songs = []
        for song in songs:
            self.current_songs.append(song)
            option_list.add_option(song)

class PlayControls(Widget):
    """Pause/resume, forward/backward controls"""
    def compose(self) -> ComposeResult:
        yield Button("⏮", variant="primary", flat=True)
        yield Button("||", id="pause", variant="success", flat=True)
        yield Button("⏭", variant="primary", flat=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """handles button state and pauses/ plays music"""
        if event.button.id == "pause":
            if event.button.label == "||":
                event.button.label = "▶"
                pause()
            else:
                event.button.label = "||"
                resume()


class Playback(Widget):
    """Displays playing bar"""
    def compose(self) -> ComposeResult:
        gradient = Gradient.from_colors("#881177","#aa3355","#cc6666","#ee9944","#eedd00","#99dd55","#44dd88","#22ccbb","#00bbcc","#0099cc","#3366bb","#663399",)

        yield Label("Playing: ", id="song-name")
        yield ProgressBar(total=100, show_eta=False, gradient=gradient)

    def on_mount(self) -> None:
        """Progress bar"""
        self.set_interval(1 / 30, self.make_progress)

    def make_progress(self) -> None:
        """Called automatically to advance the progress bar."""
        progress = 0
        time_stamps = get_progress()
        if not time_stamps[2]:
            try:
                progress = int((time_stamps[0]/time_stamps[1]) * 100)
            except ZeroDivisionError:
                progress = 0
        self.query_one(ProgressBar).update(progress=progress)

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
        """Re-parse lyrics whenever the song changes"""
        self.current_index = -1  # reset index for new song
        if path:
            self.parsed_lyrics = extract_lyrics(path=path)['lyrics']
        else:
            self.parsed_lyrics = []

    def compose(self) -> ComposeResult:
        yield Markdown("")

    def on_mount(self) -> None:
        self.border_title = "Lyrics"
        # Poll every 1/30ms
        self.set_interval(1/30, self.update_lyrics)

    def update_lyrics(self) -> None:
        if not self.parsed_lyrics:
            return

        now = get_progress()[0]  # how much the song has finished

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
        logger(content)
        self.query_one(Markdown).update(content)

class TopBox(Widget):
    """Class containing album and song list"""
    def __init__(self, path: str) -> None:
        super().__init__()
        self.data_dict = load_library(path)

    def compose(self) -> ComposeResult:
        yield AlbumList(self.data_dict)
        with RightPane():
            yield SongList(self.data_dict)
            yield LyricBox()
        yield AlbumCover()

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
            play_song(self.data_dict, song_name)
            # TODO: add song queue logic here
            # TODO: load song lyrics here
            path = next((songs[song_name] for album in self.data_dict.values() for songs in [album['songs']] if song_name in songs), "bruhhh")
            self.query_one(LyricBox).current_song_path = path
            logger(path)

    def on_mount(self)->None:
        album_data = list(self.data_dict.values())
        if album_data:
            self.query_one(AlbumCover).path = album_data[0]['album_art']

class BottomBox(Widget):
    """Class containing play controls and playback bar"""
    def compose(self) -> ComposeResult:
        yield PlayControls()
        yield Playback()

class DirectoryDialog(ModalScreen[str]):
    def compose(self) -> ComposeResult:
        yield Label(" Enter albums folder path:")
        yield Input(placeholder="/path/to/albums", id="modal_input")
        yield Button("Load", variant="primary")
        #TODO: add textual-autocomplete

    def on_button_pressed(self) -> None:
        path = os.path.abspath(os.path.expanduser(self.query_one(Input).value.strip().strip("'\"")))
        if os.path.isdir(path):
            self.dismiss(path)  # sends path back to the MusicApp
        else:
            self.query_one(Label).update(" ❌ Invalid path, try again:")


class MusicApp(App):
    """main App class"""
    def __init__(self):
        super().__init__()
        self.library_path: str = ""

    CSS_PATH = "music.tcss"
    BINDINGS = [
        ("n", "backward", "Backward"),
        ("space", "pause", "Pause"),
        ("m", "forward", "Forward"),

    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        # topbox
        yield BottomBox()

    def action_pause(self) -> None:
        self.query_one(PlayControls).query("Button")[1].press()
    def action_forward(self) -> None:
        self.query_one(PlayControls).query("Button")[2].press()
    def action_backward(self) -> None:
        self.query_one(PlayControls).query("Button")[0].press()

    def on_mount(self) -> None:
        self.push_screen(DirectoryDialog(), self.on_directory_chosen)
        # pass

    def on_directory_chosen(self, path: str) -> None:
        self.library_path = path
        self.mount(TopBox(self.library_path), before=self.query_one(BottomBox))
        # set library here


if __name__ == "__main__":
    app = MusicApp()
    app.run()
