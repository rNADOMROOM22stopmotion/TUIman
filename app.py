import os
import textwrap
from rich_pixels import Pixels
from textual.app import App, ComposeResult, RenderResult
from textual.color import Gradient
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Header, Footer, Input, OptionList, Button, ProgressBar, Label, Markdown
from utils.search import search_function, load_library
from utils.player import init_player, play_song, pause, resume, get_progress

init_player()

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
        album_cover = Pixels.from_image_path(self.path, resize=(20, 15))
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

    EXAMPLE_LYRIC = textwrap.dedent("""\
If they say why? (Why?) Why? (Why?)  
***• Tell 'em that it's human nature***  
Why? (Why?) Why? (Why?) Does he do me that way?
""")
    def compose(self) -> ComposeResult:
        yield Markdown(self.EXAMPLE_LYRIC)

    def on_mount(self) -> None:
        self.border_title = "Lyrics"


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
        path = self.query_one(Input).value.strip()
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