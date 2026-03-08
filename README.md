# 🤖 Telegram Skill Bot

Bot Telegram berbasis **Claude AI** dengan dukungan **Agent Skills** (SKILL.md).  
Deploy otomatis via **GitHub → Railway**.

---

## 📁 Struktur Proyek

```
telegram-skill-bot/
├── bot.py              # Entry point bot
├── skill_loader.py     # Loader & detector SKILL.md
├── claude_client.py    # Wrapper Anthropic API
├── requirements.txt
├── Procfile            # Untuk Railway
├── railway.toml        # Konfigurasi Railway
├── .env.example        # Template environment variables
├── .gitignore
└── skills/             # Folder skill
    ├── general/
    │   └── SKILL.md
    ├── docx/
    │   └── SKILL.md    # Tambahkan skill lain di sini
    └── ...
```

---

## ⚙️ Setup Lokal

### 1. Clone & Install

```bash
git clone https://github.com/USERNAME/telegram-skill-bot.git
cd telegram-skill-bot
pip install -r requirements.txt
```

### 2. Buat file `.env`

```bash
cp .env.example .env
```

Edit `.env`:
```
TELEGRAM_BOT_TOKEN=token_dari_botfather
ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Dapatkan Token Telegram

1. Buka [@BotFather](https://t.me/BotFather) di Telegram
2. Ketik `/newbot` dan ikuti instruksi
3. Copy token yang diberikan ke `.env`

### 4. Jalankan

```bash
python bot.py
```

---

## 🚀 Deploy ke Railway via GitHub

### Langkah 1 — Push ke GitHub

```bash
git init
git add .
git commit -m "Initial commit: Telegram Skill Bot"
git branch -M main
git remote add origin https://github.com/USERNAME/telegram-skill-bot.git
git push -u origin main
```

### Langkah 2 — Buat Project di Railway

1. Buka [railway.app](https://railway.app) dan login
2. Klik **New Project** → **Deploy from GitHub repo**
3. Pilih repo `telegram-skill-bot`
4. Railway otomatis mendeteksi Python dan menginstall dependensi

### Langkah 3 — Set Environment Variables di Railway

Di dashboard Railway, buka tab **Variables** dan tambahkan:

| Variable | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | token dari BotFather |
| `ANTHROPIC_API_KEY` | API key dari console.anthropic.com |

### Langkah 4 — Deploy

Railway akan otomatis deploy setiap kali kamu push ke `main`.  
Cek log di tab **Deployments** untuk memastikan bot berjalan.

---

## 📦 Menambahkan Skill Baru

1. Buat folder di `skills/nama-skill/`
2. Buat file `SKILL.md` dengan instruksi untuk Claude
3. Tambahkan keyword di `skill_loader.py` → `SKILL_KEYWORDS`
4. Push ke GitHub — Railway deploy otomatis

### Contoh menambah skill `docx`:

```bash
mkdir -p skills/docx
# Salin SKILL.md dari Agent Skills library atau buat sendiri
cp path/to/docx/SKILL.md skills/docx/SKILL.md
git add skills/docx/SKILL.md
git commit -m "Add docx skill"
git push
```

---

## 🤖 Perintah Bot

| Perintah | Fungsi |
|---|---|
| `/start` | Sapa & info bot |
| `/skills` | Daftar skill tersedia |
| `/skill <nama>` | Info skill tertentu |
| `/help` | Bantuan |

Kirim pesan biasa → bot otomatis deteksi skill yang relevan dan jawab.

---

## 🔧 Kustomisasi

- **Bahasa default**: Edit `SYSTEM_BASE` di `claude_client.py`
- **Keyword deteksi skill**: Edit `SKILL_KEYWORDS` di `skill_loader.py`
- **Model Claude**: Ganti `DEFAULT_MODEL` di `claude_client.py`
- **Tambah skill**: Buat folder baru di `skills/`

---

## 📚 Referensi

- [Agent Skills Spec](https://agentskills.io/specification)
- [python-telegram-bot docs](https://python-telegram-bot.readthedocs.io)
- [Anthropic API docs](https://docs.anthropic.com)
- [Railway docs](https://docs.railway.app)
