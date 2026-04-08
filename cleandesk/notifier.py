"""User notifications (plyer)."""

from __future__ import annotations

import logging
from pathlib import Path


def notify_move(src: Path, dest: Path, *, logger: logging.Logger | None = None) -> None:
    logger = logger or logging.getLogger("cleandesk")
    try:
        from plyer import notification
    except Exception:
        logger.exception("Notifications unavailable (plyer import failed)")
        return

    try:
        notification.notify(
            title="CleanDesk",
            message=f"Moved to {dest.parent.name}: {src.name}",
            app_name="CleanDesk",
            timeout=4,
        )
    except Exception:
        logger.exception("Notification failed")
