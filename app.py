from pathlib import Path
from textual.app import App, ComposeResult
from textual.css.scalar import Scalar, Unit
from textual.screen import ModalScreen
from textual.widgets import Header, Footer, Input, Label, Button
from modules.bottom_box import BottomBox, PlayControls, QueueOptions
from modules.top_box import TopBox, AlbumList
from utils.player import init_player

init_player()

def logger(text)->None:
    with open("log.txt", "w") as f:
        f.write(f"{text}\n")


class DirectoryDialog(ModalScreen[str]):
    def compose(self) -> ComposeResult:
        yield Label(" Enter albums folder path:")
        yield Input(placeholder="/path/to/albums", id="modal_input")
        yield Button("Load", variant="primary")
        #TODO: add textual-autocomplete

    def on_button_pressed(self) -> None:
        raw = self.query_one(Input).value.strip().strip("'\"")
        path = Path(raw).expanduser().resolve()

        if path.is_dir():
            self.dismiss(str(path))
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
        ("q", "show_queue", "Show Queue"),
        ("alt+q", "shuffle_queue", "Shuffle Queue"),
    ]
    AUTO_FOCUS: str | None = "#modal_input"

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
    def action_show_queue(self) -> None:
        self.query_one(QueueOptions).query_one("#show-queue").press()
    def action_shuffle_queue(self) -> None:
        self.query_one(QueueOptions).query_one("#shuffle-queue").press()

    def on_mount(self) -> None:
        self.push_screen(DirectoryDialog(), self.on_directory_chosen)
        # pass

    def on_directory_chosen(self, path: str) -> None:
        self.library_path = path
        self.mount(TopBox(self.library_path), before=self.query_one(BottomBox))
        # set library here

    def on_button_pressed(self, event: Button.Pressed)->None:
        """handle button presses"""

        # show queue if button pressed
        if event.button.id == "show-queue":
            album_obj = self.query_one(AlbumList)
            # logger(f"{album_obj.styles.width.value}, {album_obj.styles.width.unit}, {album_obj.styles.width.percent_unit}")
            if album_obj.styles.width == Scalar(value=100.0, unit=Unit.WIDTH ,percent_unit=Unit.WIDTH):
                album_obj.styles.width = Scalar(value=40.0, unit=Unit.WIDTH ,percent_unit=Unit.WIDTH)
            else:
                album_obj.styles.width = Scalar(value=100.0, unit=Unit.WIDTH ,percent_unit=Unit.WIDTH)

if __name__ == "__main__":
    app = MusicApp()
    app.run()
