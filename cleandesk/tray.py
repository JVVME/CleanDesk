"""System tray integration (pystray)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

import pystray
from PIL import Image

from . import autostart

ICON_PATH = Path(__file__).with_name("resources") / "icon.png"


def run_tray(
    *,
    pause_event,
    notifications_event,
    dry_run_event,
    on_exit: Callable[[], None],
    on_undo: Callable[[], None],
    undo_count: Callable[[], int],
    logger: logging.Logger | None = None,
) -> None:
    logger = logger or logging.getLogger("cleandesk")
    icon = pystray.Icon("CleanDesk", _load_icon(), title="CleanDesk")

    def toggle_pause(_icon, _item) -> None:
        if pause_event.is_set():
            pause_event.clear()
            logger.info("Resumed")
        else:
            pause_event.set()
            logger.info("Paused")
        icon.update_menu()

    def undo_action(_icon, _item) -> None:
        try:
            on_undo()
        except Exception:
            logger.exception("Undo failed")
        icon.update_menu()

    def toggle_notifications(_icon, _item) -> None:
        if notifications_event.is_set():
            notifications_event.clear()
            logger.info("Notifications disabled")
        else:
            notifications_event.set()
            logger.info("Notifications enabled")
        icon.update_menu()

    def toggle_autostart(_icon, _item) -> None:
        try:
            if autostart.is_enabled():
                autostart.disable()
                logger.info("Autostart disabled")
            else:
                autostart.enable()
                logger.info("Autostart enabled")
        except Exception:
            logger.exception("Autostart toggle failed")
        icon.update_menu()

    def toggle_dry_run(_icon, _item) -> None:
        if dry_run_event.is_set():
            dry_run_event.clear()
            logger.info("Dry-run disabled")
        else:
            dry_run_event.set()
            logger.info("Dry-run enabled")
        icon.update_menu()

    def exit_action(_icon, _item) -> None:
        on_exit()
        icon.stop()

    def pause_text(_item) -> str:
        return "Resume" if pause_event.is_set() else "Pause"

    def pause_checked(_item) -> bool:
        return pause_event.is_set()

    def notifications_checked(_item) -> bool:
        return notifications_event.is_set()

    def autostart_checked(_item) -> bool:
        return autostart.is_enabled()

    def dry_run_checked(_item) -> bool:
        return dry_run_event.is_set()

    def autostart_enabled(_item) -> bool:
        return autostart.is_supported()

    def undo_text(_item) -> str:
        count = undo_count()
        return f"Undo Last Move ({count})" if count else "Undo Last Move"

    icon.menu = pystray.Menu(
        pystray.MenuItem(pause_text, toggle_pause, checked=pause_checked),
        pystray.MenuItem(undo_text, undo_action),
        pystray.MenuItem(
            "Notifications", toggle_notifications, checked=notifications_checked
        ),
        pystray.MenuItem("Dry Run", toggle_dry_run, checked=dry_run_checked),
        pystray.MenuItem(
            "Start with Windows",
            toggle_autostart,
            checked=autostart_checked,
            enabled=autostart_enabled,
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", exit_action),
    )

    logger.info("Tray started")
    icon.run()


def _load_icon() -> Image.Image:
    try:
        image = Image.open(ICON_PATH).convert("RGBA")
        if image.width < 16 or image.height < 16:
            image = image.resize((64, 64), Image.LANCZOS)
        return image
    except Exception:
        return Image.new("RGBA", (64, 64), (0, 0, 0, 0))
