from __future__ import annotations

import json
from pathlib import Path
from typing import Final

from pydantic import BaseModel, Field, field_validator

DEFAULT_RULES_PATH: Final[Path] = (
    Path(__file__).with_name("resources") / "default_rules.json"
)


class NotificationsConfig(BaseModel):
    enabled: bool = False


class DateSubfoldersConfig(BaseModel):
    enabled: bool = False
    folders: list[str] = Field(default_factory=lambda: ["Images"])

    @field_validator("folders")
    @classmethod
    def _normalize_folders(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for folder in value:
            folder = folder.strip()
            if folder:
                normalized.append(folder)
        return normalized


class DryRunConfig(BaseModel):
    enabled: bool = False


class AppConfig(BaseModel):
    rules: dict[str, str] = Field(default_factory=dict)
    exclude_dirs: list[str] = Field(default_factory=list)
    watch_dirs: list[str] = Field(default_factory=list)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
    date_subfolders: DateSubfoldersConfig = Field(
        default_factory=DateSubfoldersConfig
    )
    dry_run: DryRunConfig = Field(default_factory=DryRunConfig)

    @field_validator("rules")
    @classmethod
    def _normalize_rules(cls, value: dict[str, str]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for ext, folder in value.items():
            ext = ext.strip().lower()
            if not ext:
                continue
            if not ext.startswith("."):
                ext = f".{ext}"
            folder = folder.strip()
            if not folder:
                continue
            normalized[ext] = folder
        return normalized


def load_config(path: Path | None = None) -> AppConfig:
    config_path = path or DEFAULT_RULES_PATH
    if not config_path.exists():
        return AppConfig()
    data = json.loads(config_path.read_text(encoding="utf-8"))
    return AppConfig.model_validate(data)
