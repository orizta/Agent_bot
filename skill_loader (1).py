"""
skill_loader.py — Loads and manages SKILL.md files from the skills/ directory.
Compatible with the Agent Skills open standard (https://agentskills.io)
"""

from __future__ import annotations

import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Built-in keyword → skill name mapping
BUILTIN_KEYWORDS: dict[str, list[str]] = {
    "docx": [
        "word", "dokumen", "document", "docx", ".docx",
        "laporan word", "surat", "letter", "memo",
    ],
    "pptx": [
        "presentasi", "presentation", "slide", "pptx", ".pptx",
        "powerpoint", "deck", "pitch deck",
    ],
    "xlsx": [
        "excel", "spreadsheet", "xlsx", ".xlsx", "tabel",
        "data excel", "csv", "kalkulasi",
    ],
    "pdf": [
        "pdf", ".pdf", "portable document", "gabung pdf", "merge pdf",
    ],
    "frontend-design": [
        "website", "web", "html", "css", "react", "komponen",
        "component", "ui", "ux", "landing page", "desain web",
    ],
}

# File to persist custom skill keywords
CUSTOM_KEYWORDS_FILE = "skills/_custom_keywords.json"


class SkillLoader:
    """Discovers, loads, and serves SKILL.md content."""

    def __init__(self, skills_dir: str = "skills/") -> None:
        self.skills_dir = Path(skills_dir)
        self._skills: dict[str, dict] = {}
        self._custom_keywords: dict[str, list[str]] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    def load_all(self) -> None:
        """Load every SKILL.md found under skills_dir."""
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self._load_custom_keywords()

        for path in sorted(self.skills_dir.rglob("SKILL.md")):
            name = self._name_from_path(path)
            is_custom = path.parent.parent.name == "_custom" or \
                        str(path).find("/_custom/") != -1 or \
                        name in self._custom_keywords
            self._load_skill(name, path, custom=is_custom)

        logger.info("Loaded %d skill(s): %s", len(self._skills), list(self._skills.keys()))

    def list_skills(self) -> list[str]:
        return sorted(self._skills.keys())

    def get_skill_info(self, name: str) -> dict | None:
        return self._skills.get(name.lower())

    def detect_relevant_skills(self, text: str) -> list[str]:
        """Return skill names whose keywords appear in the user text."""
        text_lower = text.lower()
        matched = []

        # Check built-in keywords
        for skill_name, keywords in BUILTIN_KEYWORDS.items():
            if skill_name in self._skills and any(kw in text_lower for kw in keywords):
                matched.append(skill_name)

        # Check custom keywords
        for skill_name, keywords in self._custom_keywords.items():
            if skill_name in self._skills and skill_name not in matched:
                if any(kw in text_lower for kw in keywords):
                    matched.append(skill_name)

        return matched

    def build_skill_context(self, skill_names: list[str]) -> str:
        """Compose skill context string to inject into Claude system prompt."""
        if not skill_names:
            return ""
        parts = []
        for name in skill_names:
            info = self._skills.get(name)
            if info:
                parts.append(f'<skill name="{name}">\n{info["content"]}\n</skill>')
        if not parts:
            return ""
        return (
            "<skills>\n"
            "Ikuti instruksi dari skill berikut saat menjawab permintaan user.\n\n"
            + "\n\n".join(parts)
            + "\n</skills>\n"
        )

    def save_custom_skill(
        self, name: str, content: str, keywords: list[str]
    ) -> tuple[bool, str]:
        """Save a new custom skill created via Telegram chat."""
        try:
            skill_dir = self.skills_dir / "_custom" / name
            skill_dir.mkdir(parents=True, exist_ok=True)
            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text(content, encoding="utf-8")

            # Register keywords
            self._custom_keywords[name] = keywords
            self._save_custom_keywords()

            # Load into memory immediately
            self._load_skill(name, skill_file, custom=True)

            logger.info("Custom skill '%s' saved with keywords: %s", name, keywords)
            return True, f"Skill '{name}' berhasil disimpan."
        except Exception as e:
            logger.error("Failed to save custom skill '%s': %s", name, e)
            return False, str(e)

    def delete_skill(self, name: str) -> tuple[bool, str]:
        """Delete a custom skill."""
        info = self._skills.get(name)
        if not info:
            return False, f"Skill '{name}' tidak ditemukan."
        if not info.get("custom"):
            return False, f"Skill '{name}' adalah skill bawaan dan tidak bisa dihapus."

        try:
            skill_path = Path(info["path"])
            skill_path.unlink(missing_ok=True)
            # Try to remove empty parent dirs
            try:
                skill_path.parent.rmdir()
            except OSError:
                pass

            # Remove from keywords & memory
            self._custom_keywords.pop(name, None)
            self._save_custom_keywords()
            self._skills.pop(name, None)

            logger.info("Custom skill '%s' deleted.", name)
            return True, f"Skill '{name}' berhasil dihapus."
        except Exception as e:
            logger.error("Failed to delete skill '%s': %s", name, e)
            return False, str(e)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _load_skill(self, name: str, path: Path, custom: bool = False) -> None:
        try:
            content = path.read_text(encoding="utf-8")
            description = self._extract_description(content)
            self._skills[name] = {
                "content": content,
                "description": description,
                "size": len(content),
                "path": str(path),
                "custom": custom,
            }
            label = "custom" if custom else "built-in"
            logger.info("  ✓ [%s] skill '%s' (%d chars)", label, name, len(content))
        except Exception as e:
            logger.warning("  ✗ Failed to load skill '%s': %s", name, e)

    def _load_custom_keywords(self) -> None:
        kw_file = Path(CUSTOM_KEYWORDS_FILE)
        if kw_file.exists():
            try:
                self._custom_keywords = json.loads(kw_file.read_text(encoding="utf-8"))
                logger.info("Loaded custom keywords for: %s", list(self._custom_keywords.keys()))
            except Exception as e:
                logger.warning("Could not load custom keywords: %s", e)
                self._custom_keywords = {}

    def _save_custom_keywords(self) -> None:
        kw_file = Path(CUSTOM_KEYWORDS_FILE)
        kw_file.parent.mkdir(parents=True, exist_ok=True)
        kw_file.write_text(
            json.dumps(self._custom_keywords, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _name_from_path(path: Path) -> str:
        return path.parent.name.lower()

    @staticmethod
    def _extract_description(content: str) -> str:
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("<!--"):
                return line[:200]
        return ""
