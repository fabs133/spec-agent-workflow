"""Extract Agent: uses OpenAI GPT to extract structured items from loaded files.

Step 2 in the text extraction workflow.
Calls the LLM for each loaded file and merges results into
context.data["extracted_items"].
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List

from core.agents import BaseAgent, register_agent
from core.llm_client import chat_completion
from core.models import Context
from agents.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


@register_agent("extract_agent")
class ExtractAgent(BaseAgent):
    """Extract structured items from loaded files using an LLM."""

    async def execute(self, context: Context) -> Context:
        api_key = context.config.get("api_key", "")
        model = context.config.get("model", "gpt-4o")
        temperature = context.config.get("temperature", 0.3)

        loaded_files = context.data.get("loaded_files", [])
        all_items: List[Dict[str, Any]] = []

        for file_info in loaded_files:
            user_prompt = USER_PROMPT_TEMPLATE.format(
                filename=file_info["filename"],
                content=file_info["content"],
            )

            start_time = time.time()
            raw_content, tokens = chat_completion(
                api_key=api_key,
                model=model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            duration_ms = int((time.time() - start_time) * 1000)
            if not raw_content:
                raw_content = "[]"

            context.add_trace({
                "type": "llm_call",
                "agent": self.name,
                "model": model,
                "file": file_info["filename"],
                "tokens": tokens,
                "duration_ms": duration_ms,
                "prompt_preview": user_prompt[:200],
                "response_preview": raw_content[:500],
            })

            items = self._parse_items(raw_content, file_info["filename"])
            all_items.extend(items)

        context.data["extracted_items"] = all_items
        return context

    def _parse_items(
        self, raw: str, source_file: str
    ) -> List[Dict[str, Any]]:
        """Parse LLM response into a list of item dicts."""
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove first and last lines (fences)
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)

        try:
            items = json.loads(cleaned)
        except json.JSONDecodeError:
            return []

        if not isinstance(items, list):
            items = [items]

        # Enrich each item with source_file
        for item in items:
            item["source_file"] = source_file

        return items
