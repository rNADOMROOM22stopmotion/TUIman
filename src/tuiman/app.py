import random
from pathlib import Path
from platformdirs import PlatformDirs
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.color import Color
from textual.css.query import NoMatches
from textual.css.scalar import Scalar, Unit
from textual.events import Click
from textual.widgets import Footer, Input, Button, OptionList
from .modules.bottom_box import BottomBox
from .modules.modals import DirectoryDialog, PlaylistScreen
from .modules.top_box import TopBox, AlbumList, SongList, LyricBox
from .utils.caching import Cache
from .utils.models import ReversibleIterator
from .utils.player import init_player
from tuiman.themes import register_all


init_player()
DIRS = PlatformDirs("tuiman_styles", "TUIman")

# default CSS shipped alongside app.py
BUNDLED_CSS = Path(__file__).parent / "tuiman.tcss"

def setup_config() -> Path:
    """Copy default CSS to user config dir if it doesn't exist, return its path."""
    css_config_path = DIRS.user_config_path / "tuiman.tcss"

    DIRS.user_config_path.mkdir(parents=True, exist_ok=True)
    css_config_path.write_text(BUNDLED_CSS.read_text())

    return css_config_path

class Tuiman(App):
    """main App class"""
    def __init__(self):
        super().__init__()
        self.library_path: str = ""
        self.cache = Cache()

        register_all(self)
        # self.theme = "fifty-eight"
        self.theme = "flughund"

    # CSS_PATH = str(setup_config())
    CSS_PATH = BUNDLED_CSS
    BINDINGS = [
        ("n", "backward", "Backward"),
        ("space", "pause", "Pause"),
        ("m", "forward", "Forward"),
        ("q", "show_queue", "Show Queue"),
        ("alt+q", "shuffle_queue", "Shuffle Queue"),
        ("s", "static_box", "Static Lyrics"),
        Binding("right", "playlist_box", "Add to Playlist"),
    ]
    AUTO_FOCUS: str | None = "#modal_input"

    def compose(self) -> ComposeResult:
        # yield Header()
        yield Footer(show_command_palette=False)
        # topbox
        yield BottomBox()

    def action_pause(self) -> None:
        self.query_one("#pause", Button).press()
    def action_forward(self) -> None:
        self.query_one("#forward", Button).press()
    def action_backward(self) -> None:
        self.query_one("#backward", Button).press()
    def action_show_queue(self) -> None:
        self.query_one("#show-queue", Button).press()
    def action_shuffle_queue(self) -> None:
        self.query_one("#shuffle-queue", Button).press()
    def action_static_box(self) -> None:
        top_box = self._top_box()
        if top_box is None:
            return

        lyric_box = top_box.query_one(LyricBox)
        lyric_box.mode = "synced" if lyric_box.mode == "plain" else "plain"
    def action_playlist_box(self)-> None:
        top_box = self._top_box()
        if top_box is None:
            return

        song = top_box.get_highlighted_song()
        if song is None:
            return

        self.push_screen(
            PlaylistScreen(
                self.cache.list_playlists(),
                song_name=song["name"],
                song_path=song["path"],
            ),
            self.on_playlist_chosen,
        )

    def _top_box(self) -> TopBox | None:
        try:
            return self.query_one(TopBox)
        except NoMatches:
            return None

    def on_playlist_chosen(self, result: dict[str, str] | None) -> None:
        if result is None:
            return

        added = self.cache.add_song_to_playlist(
            playlist_name=result["playlist"],
            song_name=result["song_name"],
            song_path=result["song_path"],
        )

        top_box = self._top_box()
        if top_box is None:
            return

        top_box.refresh_playlists()

        if added:
            self.notify(f"Added to {result['playlist']}", timeout=2)
        else:
            self.notify(f"Already in {result['playlist']}", severity="warning", timeout=2)

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
            top_box = self._top_box()
            if top_box is None:
                return

            album_obj = top_box.query_one(AlbumList)
            # logger(f"{album_obj.styles.width.value}, {album_obj.styles.width.unit}, {album_obj.styles.width.percent_unit}")
            if album_obj.styles.width == Scalar(value=100.0, unit=Unit.WIDTH ,percent_unit=Unit.WIDTH):
                album_obj.styles.width = Scalar(value=40.0, unit=Unit.WIDTH ,percent_unit=Unit.WIDTH)
            else:
                album_obj.styles.width = Scalar(value=100.0, unit=Unit.WIDTH ,percent_unit=Unit.WIDTH)

        if "playback" in event.button.classes:
            tb = self._top_box()
            if tb is None:
                return

            # forward backward logic
            queue = getattr(tb, "queue_iterator", None)

            if queue is not None:
                if event.button.id == "backward":
                    queue.pos = (queue.pos - 2) % len(queue.lst)
                tb.song_manager(song_name=next(queue))

        if "queue-btn" in event.button.classes:
            tb = self._top_box()
            if tb is None:
                return

            # shuffle logic, shuffles the queue, updates queue iterator and plays song using it.
            if tb.song_queue:
                if event.button.id == "shuffle-queue":
                    random.shuffle(tb.song_queue)
                    tb.queue_iterator = ReversibleIterator(lst=tb.song_queue)
                    tb.song_manager(song_name=next(tb.queue_iterator))

    def on_click(self, event: Click) -> None:
        """Blur focus and clear option highlights when clicking outside interactive widgets."""
        if not isinstance(event.widget, (Input, OptionList)):
            self.screen.set_focus(None)
            for option_list in self.query(OptionList):
                option_list.highlighted = None

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """This function ensures play button state stays updated when song is selected"""
        try:
            song_list = self.query_one(SongList)
        except NoMatches:
            return

        if event.control in song_list.query(OptionList):
            play_btn = self.query_one("#pause", Button)
            if play_btn.label == "▶":
                play_btn.label = "||"
                play_btn.styles.border = ("round", "deeppink")
                play_btn.styles.color = Color(255, 255, 255, 0.7)


def main():
    app = Tuiman()
    app.run()
