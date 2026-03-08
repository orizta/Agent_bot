"""
Telegram Bot with Agent Skills (SKILL.md) support
Deploy via GitHub + Railway
"""

import os
import re
import logging
from pathlib import Path

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode, ChatAction

from skill_loader import SkillLoader
from claude_client import ClaudeClient

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Globals ───────────────────────────────────────────────────────────────────
skill_loader = SkillLoader("skills/")
claude_client = ClaudeClient()

# ── Handlers ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    skills = skill_loader.list_skills()
    skill_list = "\n".join(f"  • `{s}`" for s in skills) if skills else "  _(belum ada skill)_"
    text = (
        "👋 *Selamat datang di Skill Bot!*\n\n"
        "Bot ini menggunakan *Agent Skills* (SKILL\\.md) untuk memperluas kemampuan AI\\.\n\n"
        f"📦 *Skill tersedia:*\n{skill_list}\n\n"
        "Ketik pesan apa saja untuk mulai\\. Bot akan otomatis memilih skill yang tepat\\.\n\n"
        "📌 Perintah:\n"
        "  /skills — lihat daftar skill\n"
        "  /skill \\<nama\\> — info skill tertentu\n"
        "  /help — bantuan"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🤖 *Cara pakai:*\n\n"
        "Cukup ketik pertanyaan atau permintaan Anda\\. Contoh:\n"
        "  • _Buatkan dokumen Word laporan penjualan_\n"
        "  • _Buat presentasi 5 slide tentang AI_\n"
        "  • _Analisis data Excel ini_\n\n"
        "Bot akan otomatis memuat skill yang sesuai dan menjawab dengan akurat\\.\n\n"
        "Gunakan /skills untuk melihat semua skill yang tersedia\\."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_skills(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    skills = skill_loader.list_skills()
    if not skills:
        await update.message.reply_text("⚠️ Belum ada skill yang dimuat.")
        return
    lines = ["📦 *Skill yang tersedia:*\n"]
    for name in skills:
        info = skill_loader.get_skill_info(name)
        desc = info.get("description", "Tidak ada deskripsi")[:80]
        lines.append(f"• *{name}*\n  _{desc}_")
    await update.message.reply_text(
        "\n\n".join(lines), parse_mode=ParseMode.MARKDOWN_V2
    )


async def cmd_skill_info(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not ctx.args:
        await update.message.reply_text("⚠️ Gunakan: /skill <nama_skill>")
        return
    name = ctx.args[0].lower()
    info = skill_loader.get_skill_info(name)
    if not info:
        await update.message.reply_text(f"❌ Skill `{name}` tidak ditemukan.")
        return
    content_preview = info.get("content", "")[:500]
    text = (
        f"📄 *Skill: {name}*\n\n"
        f"```\n{content_preview}\n```\n"
        f"_\\.\\.\\. ({info.get('size', 0)} karakter total\\)_"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = update.message.text or ""
    if not user_text.strip():
        return

    await update.message.chat.send_action(ChatAction.TYPING)

    # Detect relevant skills based on message content
    relevant_skills = skill_loader.detect_relevant_skills(user_text)
    skill_context = skill_loader.build_skill_context(relevant_skills)

    if relevant_skills:
        skill_names = ", ".join(relevant_skills)
        await update.message.reply_text(
            f"🔍 Memuat skill: `{skill_names}`...", parse_mode=ParseMode.MARKDOWN_V2
        )
        await update.message.chat.send_action(ChatAction.TYPING)

    try:
        response = await claude_client.chat(
            user_message=user_text,
            skill_context=skill_context,
        )
        # Kirim respons — pecah jika terlalu panjang
        for chunk in split_message(response):
            await update.message.reply_text(chunk)
    except Exception as e:
        logger.error("Claude error: %s", e)
        await update.message.reply_text(
            "❌ Terjadi kesalahan saat memproses pesan Anda. Coba lagi nanti."
        )


def split_message(text: str, limit: int = 4000) -> list[str]:
    """Split long messages to fit Telegram's 4096 char limit."""
    if len(text) <= limit:
        return [text]
    chunks = []
    while text:
        chunks.append(text[:limit])
        text = text[limit:]
    return chunks


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("❌ TELEGRAM_BOT_TOKEN environment variable is not set!")

    logger.info("Starting Telegram Skill Bot…")
    skill_loader.load_all()
    logger.info("Loaded skills: %s", skill_loader.list_skills())

    app = Application.builder().token(token).build()

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("skills", cmd_skills))
    app.add_handler(CommandHandler("skill", cmd_skill_info))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Register commands in Telegram menu
    async def post_init(application: Application) -> None:
        await application.bot.set_my_commands([
            BotCommand("start", "Mulai & info bot"),
            BotCommand("skills", "Daftar skill tersedia"),
            BotCommand("skill", "Info skill tertentu"),
            BotCommand("help", "Bantuan"),
        ])

    app.post_init = post_init

    logger.info("Bot running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
