
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, HorizontalGroup
from textual.widget import Widget
from textual.widgets import Header, Footer, Input, OptionList, Button, ProgressBar


class AlbumList(VerticalScroll):
    """Lists user albums"""
    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search album name", type="text")
        yield OptionList(
            "Aerilon","Aquaria","Canceron","Caprica","Gemenon","Leonis","Libran","Picon","Sagittaron","Scorpia","Tauron","Virgon",
        )

class SongList(VerticalScroll):
    """Lists album songs"""
    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search song name", type="text")
        yield OptionList(
            "Aerilon","Aquaria","Canceron","Caprica","Gemenon","Leonis","Libran","Picon","Sagittaron","Scorpia","Tauron","Virgon",
        )

class PlayControls(Widget):
    """Pause/resume, forward/backward controls"""
    def compose(self) -> ComposeResult:
        yield Button("<|")
        yield Button("||")
        yield Button("|>")

class Playback(Widget):
    """Displays playing bar"""
    def compose(self) -> ComposeResult:
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

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield TopBox()
        yield BottomBox()


if __name__ == "__main__":
    app = MusicApp()
    app.run()