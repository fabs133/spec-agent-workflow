"""Write Agent: writes extracted items to the output folder.

Step 3 in the text extraction workflow.
Produces:
- A JSON summary file with all extracted items
- Individual markdown files per item
"""

from __future__ import annotations

import json
from pathlib import Path

from core.agents import BaseAgent, register_agent
from core.models import Context


@register_agent("write_agent")
class WriteAgent(BaseAgent):
    """Write extracted items to the output folder."""

    async def execute(self, context: Context) -> Context:
        output_folder = Path(context.data["output_folder"])
        output_folder.mkdir(parents=True, exist_ok=True)

        items = context.data.get("extracted_items", [])
        written_files = []

        # Write JSON summary
        summary_path = output_folder / "extraction_results.json"
        summary_data = {
            "run_id": context.run_id,
            "total_items": len(items),
            "items": items,
        }
        summary_path.write_text(
            json.dumps(summary_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        written_files.append(str(summary_path))
        context.add_trace({
            "type": "file_write",
            "agent": self.name,
            "file": summary_path.name,
            "size": summary_path.stat().st_size,
        })

        # Write individual markdown files
        items_dir = output_folder / "items"
        items_dir.mkdir(exist_ok=True)

        for item in items:
            title = item.get("title", "untitled")
            safe_name = self._safe_filename(title)
            md_path = items_dir / f"{safe_name}.md"

            md_content = self._render_markdown(item)
            md_path.write_text(md_content, encoding="utf-8")
            written_files.append(str(md_path))

            context.add_trace({
                "type": "file_write",
                "agent": self.name,
                "file": md_path.name,
                "size": len(md_content),
            })

        context.data["written_files"] = written_files
        return context

    @staticmethod
    def _safe_filename(title: str) -> str:
        """Convert a title to a safe filename."""
        safe = title.lower().strip()
        safe = safe.replace(" ", "_")
        # Keep only alphanumeric, underscore, hyphen
        safe = "".join(c for c in safe if c.isalnum() or c in ("_", "-"))
        return safe[:80] or "untitled"

    @staticmethod
    def _render_markdown(item: dict) -> str:
        """Render an extracted item as a markdown note."""
        lines = [
            f"# {item.get('title', 'Untitled')}",
            "",
            f"**Type:** {item.get('item_type', 'note')}",
            f"**Confidence:** {item.get('confidence', 0.0):.0%}",
            f"**Source:** {item.get('source_file', 'unknown')}",
        ]
        tags = item.get("tags", [])
        if tags:
            lines.append(f"**Tags:** {', '.join(tags)}")

        lines.extend([
            "",
            "## Description",
            "",
            item.get("description", "No description."),
            "",
        ])
        return "\n".join(lines)
