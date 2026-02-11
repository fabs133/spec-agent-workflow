"""Sphinx configuration for Spec-Agent Workflow documentation."""

import os
import sys

# Add project root to path for autodoc
sys.path.insert(0, os.path.abspath(os.path.join("..", "..")))

project = "Spec-Agent Workflow"
copyright = "2026, VP School Project"
author = "VP School Project"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
]

templates_path = ["_templates"]
exclude_patterns = []

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

# Napoleon settings for Google-style docstrings
napoleon_google_docstrings = True
napoleon_numpy_docstrings = False

# Autodoc settings
autodoc_member_order = "bysource"
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}
