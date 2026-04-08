"""Rule engine for classification."""

from __future__ import annotations

from pathlib import Path
from typing import Final, Mapping

DEFAULT_FALLBACK_FOLDER: Final[str] = "Others"


def classify(
    path: Path,
    rules: Mapping[str, str],
    *,
    fallback: str = DEFAULT_FALLBACK_FOLDER,
) -> str:
    ext = path.suffix.lower()
    return rules.get(ext, fallback)
