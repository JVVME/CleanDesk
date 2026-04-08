from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
from typing import Iterable

from .config import load_config
from .engine import classify
from .logger import setup_logging
from .mover import FileMover
from .notifier import notify_move
from .tray import run_tray
from .watcher import (
    EVENT_CREATED,
    EVENT_MOVED,
    FileEvent,
    FileWatcher,
    get_default_watch_paths,
    is_noise_file,
)

PLACEHOLDER_TIMEOUT_SECONDS = 180.0
PLACEHOLDER_RETRY_SECONDS = 30.0
UNDO_SUPPRESS_SECONDS = 300.0


def _worker(
    event_queue: Queue[FileEvent],
    stop_event: threading.Event,
    pause_event: threading.Event,
    notifications_event: threading.Event,
    dry_run_event: threading.Event,
    logger: logging.Logger,
    rules: dict[str, str],
    exclude_dirs: Iterable[str],
    mover: FileMover,
    suppressed_paths: dict[Path, float],
    suppressed_lock: threading.Lock,
    date_subfolders_enabled: bool,
    date_subfolder_categories: set[str],
) -> None:
    normalized_excludes = _normalize_excludes(exclude_dirs)
    pending_placeholders: dict[Path, float] = {}
    last_pending_check = time.monotonic()
    pending_check_interval = 0.5
    while not stop_event.is_set():
        if pause_event.is_set():
            time.sleep(0.2)
            continue
        now = time.monotonic()
        if now - last_pending_check >= pending_check_interval:
            _process_pending_placeholders(
                pending_placeholders,
                rules,
                mover,
                logger,
                now,
                date_subfolders_enabled,
                date_subfolder_categories,
                dry_run_event,
            )
            _prune_suppressed(suppressed_paths, suppressed_lock, now)
            last_pending_check = now

        try:
            event = event_queue.get(timeout=0.2)
        except Empty:
            continue
        if event.event_type not in {EVENT_CREATED, EVENT_MOVED}:
            continue

        if event.event_type == EVENT_MOVED and event.src_path is not None:
            pending_placeholders.pop(event.src_path, None)

        if _is_suppressed(event.path, suppressed_paths, suppressed_lock, now):
            logger.info("Skip suppressed: %s", event.path)
            continue
        if event.src_path is not None and _is_suppressed(
            event.src_path, suppressed_paths, suppressed_lock, now
        ):
            logger.info("Skip suppressed: %s", event.src_path)
            continue

        if _looks_like_placeholder_name(event.path):
            pending_placeholders.setdefault(
                event.path, time.monotonic() + PLACEHOLDER_TIMEOUT_SECONDS
            )
            logger.info("Defer placeholder name: %s", event.path)
            continue

        if _is_excluded(event.path, normalized_excludes):
            logger.info("Skip excluded: %s", event.path)
            continue

        category = classify(event.path, rules)
        destination_dir = _build_destination_dir(
            event.path.parent,
            category,
            date_subfolders_enabled,
            date_subfolder_categories,
        )
        if dry_run_event.is_set():
            logger.info("Dry-run: %s -> %s", event.path, destination_dir)
            continue
        moved = mover.move(event.path, destination_dir)
        if moved is None:
            logger.warning("Move failed or skipped: %s", event.path)
            continue

        logger.info("Moved %s -> %s", event.path, moved)
        if notifications_event.is_set():
            notify_move(event.path, moved, logger=logger)


def main() -> int:
    logger = setup_logging()
    config = load_config()
    watch_paths = _resolve_watch_paths(config, logger)
    if not watch_paths:
        logger.error("No valid watch paths found.")
        return 1

    logger.info("Watching: %s", ", ".join(str(p) for p in watch_paths))
    event_queue: Queue[FileEvent] = Queue()
    stop_event = threading.Event()
    pause_event = threading.Event()
    notifications_event = threading.Event()
    dry_run_event = threading.Event()
    suppressed_paths: dict[Path, float] = {}
    suppressed_lock = threading.Lock()

    rules = config.rules
    mover = FileMover(logger=logger)
    if config.notifications.enabled:
        notifications_event.set()
    if config.dry_run.enabled:
        dry_run_event.set()
    date_subfolders_enabled = config.date_subfolders.enabled
    date_subfolder_categories = _normalize_category_set(
        config.date_subfolders.folders
    )

    watcher = FileWatcher(watch_paths, event_queue)
    watcher.start()

    worker_thread = threading.Thread(
        target=_worker,
        args=(
            event_queue,
            stop_event,
            pause_event,
            notifications_event,
            dry_run_event,
            logger,
            rules,
            config.exclude_dirs,
            mover,
            suppressed_paths,
            suppressed_lock,
            date_subfolders_enabled,
            date_subfolder_categories,
        ),
        daemon=True,
    )
    worker_thread.start()
    _scan_existing_files(watch_paths, event_queue, logger)

    try:
        run_tray(
            pause_event=pause_event,
            notifications_event=notifications_event,
            dry_run_event=dry_run_event,
            on_exit=lambda: _request_exit(stop_event, watcher, logger),
            on_undo=lambda: _handle_undo(
                mover, logger, suppressed_paths, suppressed_lock
            ),
            undo_count=mover.undo_count,
            logger=logger,
        )
    except KeyboardInterrupt:
        logger.info("Shutting down watcher...")
    finally:
        stop_event.set()
        watcher.stop()
        worker_thread.join(timeout=2)

    return 0


def _normalize_excludes(exclude_dirs: Iterable[str]) -> list[Path]:
    normalized: list[Path] = []
    for entry in exclude_dirs:
        entry = entry.strip()
        if not entry:
            continue
        normalized.append(Path(entry))
    return normalized


def _resolve_watch_paths(config, logger: logging.Logger) -> list[Path]:
    if config.watch_dirs:
        resolved = _normalize_watch_dirs(config.watch_dirs, logger)
        return resolved
    return get_default_watch_paths()


def _normalize_watch_dirs(
    watch_dirs: Iterable[str], logger: logging.Logger
) -> list[Path]:
    normalized: list[Path] = []
    seen: set[str] = set()
    for entry in watch_dirs:
        entry = entry.strip()
        if not entry:
            continue
        expanded = os.path.expandvars(entry)
        path = Path(expanded).expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        try:
            if not path.exists() or not path.is_dir():
                logger.warning("Watch dir missing: %s", path)
                continue
        except OSError:
            logger.warning("Watch dir inaccessible: %s", path)
            continue

        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        normalized.append(path)
    return normalized


def _normalize_category_set(categories: Iterable[str]) -> set[str]:
    normalized: set[str] = set()
    for entry in categories:
        entry = entry.strip()
        if not entry:
            continue
        normalized.add(entry.lower())
    return normalized


def _build_destination_dir(
    base_dir: Path,
    category: str,
    date_subfolders_enabled: bool,
    date_subfolder_categories: set[str],
) -> Path:
    destination_dir = base_dir / category
    if date_subfolders_enabled:
        if not date_subfolder_categories or category.lower() in date_subfolder_categories:
            destination_dir = destination_dir / datetime.now().strftime("%Y-%m")
    return destination_dir


def _is_excluded(path: Path, exclude_dirs: Iterable[Path]) -> bool:
    try:
        resolved = path.resolve()
    except FileNotFoundError:
        return False

    for entry in exclude_dirs:
        if entry.is_absolute():
            try:
                if resolved.is_relative_to(entry.resolve()):
                    return True
            except FileNotFoundError:
                continue
        else:
            if any(part.lower() == entry.name.lower() for part in resolved.parts):
                return True
    return False


def _handle_undo(
    mover: FileMover,
    logger: logging.Logger,
    suppressed_paths: dict[Path, float],
    suppressed_lock: threading.Lock,
) -> None:
    undone = mover.undo_last()
    if undone is None:
        logger.info("Undo unavailable")
    else:
        _suppress_path(undone, suppressed_paths, suppressed_lock)
        logger.info("Undo moved to %s", undone)


def _request_exit(
    stop_event: threading.Event, watcher: FileWatcher, logger: logging.Logger
) -> None:
    logger.info("Exit requested")
    stop_event.set()
    watcher.stop()


def _suppress_path(
    path: Path, suppressed_paths: dict[Path, float], suppressed_lock: threading.Lock
) -> None:
    try:
        resolved = path.resolve()
    except FileNotFoundError:
        return
    with suppressed_lock:
        suppressed_paths[resolved] = time.monotonic() + UNDO_SUPPRESS_SECONDS


def _is_suppressed(
    path: Path,
    suppressed_paths: dict[Path, float],
    suppressed_lock: threading.Lock,
    now: float,
) -> bool:
    try:
        resolved = path.resolve()
    except FileNotFoundError:
        return False
    with suppressed_lock:
        deadline = suppressed_paths.get(resolved)
        if deadline is None:
            return False
        if now >= deadline:
            suppressed_paths.pop(resolved, None)
            return False
        return True


def _prune_suppressed(
    suppressed_paths: dict[Path, float], suppressed_lock: threading.Lock, now: float
) -> None:
    with suppressed_lock:
        expired = [path for path, deadline in suppressed_paths.items() if now >= deadline]
        for path in expired:
            suppressed_paths.pop(path, None)


def _process_pending_placeholders(
    pending: dict[Path, float],
    rules: dict[str, str],
    mover: FileMover,
    logger: logging.Logger,
    now: float,
    date_subfolders_enabled: bool,
    date_subfolder_categories: set[str],
    dry_run_event: threading.Event,
) -> None:
    for path, deadline in list(pending.items()):
        if now < deadline:
            continue
        if not path.exists():
            pending.pop(path, None)
            continue
        if not _looks_like_placeholder_name(path):
            pending.pop(path, None)
            continue

        category = classify(path, rules)
        destination_dir = _build_destination_dir(
            path.parent,
            category,
            date_subfolders_enabled,
            date_subfolder_categories,
        )
        if dry_run_event.is_set():
            logger.info("Dry-run: %s -> %s", path, destination_dir)
            pending.pop(path, None)
            continue
        moved = mover.move(path, destination_dir)
        if moved is None:
            pending[path] = now + PLACEHOLDER_RETRY_SECONDS
            logger.info("Retry placeholder move later: %s", path)
            continue

        pending.pop(path, None)
        logger.info("Moved placeholder after timeout: %s -> %s", path, moved)


def _looks_like_placeholder_name(path: Path) -> bool:
    stem = path.stem.strip()
    if not stem:
        return True

    prefixes = [
        "新建",
        "未命名",
        "New",
        "Untitled",
    ]
    for prefix in prefixes:
        if stem.lower().startswith(prefix.lower()):
            return True
    return False


def _scan_existing_files(
    watch_paths: Iterable[Path], event_queue: Queue[FileEvent], logger: logging.Logger
) -> None:
    scanned = 0
    for watch_path in watch_paths:
        try:
            for child in watch_path.iterdir():
                if not child.is_file():
                    continue
                if is_noise_file(child):
                    continue
                event_queue.put(FileEvent(path=child, event_type=EVENT_CREATED))
                scanned += 1
        except OSError:
            logger.exception("Startup scan failed for %s", watch_path)
    if scanned:
        logger.info("Startup scan queued %s files", scanned)


if __name__ == "__main__":
    raise SystemExit(main())
