import random
from pathlib import Path
from platformdirs import PlatformDirs
from textual.app import App, ComposeResult
from textual.color import Color
from textual.containers import Horizontal, Vertical
from textual.css.scalar import Scalar, Unit
from textual.events import Click
from textual.screen import ModalScreen
from textual.widgets import Footer, Input, Label, Button, OptionList
from textual_autocomplete import PathAutoComplete
from textual_themes import register_all
from .modules.bottom_box import BottomBox, PlayControls, QueueOptions
from .modules.top_box import TopBox, AlbumList, SongList
from .utils.models import ReversibleIterator
from .utils.player import init_player
from .utils.caching import Cache


init_player()
path_cacher = Cache()
DIRS = PlatformDirs("tuiman_styles", "TUIman")

# default CSS shipped alongside app.py
BUNDLED_CSS = Path(__file__).parent / "tuiman.tcss"

def setup_config() -> Path:
    """Copy default CSS to user config dir if it doesn't exist, return its path."""
    css_config_path = DIRS.user_config_path / "tuiman.tcss"

    if not css_config_path.exists():
        DIRS.user_config_path.mkdir(parents=True, exist_ok=True)
        css_config_path.write_text(BUNDLED_CSS.read_text())

    return css_config_path

class DirectoryDialog(ModalScreen[str]):
    def compose(self) -> ComposeResult:
        with Vertical(id="dialog-container"):
            yield Label(" Enter albums folder path:")
            input_widget = Input(placeholder="/path/to/albums", id="modal_input")
            yield input_widget
            yield PathAutoComplete(target=input_widget, path=Path.cwd())
            with Horizontal(id="dialog-buttons"):
                yield Button("Load", variant="primary", id="dia-sub")
                yield Button("Load previous path", variant="primary", id="dia-prev")

    @staticmethod
    def resolve_album_path(raw: str) -> Path | None:
        candidate = Path(raw).expanduser().resolve(strict=False)

        if candidate.is_dir():
            return candidate

        if raw.startswith("/"):
            fallback = (Path.cwd() / raw.lstrip("/")).resolve(strict=False)
            if fallback.is_dir():
                return fallback

        return None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "dia-sub":
            raw = self.query_one(Input).value.strip().strip("'\"")
            if raw:
                path = self.resolve_album_path(raw)

                if path:
                    path_cacher.create_path_cache(path=str(path))
                    self.dismiss(str(path))
                else:
                    self.query_one(Label).update(" ❌ Invalid path, try again:")
        # load previous path
        elif event.button.id == "dia-prev":
            path = path_cacher.find_path_cache()
            if path:
                self.dismiss(str(path))


class Tuiman(App):
    """main App class"""
    def __init__(self):
        super().__init__()
        self.library_path: str = ""

        register_all(self)
        self.theme = "fifty-eight"

    CSS_PATH = str(setup_config())
    BINDINGS = [
        ("n", "backward", "Backward"),
        ("space", "pause", "Pause"),
        ("m", "forward", "Forward"),
        ("q", "show_queue", "Show Queue"),
        ("alt+q", "shuffle_queue", "Shuffle Queue"),
    ]
    AUTO_FOCUS: str | None = "#modal_input"

    def compose(self) -> ComposeResult:
        # yield Header()
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

        # show Queue if button pressed
        if event.button.id == "show-queue":
            album_obj = self.query_one(AlbumList)
            # logger(f"{album_obj.styles.width.value}, {album_obj.styles.width.unit}, {album_obj.styles.width.percent_unit}")
            if album_obj.styles.width == Scalar(value=100.0, unit=Unit.WIDTH ,percent_unit=Unit.WIDTH):
                album_obj.styles.width = Scalar(value=40.0, unit=Unit.WIDTH ,percent_unit=Unit.WIDTH)
            else:
                album_obj.styles.width = Scalar(value=100.0, unit=Unit.WIDTH ,percent_unit=Unit.WIDTH)

        if "playback" in event.button.classes:
            tb = self.query_one(TopBox)
            # forward backward logic
            queue = getattr(tb, "queue_iterator", None)

            if queue is not None:
                if event.button.id == "backward":
                    queue.pos = (queue.pos - 2) % len(queue.lst)
                tb.song_manager(song_name=next(queue))

        if "queue-btn" in event.button.classes:
            tb = self.query_one(TopBox)
            # shuffle logic, shuffles the queue, updates queue iterator and plays song using it.
            if tb.song_queue:
                if event.button.id == "shuffle-queue":
                    random.shuffle(tb.song_queue)
                    tb.queue_iterator = ReversibleIterator(lst=tb.song_queue)
                    tb.song_manager(song_name=next(tb.queue_iterator))

    def on_click(self, event: Click) -> None:
        """Focusing logic"""
        if not isinstance(event.widget, (Input, OptionList)):
            self.screen.set_focus(None)
            for option_list in self.query(OptionList):
                option_list.highlighted = None

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """This function ensures play button state stays updated when song is selected"""
        if event.control in self.query_one(SongList).query(OptionList):
            play_btn = self.query_one("#pause", Button)
            if play_btn.label == "▶":
                play_btn.label = "||"
                play_btn.styles.border = ("round", "deeppink")
                play_btn.styles.color = Color(255, 255, 255, 0.7)


def main():
    app = Tuiman()
    app.run()
