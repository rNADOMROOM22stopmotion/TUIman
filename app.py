import os
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Header, Footer, Input, OptionList, Button, ProgressBar, Label
from utils.search import search_function, load_library


class AlbumList(VerticalScroll):
    """Lists user albums"""
    def __init__(self, albums: list[str]) -> None:
        super().__init__()
        self.albums = albums

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search album name", type="text")
        yield OptionList(
            *self.albums
        )

    def on_input_changed(self, event: Input.Changed) -> None:
        search_function(self, event, self.albums)

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

    def on_input_changed(self, event: Input.Changed) -> None:
        all_songs = self.current_songs

        search_function(self, event, all_songs)

    def load_album(self, album_name: str) -> None:
        """
        updates the SongList Ui
        :param album_name: passed by event handler
        """
        songs = self.song_data.get(album_name, [])
        # your logic here — e.g. clear and repopulate the OptionList
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
        if event.button.id == "pause":
            event.button.label = "▶" if event.button.label == "||" else "||"

class Playback(Widget):
    """Displays playing bar"""
    def compose(self) -> ComposeResult:
        yield Label("Playing: ", id="song-name")
        yield ProgressBar()


class TopBox(Widget):
    """Class containing album and song list"""
    def __init__(self, path: str) -> None:
        super().__init__()
        self.data_dict = load_library(path)
        self.albums = [*self.data_dict.keys()]

    def compose(self) -> ComposeResult:
        yield AlbumList(self.albums)
        yield SongList(self.data_dict)

    def on_mount(self) -> None:
        self.query_one(SongList).border_title = "Songs"
        self.query_one(AlbumList).border_title = "Albums"

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        # Make sure the event came from AlbumList, not SongList's OptionList
        if event.control in self.query_one(AlbumList).query(OptionList):
            album_name = str(event.option.prompt)
            song_list_obj = self.query_one(SongList)
            song_list_obj.load_album(album_name)
            song_list_obj.query_one(Input).clear()

        if event.control in self.query_one(SongList).query(OptionList):
            song_name = str(event.option.prompt)
            # add song playing logic here

class BottomBox(Widget):
    """Class containing play controls and playback bar"""
    def compose(self) -> ComposeResult:
        yield PlayControls()
        yield Playback()

class DirectoryDialog(ModalScreen[str]):
    def compose(self) -> ComposeResult:
        yield Label("Enter albums folder path:")
        yield Input(placeholder="/path/to/albums")
        yield Button("Load", variant="primary")

    def on_button_pressed(self) -> None:
        path = self.query_one(Input).value.strip()
        if os.path.isdir(path):
            self.dismiss(path)  # sends path back to the MusicApp
        else:
            self.query_one(Label).update("❌ Invalid path, try again:")


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