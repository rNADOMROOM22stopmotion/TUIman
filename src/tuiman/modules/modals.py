from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, Grid
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Input, Label, ListView, ListItem
from textual_autocomplete import PathAutoComplete
from tuiman.utils.caching import Cache

path_cacher = Cache()

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

class PlaylistScreen(Screen):
    """Save a song to playlist, create a new playlist..."""
    def __init__(self, playlists: list[str]) -> None:
        super().__init__()
        self.playlists = playlists

    def compose(self) -> ComposeResult:
        with Vertical(id="playlist-container"):
            yield Label("Add song to playlist:")
            yield ListView(*[ListItem(Label(name), name=name) for name in self.playlists],
                id="playlist-list",)
            with Horizontal(id="playlist-buttons"):
                yield Button("Add", variant="primary", id="pla-add")
                yield Button("Cancel", variant="primary", id="pla-can")
            yield Input(placeholder="Playlist name", id="playlist-name")
            yield Button("Create new playlist", variant="primary", id="pla-new")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.app.exit()
        else:
            self.app.pop_screen()
