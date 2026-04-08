from pathlib import Path

from cleandesk.engine import DEFAULT_FALLBACK_FOLDER, classify


def test_classify_known_extension() -> None:
    rules = {".pdf": "Documents"}
    assert classify(Path("report.PDF"), rules) == "Documents"


def test_classify_unknown_extension() -> None:
    assert classify(Path("file.unknown"), {}) == DEFAULT_FALLBACK_FOLDER
