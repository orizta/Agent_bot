"""
Telegram Bot with Agent Skills (SKILL.md) support
Deploy via GitHub + Railway
"""

from __future__ import annotations

import os
import re
import logging
from pathlib import Path

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode, ChatAction

from skill_loader import SkillLoader
from claude_client import ClaudeClient

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Conversation states ────────────────────────────────────────────────────────
ASK_SKILL_NAME, ASK_SKILL_KEYWORDS, ASK_SKILL_CONTENT, CONFIRM_SKILL = range(4)

# ── Globals ───────────────────────────────────────────────────────────────────
ADMIN_IDS_RAW = os.environ.get("ADMIN_IDS", "")
ADMIN_IDS = set(int(x.strip()) for x in ADMIN_IDS_RAW.split(",") if x.strip().isdigit())

skill_loader = SkillLoader("skills/")
claude_client = ClaudeClient()


def is_admin(user_id: int) -> bool:
    """Jika ADMIN_IDS tidak di-set, semua user bisa tambah skill."""
    return not ADMIN_IDS or user_id in ADMIN_IDS


# ── Standard Handlers ─────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    skills = skill_loader.list_skills()
    skill_list = "\n".join(f"  • {s}" for s in skills) if skills else "  (belum ada skill)"
    text = (
        "👋 Selamat datang di Skill Bot!\n\n"
        "Bot ini menggunakan Agent Skills (SKILL.md) untuk memperluas kemampuan AI.\n\n"
        f"📦 Skill tersedia:\n{skill_list}\n\n"
        "Ketik pesan apa saja untuk mulai.\n\n"
        "📌 Perintah:\n"
        "  /skills — lihat daftar skill\n"
        "  /addskill — tambah skill baru via chat\n"
        "  /deleteskill <nama> — hapus skill\n"
        "  /skill <nama> — info skill tertentu\n"
        "  /help — bantuan"
    )
    await update.message.reply_text(text)


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🤖 Cara pakai:\n\n"
        "Cukup ketik pertanyaan atau permintaan Anda. Contoh:\n"
        "  • Buatkan dokumen Word laporan penjualan\n"
        "  • Buat presentasi 5 slide tentang AI\n"
        "  • Analisis data Excel ini\n\n"
        "Bot akan otomatis memuat skill yang sesuai.\n\n"
        "➕ Tambah skill baru: /addskill\n"
        "📋 Lihat semua skill: /skills\n"
        "🗑 Hapus skill: /deleteskill <nama>"
    )
    await update.message.reply_text(text)


async def cmd_skills(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    skills = skill_loader.list_skills()
    if not skills:
        await update.message.reply_text("⚠️ Belum ada skill yang dimuat.")
        return
    lines = ["📦 Skill yang tersedia:\n"]
    for name in skills:
        info = skill_loader.get_skill_info(name)
        desc = info.get("description", "Tidak ada deskripsi")[:80]
        source = "📝 custom" if info.get("custom") else "📦 bawaan"
        lines.append(f"• {name} ({source})\n  {desc}")
    await update.message.reply_text("\n\n".join(lines))


async def cmd_skill_info(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not ctx.args:
        await update.message.reply_text("Gunakan: /skill <nama_skill>")
        return
    name = ctx.args[0].lower()
    info = skill_loader.get_skill_info(name)
    if not info:
        await update.message.reply_text(f"❌ Skill '{name}' tidak ditemukan.")
        return
    content_preview = info.get("content", "")[:600]
    text = (
        f"📄 Skill: {name}\n\n"
        f"{content_preview}\n"
        f"... ({info.get('size', 0)} karakter total)"
    )
    await update.message.reply_text(text)


async def cmd_delete_skill(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Kamu tidak punya akses untuk menghapus skill.")
        return
    if not ctx.args:
        await update.message.reply_text("Gunakan: /deleteskill <nama_skill>")
        return
    name = ctx.args[0].lower()
    success, msg = skill_loader.delete_skill(name)
    await update.message.reply_text("✅ " + msg if success else "❌ " + msg)


# ── Add Skill Conversation ─────────────────────────────────────────────────────

async def addskill_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Kamu tidak punya akses untuk menambah skill.")
        return ConversationHandler.END

    await update.message.reply_text(
        "➕ Tambah Skill Baru\n\n"
        "Langkah 1/3 — Ketik NAMA skill (huruf kecil, tanpa spasi).\n"
        "Contoh: memasak, hukum, keuangan, coding\n\n"
        "Ketik /cancel untuk batal."
    )
    return ASK_SKILL_NAME


async def addskill_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip().lower()
    name = re.sub(r"[^a-z0-9_-]", "", name)

    if not name:
        await update.message.reply_text("❌ Nama tidak valid. Gunakan huruf/angka saja. Coba lagi:")
        return ASK_SKILL_NAME

    if skill_loader.get_skill_info(name):
        await update.message.reply_text(
            f"⚠️ Skill '{name}' sudah ada.\n"
            "Gunakan nama lain, atau /deleteskill untuk menghapus yang lama."
        )
        return ASK_SKILL_NAME

    ctx.user_data["new_skill_name"] = name
    await update.message.reply_text(
        f"✅ Nama skill: {name}\n\n"
        "Langkah 2/3 — Ketik KEYWORD yang akan memicu skill ini.\n"
        "Pisahkan dengan koma.\n\n"
        f"Contoh untuk skill '{name}':\n"
        "  resep, masak, makanan, bahan, cara membuat\n\n"
        "Ketik /cancel untuk batal."
    )
    return ASK_SKILL_KEYWORDS


async def addskill_keywords(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    raw = update.message.text.strip()
    keywords = [k.strip().lower() for k in raw.split(",") if k.strip()]

    if not keywords:
        await update.message.reply_text("❌ Keyword tidak boleh kosong. Coba lagi:")
        return ASK_SKILL_KEYWORDS

    ctx.user_data["new_skill_keywords"] = keywords
    name = ctx.user_data["new_skill_name"]

    await update.message.reply_text(
        f"✅ Keywords: {', '.join(keywords)}\n\n"
        "Langkah 3/3 — Ketik ISI skill (instruksi untuk Claude).\n\n"
        "Contoh format:\n"
        "──────────────────\n"
        f"# {name.title()} Skill\n\n"
        "Kamu adalah ahli di bidang ini. Ketika user bertanya:\n"
        "- Jawab dengan detail dan akurat\n"
        "- Berikan contoh nyata\n"
        "- Gunakan bahasa yang mudah dipahami\n"
        "──────────────────\n\n"
        "Ketik /cancel untuk batal."
    )
    return ASK_SKILL_CONTENT


async def addskill_content(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    content = update.message.text.strip()

    if len(content) < 20:
        await update.message.reply_text(
            "❌ Instruksi terlalu pendek (min 20 karakter). Tulis lebih detail:"
        )
        return ASK_SKILL_CONTENT

    ctx.user_data["new_skill_content"] = content
    name = ctx.user_data["new_skill_name"]
    keywords = ctx.user_data["new_skill_keywords"]

    preview = content[:300] + ("..." if len(content) > 300 else "")
    await update.message.reply_text(
        f"📋 Konfirmasi Skill Baru:\n\n"
        f"Nama     : {name}\n"
        f"Keywords : {', '.join(keywords)}\n\n"
        f"Isi:\n{preview}\n\n"
        "Ketik YA untuk simpan, atau TIDAK untuk batal."
    )
    return CONFIRM_SKILL


async def addskill_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    answer = update.message.text.strip().upper()

    if answer not in ("YA", "TIDAK", "Y", "N", "YES", "NO"):
        await update.message.reply_text("Ketik YA untuk simpan atau TIDAK untuk batal.")
        return CONFIRM_SKILL

    if answer in ("TIDAK", "N", "NO"):
        ctx.user_data.clear()
        await update.message.reply_text("❌ Dibatalkan. Skill tidak disimpan.")
        return ConversationHandler.END

    name = ctx.user_data["new_skill_name"]
    keywords = ctx.user_data["new_skill_keywords"]
    content = ctx.user_data["new_skill_content"]

    success, msg = skill_loader.save_custom_skill(name, content, keywords)

    if success:
        await update.message.reply_text(
            f"✅ Skill '{name}' berhasil disimpan!\n\n"
            f"Bot akan otomatis pakai skill ini ketika ada kata:\n"
            f"{', '.join(keywords)}\n\n"
            "Gunakan /skills untuk lihat semua skill."
        )
    else:
        await update.message.reply_text(f"❌ Gagal menyimpan skill: {msg}")

    ctx.user_data.clear()
    return ConversationHandler.END


async def addskill_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data.clear()
    await update.message.reply_text("❌ Pembuatan skill dibatalkan.")
    return ConversationHandler.END


# ── Message Handler ───────────────────────────────────────────────────────────

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = update.message.text or ""
    if not user_text.strip():
        return

    await update.message.chat.send_action(ChatAction.TYPING)

    relevant_skills = skill_loader.detect_relevant_skills(user_text)
    skill_context = skill_loader.build_skill_context(relevant_skills)

    if relevant_skills:
        skill_names = ", ".join(relevant_skills)
        await update.message.reply_text(f"🔍 Menggunakan skill: {skill_names}")
        await update.message.chat.send_action(ChatAction.TYPING)

    try:
        response = await claude_client.chat(
            user_message=user_text,
            skill_context=skill_context,
        )
        for chunk in split_message(response):
            await update.message.reply_text(chunk)
    except Exception as e:
        logger.error("Claude error: %s", e)
        await update.message.reply_text(
            "❌ Terjadi kesalahan saat memproses pesan. Coba lagi nanti."
        )


def split_message(text: str, limit: int = 4000) -> "list[str]":
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
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is not set!")

    logger.info("Starting Telegram Skill Bot…")
    skill_loader.load_all()
    logger.info("Loaded skills: %s", skill_loader.list_skills())

    app = Application.builder().token(token).build()

    # Conversation handler untuk /addskill
    add_skill_conv = ConversationHandler(
        entry_points=[CommandHandler("addskill", addskill_start)],
        states={
            ASK_SKILL_NAME:     [MessageHandler(filters.TEXT & ~filters.COMMAND, addskill_name)],
            ASK_SKILL_KEYWORDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, addskill_keywords)],
            ASK_SKILL_CONTENT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, addskill_content)],
            CONFIRM_SKILL:      [MessageHandler(filters.TEXT & ~filters.COMMAND, addskill_confirm)],
        },
        fallbacks=[CommandHandler("cancel", addskill_cancel)],
    )

    app.add_handler(add_skill_conv)
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("skills", cmd_skills))
    app.add_handler(CommandHandler("skill", cmd_skill_info))
    app.add_handler(CommandHandler("deleteskill", cmd_delete_skill))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    async def post_init(application: Application) -> None:
        await application.bot.set_my_commands([
            BotCommand("start",       "Mulai & info bot"),
            BotCommand("skills",      "Daftar skill tersedia"),
            BotCommand("addskill",    "Tambah skill baru via chat"),
            BotCommand("deleteskill", "Hapus skill"),
            BotCommand("skill",       "Info skill tertentu"),
            BotCommand("help",        "Bantuan"),
        ])

    app.post_init = post_init

    logger.info("Bot running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
