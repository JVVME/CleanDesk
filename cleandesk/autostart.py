"""Windows autostart registration via registry."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Final

APP_NAME: Final[str] = "CleanDesk"
REG_PATH: Final[str] = r"Software\Microsoft\Windows\CurrentVersion\Run"


def is_supported() -> bool:
    return sys.platform.startswith("win")


def get_startup_command() -> str:
    project_root = Path(__file__).resolve().parents[1]
    launcher = project_root / "cleandesk_launcher.py"
    python_exe = Path(sys.executable).resolve()
    return f"\"{python_exe}\" \"{launcher}\""


def is_enabled() -> bool:
    if not is_supported():
        return False
    try:
        import winreg
    except Exception:
        return False

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
            winreg.QueryValueEx(key, APP_NAME)
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def enable() -> None:
    if not is_supported():
        return
    import winreg

    command = get_startup_command()
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE
    ) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)


def disable() -> None:
    if not is_supported():
        return
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, APP_NAME)
    except FileNotFoundError:
        return
    except OSError:
        return
