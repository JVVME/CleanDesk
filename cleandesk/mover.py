"""Safe file mover with undo buffer."""

from __future__ import annotations

import logging
import platform
import shutil
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final

DEFAULT_QUIET_PERIOD_SECONDS: Final[float] = 1.5
DEFAULT_CHECK_INTERVAL_SECONDS: Final[float] = 0.5
DEFAULT_AVAILABILITY_RETRIES: Final[int] = 3
DEFAULT_AVAILABILITY_DELAY_SECONDS: Final[float] = 0.5
DEFAULT_UNDO_LIMIT: Final[int] = 50


@dataclass(frozen=True)
class MoveRecord:
    src: Path
    dest: Path


def wait_for_stable_size(
    path: Path,
    *,
    quiet_period: float = DEFAULT_QUIET_PERIOD_SECONDS,
    check_interval: float = DEFAULT_CHECK_INTERVAL_SECONDS,
    timeout: float = 30.0,
) -> bool:
    """Wait until file size and mtime are stable for quiet_period seconds."""
    start = time.monotonic()
    last_size: int | None = None
    last_mtime: float | None = None
    last_change = time.monotonic()

    while True:
        try:
            stat = path.stat()
        except FileNotFoundError:
            return False
        size = stat.st_size
        mtime = stat.st_mtime

        if last_size is None or size != last_size or mtime != last_mtime:
            last_size = size
            last_mtime = mtime
            last_change = time.monotonic()

        if (time.monotonic() - last_change) >= quiet_period:
            return True

        if (time.monotonic() - start) >= timeout:
            return False

        time.sleep(check_interval)


def wait_for_file_available(
    path: Path,
    *,
    retries: int = DEFAULT_AVAILABILITY_RETRIES,
    delay: float = DEFAULT_AVAILABILITY_DELAY_SECONDS,
) -> bool:
    """Try opening file to detect locks; retry a few times."""
    if platform.system().lower().startswith("win"):
        return _wait_for_file_available_windows(path, retries=retries, delay=delay)

    for _ in range(max(1, retries)):
        try:
            with path.open("rb"):
                return True
        except PermissionError:
            time.sleep(delay)
        except FileNotFoundError:
            return False
    return False


def _wait_for_file_available_windows(
    path: Path, *, retries: int, delay: float
) -> bool:
    for _ in range(max(1, retries)):
        if _try_open_exclusive_windows(path):
            return True
        time.sleep(delay)
    return False


def _try_open_exclusive_windows(path: Path) -> bool:
    import ctypes
    from ctypes import wintypes

    GENERIC_READ = 0x80000000
    FILE_SHARE_NONE = 0x00000000
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_NORMAL = 0x00000080
    INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value

    create_file = ctypes.windll.kernel32.CreateFileW
    create_file.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create_file.restype = wintypes.HANDLE

    close_handle = ctypes.windll.kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL

    handle = create_file(
        str(path),
        GENERIC_READ,
        FILE_SHARE_NONE,
        None,
        OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL,
        None,
    )
    if handle == INVALID_HANDLE_VALUE:
        return False

    close_handle(handle)
    return True


def resolve_conflict(dest_path: Path) -> Path:
    """If dest exists, append date suffix; add counter if needed."""
    if not dest_path.exists():
        return dest_path

    date_str = datetime.now().strftime("%Y-%m-%d")
    stem = dest_path.stem
    suffix = dest_path.suffix
    candidate = dest_path.with_name(f"{stem} ({date_str}){suffix}")
    if not candidate.exists():
        return candidate

    counter = 2
    while True:
        candidate = dest_path.with_name(f"{stem} ({date_str} {counter}){suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


class FileMover:
    def __init__(
        self,
        *,
        undo_limit: int = DEFAULT_UNDO_LIMIT,
        quiet_period: float = DEFAULT_QUIET_PERIOD_SECONDS,
        check_interval: float = DEFAULT_CHECK_INTERVAL_SECONDS,
        availability_retries: int = DEFAULT_AVAILABILITY_RETRIES,
        availability_delay: float = DEFAULT_AVAILABILITY_DELAY_SECONDS,
        logger: logging.Logger | None = None,
    ) -> None:
        self._undo: deque[MoveRecord] = deque(maxlen=undo_limit)
        self._quiet_period = quiet_period
        self._check_interval = check_interval
        self._availability_retries = availability_retries
        self._availability_delay = availability_delay
        self._logger = logger or logging.getLogger("cleandesk")

    def move(self, src: Path, dest_dir: Path) -> Path | None:
        src = Path(src)
        dest_dir = Path(dest_dir)

        if not src.exists() or not src.is_file():
            self._logger.warning("Skip move: source missing %s", src)
            return None

        if not wait_for_stable_size(
            src,
            quiet_period=self._quiet_period,
            check_interval=self._check_interval,
        ):
            self._logger.warning("Skip move: file not stable %s", src)
            return None

        if not wait_for_file_available(
            src,
            retries=self._availability_retries,
            delay=self._availability_delay,
        ):
            self._logger.warning("Skip move: file locked %s", src)
            return None

        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = resolve_conflict(dest_dir / src.name)

        moved_path = Path(shutil.move(str(src), str(dest_path)))
        self._undo.append(MoveRecord(src=src, dest=moved_path))
        return moved_path

    def undo_last(self) -> Path | None:
        if not self._undo:
            return None

        record = self._undo.pop()
        if not record.dest.exists():
            self._logger.warning("Undo failed: dest missing %s", record.dest)
            return None

        target = record.src
        if target.exists():
            target = resolve_conflict(target)

        target.parent.mkdir(parents=True, exist_ok=True)
        return Path(shutil.move(str(record.dest), str(target)))

    def undo_count(self) -> int:
        return len(self._undo)
