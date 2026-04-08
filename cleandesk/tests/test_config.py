from __future__ import annotations

import json
from pathlib import Path

from cleandesk.config import AppConfig, load_config


def test_config_normalizes_extensions() -> None:
    cfg = AppConfig.model_validate({"rules": {"PDF": "Documents", ".JPG": "Images"}})
    assert cfg.rules[".pdf"] == "Documents"
    assert cfg.rules[".jpg"] == "Images"


def test_load_config_from_path(tmp_path: Path) -> None:
    config_file = tmp_path / "rules.json"
    config_file.write_text(json.dumps({"rules": {".txt": "Documents"}}), encoding="utf-8")
    cfg = load_config(config_file)
    assert cfg.rules[".txt"] == "Documents"


def test_notifications_enabled_flag(tmp_path: Path) -> None:
    config_file = tmp_path / "rules.json"
    config_file.write_text(
        json.dumps({"notifications": {"enabled": False}}), encoding="utf-8"
    )
    cfg = load_config(config_file)
    assert cfg.notifications.enabled is False


def test_watch_dirs_field(tmp_path: Path) -> None:
    config_file = tmp_path / "rules.json"
    config_file.write_text(
        json.dumps({"watch_dirs": ["C:/Temp", "C:/Downloads"]}),
        encoding="utf-8",
    )
    cfg = load_config(config_file)
    assert cfg.watch_dirs == ["C:/Temp", "C:/Downloads"]


def test_date_subfolders_defaults() -> None:
    cfg = AppConfig()
    assert cfg.date_subfolders.enabled is False
    assert cfg.date_subfolders.folders


def test_dry_run_default() -> None:
    cfg = AppConfig()
    assert cfg.dry_run.enabled is False
