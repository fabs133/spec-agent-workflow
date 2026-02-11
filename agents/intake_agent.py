"""Intake Agent: loads text files from the input folder.

Step 1 in the text extraction workflow.
Reads .txt and .md files and stores them in context.data["loaded_files"].
"""

from __future__ import annotations

from pathlib import Path

from core.agents import BaseAgent, register_agent
from core.models import Context


@register_agent("intake_agent")
class IntakeAgent(BaseAgent):
    """Load text files from the input folder into context."""

    SUPPORTED_EXTENSIONS = {".txt", ".md"}

    async def execute(self, context: Context) -> Context:
        input_folder = Path(context.data["input_folder"])

        if not input_folder.exists():
            raise FileNotFoundError(f"Input folder does not exist: {input_folder}")

        loaded_files = []
        for file_path in sorted(input_folder.iterdir()):
            if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                content = file_path.read_text(encoding="utf-8")
                loaded_files.append({
                    "filename": file_path.name,
                    "content": content,
                    "size": len(content),
                })
                context.add_trace({
                    "type": "file_read",
                    "agent": self.name,
                    "file": file_path.name,
                    "size": len(content),
                })

        context.data["loaded_files"] = loaded_files
        return context
