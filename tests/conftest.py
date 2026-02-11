"""Shared test fixtures."""

import sqlite3
from pathlib import Path

import pytest

from core.models import Context


@pytest.fixture
def sample_context() -> Context:
    """A Context with typical test data pre-filled."""
    return Context(
        data={
            "input_folder": "/tmp/test_input",
            "output_folder": "/tmp/test_output",
        },
        config={
            "api_key": "test-key-123",
            "model": "gpt-4o",
            "temperature": 0.3,
        },
    )


@pytest.fixture
def empty_context() -> Context:
    """A completely empty Context."""
    return Context()


@pytest.fixture
def context_after_intake() -> Context:
    """Context state after a successful intake step."""
    return Context(
        data={
            "input_folder": "/tmp/test_input",
            "output_folder": "/tmp/test_output",
            "loaded_files": [
                {"filename": "notes.txt", "content": "Some notes here.", "size": 16},
                {"filename": "ideas.md", "content": "# Ideas\n- Idea 1", "size": 20},
            ],
        },
        config={
            "api_key": "test-key-123",
            "model": "gpt-4o",
        },
    )


@pytest.fixture
def context_after_extract(context_after_intake) -> Context:
    """Context state after a successful extract step."""
    context_after_intake.data["extracted_items"] = [
        {
            "title": "Implement login page",
            "item_type": "task",
            "description": "Build the user login page with email/password.",
            "tags": ["frontend", "auth"],
            "source_file": "notes.txt",
            "confidence": 0.9,
        },
        {
            "title": "Add dark mode support",
            "item_type": "feature",
            "description": "Allow users to toggle dark mode.",
            "tags": ["ui", "design"],
            "source_file": "ideas.md",
            "confidence": 0.85,
        },
    ]
    return context_after_intake


@pytest.fixture
def context_after_write(context_after_extract) -> Context:
    """Context state after a successful write step."""
    context_after_extract.data["written_files"] = [
        "/tmp/test_output/extraction_results.json",
        "/tmp/test_output/items/implement_login_page.md",
        "/tmp/test_output/items/add_dark_mode_support.md",
    ]
    return context_after_extract


@pytest.fixture
def in_memory_db():
    """Fresh in-memory SQLite database with schema applied."""
    schema_path = Path(__file__).parent.parent / "db" / "schema.sql"
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if schema_path.exists():
        conn.executescript(schema_path.read_text())
    yield conn
    conn.close()
