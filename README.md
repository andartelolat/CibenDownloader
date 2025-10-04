# Ciben YT Downloader

> YouTube video & audio downloader berbasis **Flask** dengan UI **Tailwind** yang modern dan ringan. Mendukung **progressive (≤720p)** & **adaptive (hingga 4K)**, serta **auto-merge** video+audio memakai **FFmpeg** (jika tersedia). Mobile-first, dark mode, animated gradient background, dan “Poké ball” bubbles yang bergerak lembut.

![demo](docs/demo.gif) <!-- Optional: ganti dengan GIF/PNG demo -->

<p align="center">
  <a href="#fitur">Fitur</a> •
  <a href="#persyaratan">Persyaratan</a> •
  <a href="#instalasi">Instalasi</a> •
  <a href="#menjalankan">Menjalankan</a> •
  <a href="#cara-pakai">Cara Pakai</a> •
  <a href="#konfigurasi--opsional">Konfigurasi</a> •
  <a href="#troubleshooting">Troubleshooting</a> •
  <a href="#roadmap">Roadmap</a> •
  <a href="#legal--disclaimer">Legal</a> •
  <a href="#license">License</a>
</p>

---

## Fitur

- 🎯 **Simple & cepat**: Tempel URL → pilih kualitas → unduh.
- 🧩 **Mode Mudah (progressive)**: Video+audio dalam satu file (≤720p).
- 💎 **Mode Maks (adaptive)**: Hingga 1080p/1440p/2160p (4K).  
  - **Auto-merge** video+audio jika **FFmpeg** terdeteksi.  
  - Tanpa FFmpeg, tetap bisa unduh **video-only**.
- 🎨 **UI modern & mobile-first**: Tailwind, dark mode, animated gradient background, “Poké ball” bubbles, micro-interactions.
- 🔍 **Preview**: Thumbnail live saat URL ditempel, judul muncul setelah pemrosesan.
- 📁 **Folder unduhan otomatis** lintas OS:
  - **Windows**: `~/Downloads/YTDownloads`
  - **Linux/Termux (Android)**: `~/storage/shared/YTDownloads`
  - **macOS/Unix lain**: `~/Downloads/YTDownloads`

---

## Persyaratan

- **Python** 3.9+ (disarankan 3.10/3.11)
- **pip**
- **FFmpeg** (opsional, tetapi direkomendasikan untuk gabung video+audio dan konversi cepat)
- Koneksi internet stabil

Python packages (intinya):
- `Flask`
- `pytubefix`

---

## Instalasi

```bash
git clone https://github.com/andartelolat/<repo-kamu>.git
cd <repo-kamu>

# Buat venv (opsional tapi disarankan)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install deps
pip install flask pytubefix
