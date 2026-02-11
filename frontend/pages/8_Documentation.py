"""Page 8: Sphinx Documentation Viewer.

Embeds the auto-generated Sphinx HTML documentation directly
into the Streamlit app. Extracts the main content from Sphinx HTML
and wraps it with inlined CSS for proper rendering.
"""

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import streamlit.components.v1 as components

st.header("Documentation")
st.markdown(
    "Auto-generated API documentation from Python docstrings, "
    "powered by [Sphinx](https://www.sphinx-doc.org/)."
)

DOCS_BUILD = PROJECT_ROOT / "docs" / "build" / "html"

# Available documentation pages
DOC_PAGES = {
    "Architecture": "architecture.html",
    "Getting Started": "getting_started.html",
    "API: Core Engine": "api/core.html",
    "API: Agents": "api/agents.html",
    "API: Database": "api/db.html",
}

if not DOCS_BUILD.exists() or not (DOCS_BUILD / "index.html").exists():
    st.warning(
        "Sphinx documentation has not been built yet. "
        "Run the following command to build it:"
    )
    st.code("cd docs && sphinx-build -b html source build/html", language="bash")
    st.stop()

# Page selector
selected = st.selectbox(
    "Documentation Section",
    options=list(DOC_PAGES.keys()),
    index=0,
)

html_file = DOCS_BUILD / DOC_PAGES[selected]

if not html_file.exists():
    st.error(f"File not found: {html_file}")
    st.stop()


def _collect_css(base_dir: Path) -> str:
    """Read and concatenate all Sphinx CSS files into a single string."""
    css_files = [
        DOCS_BUILD / "_static" / "pygments.css",
        DOCS_BUILD / "_static" / "css" / "theme.css",
    ]
    parts = []
    for css_path in css_files:
        if css_path.exists():
            parts.append(css_path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


def _extract_body_content(html: str) -> str:
    """Extract the main documentation content from Sphinx HTML.

    Extracts the <div class="rst-content"> section which contains the
    article body, breadcrumbs, and footer (breadcrumbs/footer are hidden
    via CSS overrides).
    """
    # Extract <div class="rst-content">...</div> (greedy, captures all nested content)
    match = re.search(
        r'(<div\s+class="rst-content">)(.*?)(</div>\s*</div>\s*</section>)',
        html,
        flags=re.DOTALL,
    )
    if match:
        return match.group(1) + match.group(2) + "</div>"

    # Fallback: return body content
    match = re.search(r'<body[^>]*>(.*?)</body>', html, flags=re.DOTALL)
    if match:
        return match.group(1)

    return html


# Collect CSS
all_css = _collect_css(html_file.parent)

# Read the HTML and extract content
html_content = html_file.read_text(encoding="utf-8")
body_content = _extract_body_content(html_content)

# Build a clean, self-contained HTML document
rendered_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{all_css}
</style>
<style>
/* Override RTD theme layout for embedded view */
body {{
    background: #fcfcfc !important;
    font-family: "Lato", "proxima-nova", "Helvetica Neue", Arial, sans-serif;
    color: #404040;
    margin: 0;
    padding: 1em;
}}
.wy-nav-content {{
    max-width: 100% !important;
    padding: 0 !important;
    margin: 0 !important;
}}
/* Hide breadcrumb navigation (links don't work inside iframe) */
div[role="navigation"] {{ display: none !important; }}
.wy-breadcrumbs {{ display: none !important; }}
/* Hide "Next/Previous" footer nav */
.rst-footer-buttons {{ display: none !important; }}
/* Hide "View page source" link */
.wy-breadcrumbs-aside {{ display: none !important; }}
/* Hide copyright footer to save space */
div[role="contentinfo"] {{ display: none !important; }}
footer {{ display: none !important; }}
/* Ensure code blocks render properly */
.highlight pre {{
    background: #272822;
    color: #f8f8f2;
    padding: 12px;
    border-radius: 4px;
    overflow-x: auto;
    font-size: 13px;
}}
/* Style tables */
table.docutils {{
    border-collapse: collapse;
    width: 100%;
}}
table.docutils td, table.docutils th {{
    border: 1px solid #e1e4e5;
    padding: 8px 12px;
}}
/* Style API class/function entries */
dl.py dt {{
    background: #e7f2fa;
    padding: 6px 10px;
    border-top: 3px solid #6ab0de;
    font-family: "SFMono-Regular", Consolas, monospace;
    font-size: 0.9em;
}}
/* Style section headers */
h1 {{ font-size: 1.8em; border-bottom: 1px solid #e1e4e5; padding-bottom: 0.3em; }}
h2 {{ font-size: 1.4em; }}
h3 {{ font-size: 1.2em; }}
/* Style links */
a {{ color: #2980b9; text-decoration: none; }}
a:hover {{ color: #3091d1; }}
/* Hide headerlink anchors */
a.headerlink {{ display: none; }}
/* Admonitions */
.admonition {{ padding: 12px; margin: 12px 0; border-left: 4px solid #6ab0de; background: #e7f2fa; }}
.admonition-title {{ font-weight: bold; }}
/* List tables */
table.docutils.align-default {{ margin: 0; }}
/* Cross-page links styled as plain text (not clickable) */
a.cross-page {{ color: #404040; cursor: default; pointer-events: none; }}
/* Tooltip shown when hovering disabled links */
.link-tooltip {{
    display: none;
    position: fixed;
    background: #333;
    color: #fff;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 12px;
    z-index: 9999;
    white-space: nowrap;
}}
</style>
</head>
<body>
<div class="rst-content">
{body_content}
</div>
<div class="link-tooltip" id="linkTooltip">Use the dropdown above to navigate</div>
<script>
// Intercept clicks on links inside the documentation
document.addEventListener('click', function(e) {{
    var link = e.target.closest('a');
    if (!link) return;
    var href = link.getAttribute('href');
    if (!href) return;
    // Allow same-page anchor links (scroll within content)
    if (href.startsWith('#')) return;
    // Block all other navigation (cross-page .html links, external links)
    e.preventDefault();
    e.stopPropagation();
}});
// On load: mark cross-page links visually and disable them
document.addEventListener('DOMContentLoaded', function() {{
    document.querySelectorAll('a[href]').forEach(function(link) {{
        var href = link.getAttribute('href');
        if (href && !href.startsWith('#')) {{
            link.classList.add('cross-page');
            link.removeAttribute('href');
        }}
    }});
}});
</script>
</body>
</html>"""

# Render the HTML
components.html(rendered_html, height=800, scrolling=True)

st.markdown("---")
st.caption(
    "Documentation is generated from Python docstrings using Sphinx autodoc. "
    "To rebuild after code changes: `cd docs && sphinx-build -b html source build/html`"
)
