import mutagen
import pygame
from typing import Optional

# module-level state
_current_album: Optional[str] = None
_current_song: Optional[str] = "-----"
_current_duration: float = 0.0
_paused: bool = False

def init_player() -> None:
    """Call once at app startup."""
    pygame.mixer.init()

def play_song(data_dict: dict, song_name: str) -> bool:
    """
    Play a song by name, searching across all albums.
    Returns True on success, False if song not found.
    """
    global _current_album, _current_duration, _current_song, _paused

    for album_name, data in data_dict.items():
        if song_name in data['songs']:
            path = data['songs'][song_name]
            pygame.mixer.music.stop()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            _current_album = album_name
            _current_song = song_name
            _paused = False

            # old code to cache duration at load time (mutagen was returning 0.0 for really short audios)
            audio = mutagen.File(path)
            _current_duration = audio.info.length if audio else 0.0

            # sound = pygame.mixer.Sound(path)
            # _current_duration = sound.get_length()

            return True

    return False

def pause() -> None:
    if pygame.mixer.music.get_busy() and not _paused:
        pygame.mixer.music.pause()
        globals()['_paused'] = True

def resume() -> None:
    global _paused
    if _paused:
        pygame.mixer.music.unpause()
        _paused = False

def stop() -> None:
    global _current_album, _current_song, _paused
    pygame.mixer.music.stop()
    _current_album = None
    _current_song = None
    _paused = False

def set_volume(level: float) -> None:
    """level: 0.0 to 1.0"""
    pygame.mixer.music.set_volume(max(0.0, min(1.0, level)))

def get_current() -> dict:
    return {
        "album": _current_album,
        "song": _current_song,
        "paused": _paused,
        "playing": pygame.mixer.music.get_busy()
    }

def get_progress() -> tuple[float, float, bool]:
    """Returns (elapsed_seconds, total_seconds, track_ended)."""
    if _current_song is None:
        return 0.0, 0.0, False

    track_ended = False
    raw_pos = pygame.mixer.music.get_pos()
    elapsed = max(0.0, raw_pos / 1000.0)

    if elapsed > _current_duration:
        track_ended = True

    return elapsed, _current_duration, track_ended