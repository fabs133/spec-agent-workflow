"""Page 5: Settings - API key, model defaults, folder paths."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from db.connection import get_connection, init_db
from db.repository import SettingsRepository

init_db()

st.header("Settings")

conn = get_connection()
repo = SettingsRepository()

# Load current settings
current = repo.get_all(conn)

st.subheader("API Configuration")

api_key = st.text_input(
    "OpenAI API Key",
    value=current.get("openai_api_key", ""),
    type="password",
)

model = st.selectbox(
    "Default Model",
    options=["gpt-4o", "gpt-4o-mini", "gpt-4.1-nano", "gpt-3.5-turbo"],
    index=["gpt-4o", "gpt-4o-mini", "gpt-4.1-nano", "gpt-3.5-turbo"].index(
        current.get("default_model", "gpt-4o")
    ),
)

st.subheader("Default Folders")

input_folder = st.text_input(
    "Default Input Folder",
    value=current.get("default_input_folder", str(PROJECT_ROOT / "data" / "input")),
)

output_folder = st.text_input(
    "Default Output Folder",
    value=current.get("default_output_folder", str(PROJECT_ROOT / "data" / "output")),
)

st.markdown("---")

if st.button("Save All Settings", type="primary"):
    repo.set(conn, "openai_api_key", api_key)
    repo.set(conn, "default_model", model)
    repo.set(conn, "default_input_folder", input_folder)
    repo.set(conn, "default_output_folder", output_folder)

    # Update session state
    st.session_state["api_key"] = api_key
    st.session_state["model"] = model
    st.session_state["input_folder"] = input_folder
    st.session_state["output_folder"] = output_folder

    st.success("Settings saved!")

st.markdown("---")
st.subheader("Current Settings (from DB)")
st.json(repo.get_all(conn))

conn.close()
