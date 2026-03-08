"""
claude_client.py — Async wrapper around the Anthropic Messages API.
"""

import os
import logging
import anthropic

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096

SYSTEM_BASE = (
    "Kamu adalah asisten AI yang helpful, cerdas, dan berbicara dalam Bahasa Indonesia "
    "kecuali user minta bahasa lain. Kamu berjalan di dalam Telegram Bot. "
    "Jawab dengan jelas, ringkas, dan terstruktur. "
    "Jika ada instruksi dari <skills>, ikuti dengan seksama."
)


class ClaudeClient:
    def __init__(self) -> None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set!")
        self.client = anthropic.Anthropic(api_key=api_key)

    async def chat(
        self,
        user_message: str,
        skill_context: str = "",
        conversation_history: list[dict] | None = None,
    ) -> str:
        """Send a message to Claude and return the text response."""

        system_prompt = SYSTEM_BASE
        if skill_context:
            system_prompt = f"{skill_context}\n\n{SYSTEM_BASE}"

        messages = list(conversation_history or [])
        messages.append({"role": "user", "content": user_message})

        try:
            response = self.client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                messages=messages,
            )
            return response.content[0].text
        except anthropic.APIError as e:
            logger.error("Anthropic API error: %s", e)
            raise
