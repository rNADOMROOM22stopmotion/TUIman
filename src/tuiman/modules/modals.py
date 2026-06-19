from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, ListView, ListItem
from textual_autocomplete import PathAutoComplete
from tuiman.utils.caching import Cache

path_cacher = Cache()
PlaylistResult = dict[str, str]

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

class PlaylistScreen(ModalScreen[PlaylistResult | None]):
    """Save a song to playlist, create a new playlist..."""
    def __init__(self, playlists: list[str], song_name: str, song_path: str) -> None:
        super().__init__()
        self.playlists = playlists
        self.song_name = song_name
        self.song_path = song_path

    def compose(self) -> ComposeResult:
        with Vertical(id="playlist-container"):
            yield Label("Add song to playlist:", id="playlist-label")
            yield ListView(
                *[ListItem(Label(name)) for name in self.playlists],
                id="playlist-list",
                initial_index=0 if self.playlists else None,
            )
            with Horizontal(id="playlist-buttons"):
                yield Button("Add", variant="primary", id="pla-add")
                yield Button("Cancel", variant="primary", id="pla-can")
            yield Input(placeholder="Playlist name", id="playlist-name")
            yield Button("Create new playlist", variant="primary", id="pla-new")

    def _selected_playlist(self) -> str | None:
        playlist_list = self.query_one("#playlist-list", ListView)
        index = playlist_list.index
        if index is None or index < 0 or index >= len(self.playlists):
            return None
        return self.playlists[index]

    def _dismiss_playlist(self, playlist_name: str | None) -> None:
        if not playlist_name:
            self.query_one("#playlist-label", Label).update("Select or create a playlist:")
            return

        self.dismiss(
            {
                "playlist": playlist_name,
                "song_name": self.song_name,
                "song_path": self.song_path,
            }
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "pla-add":
            self._dismiss_playlist(self._selected_playlist())
        elif event.button.id == "pla-can":
            self.dismiss(None)
        elif event.button.id == "pla-new":
            playlist_name = self.query_one("#playlist-name", Input).value.strip()
            self._dismiss_playlist(playlist_name)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.control.id == "playlist-list":
            self._dismiss_playlist(self.playlists[event.index])
