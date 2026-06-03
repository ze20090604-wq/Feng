from __future__ import annotations

from pathlib import Path

import streamlit as st

SHELL_ROOT = Path(__file__).resolve().parent

st.set_page_config(page_title="Agent Studio", page_icon="*", layout="wide")


def overview() -> None:
    st.title("Agent Studio")
    st.caption("Open a page from the sidebar.")
    st.markdown(
        """
### Pages
- **Tetris**: a playable falling-block game built in Streamlit.
- **Home**, **Playground**, and **UI Cheatsheet**: workshop pages from the original studio.
"""
    )


pages = {
    "Studio": [
        st.Page(overview, title="Overview", default=True),
        st.Page(str(SHELL_ROOT / "pages" / "3_Tetris.py"), title="俄囉斯方塊"),
        st.Page(str(SHELL_ROOT / "pages" / "1_Home.py"), title="Home"),
        st.Page(str(SHELL_ROOT / "pages" / "2_Playground.py"), title="Playground"),
        st.Page(str(SHELL_ROOT / "pages" / "3_UI_Cheatsheet.py"), title="UI Cheatsheet"),
    ],
}

st.navigation(pages).run()
