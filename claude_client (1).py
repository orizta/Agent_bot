"""
claude_client.py — Async wrapper around the Anthropic Messages API.
"""

from __future__ import annotations

import os
import logging
import anthropic

logger = logging.getLogger(__name__)

# Gunakan model terbaik — bisa di-override via env variable MODEL_NAME
DEFAULT_MODEL = os.environ.get("MODEL_NAME", "claude-opus-4-5")
MAX_TOKENS = 8096

SYSTEM_BASE = """Kamu adalah asisten AI yang sangat cerdas, membantu, dan berempati. \
Kamu berjalan di dalam sebuah Telegram Bot.

ATURAN UTAMA:
1. Selalu jawab dalam Bahasa Indonesia kecuali user menulis dalam bahasa lain — ikuti bahasa user.
2. PAHAMI maksud user secara mendalam sebelum menjawab. Jangan asal jawab.
3. Jawab dengan RELEVAN, spesifik, dan langsung ke inti pertanyaan.
4. Jika pertanyaan ambigu, tanya klarifikasi singkat sebelum menjawab panjang.
5. Gunakan format yang sesuai konteks:
   - Chat biasa → paragraf pendek, santai
   - Instruksi/langkah → nomor urut
   - Perbandingan → tabel atau poin
6. Jangan mulai jawaban dengan basa-basi panjang seperti "Tentu saja!", "Baik!", dll.
7. Jika ada instruksi dari <skills>, ikuti dengan sangat seksama — itu adalah keahlian khusus kamu.
8. Jika kamu tidak tahu sesuatu, katakan dengan jujur daripada mengarang jawaban.

KONTEKS: Kamu berjalan di Telegram, jadi hindari formatting Markdown kompleks \
kecuali benar-benar diperlukan."""


class ClaudeClient:
    def __init__(self) -> None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set!")
        self.client = anthropic.Anthropic(api_key=api_key)
        logger.info("Claude client initialized with model: %s", DEFAULT_MODEL)

    async def chat(
        self,
        user_message: str,
        skill_context: str = "",
        conversation_history: "list[dict] | None" = None,
    ) -> str:
        """Send a message to Claude and return the text response."""

        # Skill context diletakkan SEBELUM system prompt agar Claude prioritaskan
        if skill_context:
            system_prompt = f"{skill_context}\n\n{SYSTEM_BASE}"
        else:
            system_prompt = SYSTEM_BASE

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
