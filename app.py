from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, HorizontalGroup
from textual.widget import Widget
from textual.widgets import Header, Footer, Input, OptionList, Button, ProgressBar, Label
from utils.search import search_function


class AlbumList(VerticalScroll):
    """Lists user albums"""
    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search album name", type="text")
        yield OptionList(
            "Aerilon","Aquaria","Canceron","Caprica","Gemenon","Leonis","Libran","Picon","Sagittaron","Scorpia","Tauron","Virgon",
        )

    def on_input_changed(self, event: Input.Changed) -> None:
        all_albums = ["Aerilon", "Aquaria", "Canceron", "Caprica", "Gemenon", "Leonis", "Libran", "Picon", "Sagittaron",
                      "Scorpia", "Tauron", "Virgon", ]

        search_function(self, event, all_albums)

class SongList(VerticalScroll):
    """Lists album songs"""
    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search song name", type="text")
        yield OptionList(
            "Aerilon","Aquaria","Canceron","Caprica","Gemenon","Leonis","Libran","Picon","Sagittaron","Scorpia","Tauron","Virgon",
        )

    def on_input_changed(self, event: Input.Changed) -> None:
        all_songs = ["Aerilon", "Aquaria", "Canceron", "Caprica", "Gemenon", "Leonis", "Libran", "Picon", "Sagittaron",
                      "Scorpia", "Tauron", "Virgon", ]

        search_function(self, event, all_songs)

class PlayControls(Widget):
    """Pause/resume, forward/backward controls"""
    def compose(self) -> ComposeResult:
        yield Button("<|", variant="error", flat=True)
        yield Button("||", variant="success", flat=True)
        yield Button("|>", variant="error", flat=True)

class Playback(Widget):
    """Displays playing bar"""
    def compose(self) -> ComposeResult:
        yield Label("Playing: ", id="song-name")
        yield ProgressBar()


class TopBox(Widget):
    """Class containing album and song list"""
    def compose(self) -> ComposeResult:
        yield AlbumList()
        yield SongList()

class BottomBox(Widget):
    """Class containing play controls and playback bar"""
    def compose(self) -> ComposeResult:
        yield PlayControls()
        yield Playback()


class MusicApp(App):
    """main App class"""
    CSS_PATH = "music.tcss"
    BINDINGS = [
        ("n", "backward", "Backward"),
        ("space", "pause", "Pause"),
        ("m", "forward", "Forward"),

    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield TopBox()
        yield BottomBox()

    def action_pause(self) -> None:
        self.query_one(PlayControls).query("Button")[1].press()
    def action_forward(self) -> None:
        self.query_one(PlayControls).query("Button")[2].press()
    def action_backward(self) -> None:
        self.query_one(PlayControls).query("Button")[0].press()


if __name__ == "__main__":
    app = MusicApp()
    app.run()