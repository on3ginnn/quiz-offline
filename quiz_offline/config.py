"""Portable-пути: данные рядом с exe (флешка), fallback для dev."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def get_executable_dir() -> Path:
    """Каталог exe (PyInstaller) или скрипта в dev."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _is_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def get_app_data_dir() -> Path:
    """data/ рядом с exe; иначе %LOCALAPPDATA%/AlmetQuizOffline."""
    portable = get_executable_dir() / "data"
    if _is_writable(portable):
        return portable
    fallback = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "AlmetQuizOffline"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def get_rooms_dir() -> Path:
    """Каталог копий JSON-пакетов."""
    rooms = get_executable_dir() / "rooms"
    rooms.mkdir(parents=True, exist_ok=True)
    return rooms


def get_database_path() -> Path:
    return get_app_data_dir() / "journal.sqlite"
