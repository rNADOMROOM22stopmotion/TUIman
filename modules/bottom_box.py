from textual.app import ComposeResult
from textual.color import Gradient, Color
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Label, ProgressBar
from utils.player import get_progress, get_current


class PlayControls(Widget):
    """Pause/resume, forward/backward controls"""
    def compose(self) -> ComposeResult:
        yield Button("⏮", id="backward", classes="playback", variant="primary", flat=True)
        yield Button("||", id="pause",variant="success", flat=True)
        yield Button("⏭", id="forward", classes="playback",variant="primary", flat=True)


class Playback(Widget):
    """Displays playing bar. Everything from updating the Playing: to the progressbar seems to be autonomous (depends
    on output give by player.py)"""
    current_song = reactive("-----")

    def compose(self) -> ComposeResult:
        gradient = Gradient.from_colors("#881177","#aa3355","#cc6666","#ee9944","#eedd00","#99dd55","#44dd88","#22ccbb","#00bbcc","#0099cc","#3366bb","#663399",)
        yield Label("Playing: -----", id="song-name")
        yield ProgressBar(total=100, show_eta=False, gradient=gradient)

    def on_mount(self) -> None:
        """Progress bar"""
        self.set_interval(1 /30, self.make_progress)
        self.set_interval(1/30 , self.sync_song)

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

    def sync_song(self)->None:
        c_song = get_current().get("song")
        if c_song != self.current_song:
            self.current_song = c_song

    def watch_current_song(self, song):
        self.query_one("#song-name", Label).update(f"Playing: {song}")

class QueueOptions(Widget):
    """show/ hide queue, shuffle options"""

    def compose(self) -> ComposeResult:
        yield Button("Queue", variant="primary", flat=True, classes="queue-btn", id="show-queue")
        yield Button("Shuffle", variant="primary", flat=True, classes="queue-btn" ,id="shuffle-queue")


    def on_mount(self) -> None:
        self.query_one("#show-queue").border_title = "Show"
        self.query_one("#shuffle-queue").border_subtitle = "queue"

class BottomBox(Widget):
    """Class containing play controls and playback bar"""
    def compose(self) -> ComposeResult:
        yield PlayControls()
        yield Playback()
        yield QueueOptions()