"""
skill_loader.py — Loads and manages SKILL.md files from the skills/ directory.
Compatible with the Agent Skills open standard (https://agentskills.io)
"""

import os
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


# Keyword → skill name mapping for auto-detection
SKILL_KEYWORDS: dict[str, list[str]] = {
    "docx": [
        "word", "dokumen", "document", "docx", ".docx", "laporan word",
        "surat", "letter", "memo", "template word",
    ],
    "pptx": [
        "presentasi", "presentation", "slide", "pptx", ".pptx",
        "powerpoint", "deck", "pitch deck",
    ],
    "xlsx": [
        "excel", "spreadsheet", "xlsx", ".xlsx", "tabel", "table",
        "data excel", "csv", "kalkulasi",
    ],
    "pdf": [
        "pdf", ".pdf", "portable document", "cetak", "print",
        "gabung pdf", "merge pdf", "split pdf",
    ],
    "frontend-design": [
        "website", "web", "html", "css", "react", "komponen", "component",
        "ui", "ux", "landing page", "desain web",
    ],
}


class SkillLoader:
    """Discovers, loads, and serves SKILL.md content."""

    def __init__(self, skills_dir: str = "skills/") -> None:
        self.skills_dir = Path(skills_dir)
        self._skills: dict[str, dict] = {}  # name → {content, description, size}

    # ── Public API ────────────────────────────────────────────────────────────

    def load_all(self) -> None:
        """Load every SKILL.md found under skills_dir."""
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        loaded = []
        for path in sorted(self.skills_dir.rglob("SKILL.md")):
            name = self._name_from_path(path)
            self._load_skill(name, path)
            loaded.append(name)
        logger.info("Loaded %d skill(s): %s", len(loaded), loaded)

    def list_skills(self) -> list[str]:
        return sorted(self._skills.keys())

    def get_skill_info(self, name: str) -> dict | None:
        return self._skills.get(name.lower())

    def detect_relevant_skills(self, text: str) -> list[str]:
        """Return skill names whose keywords appear in the user text."""
        text_lower = text.lower()
        matched = []
        for skill_name, keywords in SKILL_KEYWORDS.items():
            if skill_name in self._skills and any(kw in text_lower for kw in keywords):
                matched.append(skill_name)
        return matched

    def build_skill_context(self, skill_names: list[str]) -> str:
        """Compose a system-level skill context string to prepend to Claude calls."""
        if not skill_names:
            return ""
        parts = []
        for name in skill_names:
            info = self._skills.get(name)
            if info:
                parts.append(
                    f"<skill name=\"{name}\">\n{info['content']}\n</skill>"
                )
        if not parts:
            return ""
        return (
            "<skills>\n"
            "The following Agent Skills provide you with specialized instructions.\n"
            "Follow them carefully when completing the user's request.\n\n"
            + "\n\n".join(parts)
            + "\n</skills>\n"
        )

    # ── Internal ──────────────────────────────────────────────────────────────

    def _load_skill(self, name: str, path: Path) -> None:
        try:
            content = path.read_text(encoding="utf-8")
            description = self._extract_description(content)
            self._skills[name] = {
                "content": content,
                "description": description,
                "size": len(content),
                "path": str(path),
            }
            logger.info("  ✓ skill '%s' (%d chars)", name, len(content))
        except Exception as e:
            logger.warning("  ✗ Failed to load skill '%s': %s", name, e)

    @staticmethod
    def _name_from_path(path: Path) -> str:
        """Derive a skill name from its directory."""
        # skills/docx/SKILL.md → "docx"
        return path.parent.name.lower()

    @staticmethod
    def _extract_description(content: str) -> str:
        """Try to pull the first meaningful sentence from a SKILL.md."""
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("<!--"):
                return line[:200]
        return ""
