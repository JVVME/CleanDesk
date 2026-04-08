"""File system watcher (watchdog wrapper)."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from queue import Queue
from typing import Iterable, Final

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

EVENT_CREATED: Final[str] = "created"
EVENT_MODIFIED: Final[str] = "modified"
EVENT_MOVED: Final[str] = "moved"

DEFAULT_DEBOUNCE_SECONDS: Final[float] = 0.5
DEFAULT_IGNORED_SUFFIXES: Final[set[str]] = {
    ".tmp",
    ".part",
    ".crdownload",
    ".download",
    ".temp",
}
DEFAULT_IGNORED_NAMES: Final[set[str]] = {"Thumbs.db", "desktop.ini"}


def is_noise_file(path: Path) -> bool:
    name = path.name
    if name in DEFAULT_IGNORED_NAMES:
        return True
    if name.startswith("~$"):
        return True
    if path.suffix.lower() in DEFAULT_IGNORED_SUFFIXES:
        return True
    return False


@dataclass(frozen=True)
class FileEvent:
    path: Path
    event_type: str
    src_path: Path | None = None


def get_default_watch_paths() -> list[Path]:
    """Return default Desktop + Downloads paths that actually exist."""
    home = Path.home()
    candidates = [home / "Desktop", home / "Downloads"]
    return [path for path in candidates if path.exists() and path.is_dir()]


class _WatchdogHandler(FileSystemEventHandler):
    def __init__(
        self,
        event_queue: Queue[FileEvent],
        *,
        debounce_seconds: float = DEFAULT_DEBOUNCE_SECONDS,
        ignored_suffixes: set[str] | None = None,
        ignored_names: set[str] | None = None,
    ) -> None:
        super().__init__()
        self._queue = event_queue
        self._debounce_seconds = debounce_seconds
        self._ignored_suffixes = ignored_suffixes or set(DEFAULT_IGNORED_SUFFIXES)
        self._ignored_names = ignored_names or set(DEFAULT_IGNORED_NAMES)
        self._last_seen: dict[tuple[str, Path], float] = {}
        self._lock = threading.Lock()

    def on_created(self, event: FileSystemEvent) -> None:
        self._handle_event(event, EVENT_CREATED)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._handle_event(event, EVENT_MODIFIED)

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        dest_path = Path(getattr(event, "dest_path", ""))
        if not dest_path:
            return
        if self._is_noise_file(dest_path):
            return
        self._enqueue_event(dest_path, EVENT_MOVED, src_path=Path(event.src_path))

    def _handle_event(self, event: FileSystemEvent, event_type: str) -> None:
        if event.is_directory:
            return

        path = Path(event.src_path)
        if self._is_noise_file(path):
            return

        self._enqueue_event(path, event_type)

    def _enqueue_event(
        self, path: Path, event_type: str, *, src_path: Path | None = None
    ) -> None:
        now = time.monotonic()
        key = (event_type, path)
        with self._lock:
            last = self._last_seen.get(key)
            if last is not None and (now - last) < self._debounce_seconds:
                return
            self._last_seen[key] = now

        self._queue.put(FileEvent(path=path, event_type=event_type, src_path=src_path))

    def _is_noise_file(self, path: Path) -> bool:
        name = path.name
        if name in self._ignored_names:
            return True
        if name.startswith("~$"):
            return True
        if path.suffix.lower() in self._ignored_suffixes:
            return True
        return False


class FileWatcher:
    def __init__(
        self,
        paths: Iterable[Path],
        event_queue: Queue[FileEvent],
        *,
        debounce_seconds: float = DEFAULT_DEBOUNCE_SECONDS,
    ) -> None:
        self._paths = [Path(path) for path in paths]
        self._handler = _WatchdogHandler(
            event_queue, debounce_seconds=debounce_seconds
        )
        self._observer = Observer()
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        for path in self._paths:
            if not path.exists():
                continue
            self._observer.schedule(self._handler, str(path), recursive=False)
        self._observer.start()
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        self._observer.stop()
        self._observer.join(timeout=5)
        self._started = False
