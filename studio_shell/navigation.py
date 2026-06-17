from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

_PAGE_FILE_PATTERN = re.compile(r"^\d+_.+\.py$")

TITLE_OVERRIDES = {
    "1_Home": "Home",
    "2_Playground": "Playground",
    "3_UI_Cheatsheet": "UI 元件詞彙表",
}


def page_title_from_path(path: Path) -> str:
    stem = path.stem
    if stem in TITLE_OVERRIDES:
        return TITLE_OVERRIDES[stem]
    if "_" in stem:
        return stem.split("_", 1)[1].replace("_", " ")
    return stem.replace("_", " ")


def discover_file_pages(pages_dir: Path) -> list[Path]:
    if not pages_dir.is_dir():
        return []
    pages = [
        path
        for path in pages_dir.glob("*.py")
        if not path.name.startswith("_") and _PAGE_FILE_PATTERN.match(path.name)
    ]
    return sorted(pages, key=lambda path: path.stem)


def build_navigation_pages(
    *,
    shell_root: Path,
    overview_callable: Callable[[], None],
) -> dict[str, list[Any]]:
    import streamlit as st

    file_pages = [
        st.Page(str(path), title=page_title_from_path(path))
        for path in discover_file_pages(shell_root / "pages")
    ]
    return {
        "Studio": [
            st.Page(overview_callable, title="總覽", default=True),
            *file_pages,
        ]
    }
