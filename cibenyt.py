from flask import Flask, request, render_template_string, send_file
from pytubefix import YouTube
import os, re, platform, shutil, tempfile, subprocess

app = Flask(__name__)

# ---------- Utilities ----------
def safe_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip() or "video"

def get_download_folder():
    system = platform.system().lower()
    if "linux" in system:  # termasuk Android (Termux)
        path = os.path.expanduser("~/storage/shared/YTDownloads")
    elif "windows" in system:
        path = os.path.join(os.path.expanduser("~/Downloads"), "YTDownloads")
    else:
        path = os.path.join(os.path.expanduser("~"), "Downloads", "YTDownloads")
    os.makedirs(path, exist_ok=True)
    return path

DOWNLOAD_FOLDER = get_download_folder()

def valid_youtube_url(url):
    pattern = r"(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w-]+"
    return re.match(pattern, url)

def clean_youtube_url(url):
    if "youtu.be" in url:
        return url.split("?")[0]
    elif "youtube.com/watch" in url:
        return url.split("&")[0]
    return url

def ffmpeg_available():
    return shutil.which("ffmpeg") is not None

def merge_av(video_path, audio_path, out_basename, v_mime="video/mp4", a_mime="audio/mp4"):
    """
    Gabungkan video+audio menggunakan ffmpeg.
    - Jika keduanya MP4/H.264/AAC, hasilkan .mp4 dengan -c copy (cepat).
    - Jika codec/container beda, hasilkan .mkv dengan -c copy (tanpa re-encode) agar cepat.
    """
    out_ext = ".mp4" if ("mp4" in v_mime and "mp4" in a_mime) else ".mkv"
    out_path = os.path.join(DOWNLOAD_FOLDER, out_basename + out_ext)

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path, "-i", audio_path,
        "-c", "copy",
        out_path
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return out_path
    except Exception:
        # fallback re-encode ringan ke mp4 untuk kompatibilitas luas
        out_path = os.path.join(DOWNLOAD_FOLDER, out_basename + ".mp4")
        cmd_reencode = [
            "ffmpeg", "-y",
            "-i", video_path, "-i", audio_path,
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            out_path
        ]
        subprocess.run(cmd_reencode, check=True)
        return out_path

# ---------- UI (Tailwind + Alpine) ----------
# ---------- UI (Tailwind + Alpine) ----------
html_form = """
<!doctype html>
<html lang="id" x-data="app()" :class="darkMode ? 'dark' : ''">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#111827">
  <script src="https://cdn.tailwindcss.com"></script>
  <script defer src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"></script>
  <title>Ciben YT Downloader</title>
  <style>
    :root{
      --bg1: #ef4444;  /* red-500 */
      --bg2: #3b82f6;  /* blue-500 */
      --bg3: #22c55e;  /* green-500 */
      --bg4: #eab308;  /* yellow-500 */
    }
    .dark:root{
      --bg1: #f43f5e; /* rose-500 */
      --bg2: #06b6d4; /* cyan-500 */
      --bg3: #a855f7; /* violet-500 */
      --bg4: #fb7185; /* rose-400 */
    }

    /* Layer gradient animasi halus */
    .animated-bg{
      position: fixed; inset: 0; z-index: -2;
      background:
        radial-gradient(1200px 600px at 10% 15%, color-mix(in oklab, var(--bg1), transparent 80%), transparent),
        radial-gradient(800px 500px at 90% 20%, color-mix(in oklab, var(--bg2), transparent 82%), transparent),
        radial-gradient(1000px 600px at 60% 85%, color-mix(in oklab, var(--bg3), transparent 82%), transparent),
        radial-gradient(1200px 800px at 30% 60%, color-mix(in oklab, var(--bg4), transparent 85%), transparent);
      filter: saturate(1.1);
      animation: gradientShift 24s ease-in-out infinite alternate;
    }
    @keyframes gradientShift{
      0%   { transform: translate3d(0,0,0); filter: hue-rotate(0deg) saturate(1.05); }
      50%  { transform: translate3d(-1.5%, -1%, 0); filter: hue-rotate(10deg) saturate(1.15); }
      100% { transform: translate3d(1.5%, 1%, 0); filter: hue-rotate(-10deg) saturate(1.1); }
    }

    /* Layer bola Pokémon */
    .bubble-layer{ position: fixed; inset: 0; z-index: -1; pointer-events:none; overflow:hidden; }
    .poke{
      position:absolute; border-radius:9999px;
      box-shadow:
        0 0 0 2px rgba(0,0,0,.25) inset,
        0 8px 24px rgba(0,0,0,.12);
      will-change: transform;
    }
    /* Desain pokeball dengan gradient (setengah merah/putih + garis hitam + lingkaran tengah) */
    .poke::before, .poke::after{ content:""; position:absolute; inset:0; border-radius:inherit; }
    /* Top half merah & bottom putih menggunakan linear-gradient */
    .poke::before{
      background:
        linear-gradient(#000 0 0) center/100% 10% no-repeat, /* garis hitam tengah, disetel via transform */
        linear-gradient(to bottom, #ef4444 0 50%, #ffffff 50% 100%);
      transform: translateY(calc(var(--line, 0%) - 0%)); /* placeholder agar mudah diubah bila perlu */
      opacity:.98;
    }
    /* Tombol pusat */
    .poke::after{
      width:34%; height:34%; margin:auto; top:0; bottom:0; left:0; right:0;
      border-radius:9999px; background:
        radial-gradient(circle at 50% 50%, #fff 0 45%, #000 46% 60%, transparent 61%);
      box-shadow: 0 0 0 2px rgba(0,0,0,.35);
    }

    /* Animasi gerak lembut (kombinasi) */
    @keyframes floatY { 0%{ transform: translateY(0px) } 50%{ transform: translateY(-18px) } 100%{ transform: translateY(0px) } }
    @keyframes driftX { 0%{ transform: translateX(0px) } 50%{ transform: translateX(16px) } 100%{ transform: translateX(0px) } }

    .floatY{ animation: floatY var(--fy, 12s) ease-in-out infinite; }
    .driftX{ animation: driftX var(--fx, 14s) ease-in-out infinite; }

    /* Aksesibilitas: hormati reduced-motion */
    @media (prefers-reduced-motion: reduce){
      .animated-bg, .floatY, .driftX{ animation: none !important; }
    }

    /* Card blur halus di atas background */
    .surface{
      backdrop-filter: blur(8px);
      background: color-mix(in oklab, #ffffff, transparent 8%);
    }
    .dark .surface{
      background: color-mix(in oklab, #0b1220, transparent 5%);
    }

    /* Micro transitions untuk tombol */
    @media (prefers-reduced-motion:no-preference){
      .btn-trans{ transition: transform .15s ease, box-shadow .2s ease; }
      .btn-trans:active{ transform: translateY(1px) scale(.995); }
      .btn-trans:hover{ box-shadow: 0 6px 16px rgba(0,0,0,.12); }
    }
  </style>
</head>
<body class="min-h-screen bg-white/60 dark:bg-gray-950/60 text-gray-900 dark:text-gray-100">
  <!-- Background layers -->
  <div class="animated-bg"></div>
  <div id="bubbleLayer" class="bubble-layer"></div>

  <!-- Top App Bar -->
  <header class="sticky top-0 z-40 bg-white/60 dark:bg-gray-900/60 backdrop-blur border-b border-white/20 dark:border-white/10">
    <div class="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="h-9 w-9 rounded-xl bg-red-500 text-white grid place-items-center font-bold">YT</div>
        <div class="font-bold">Downloader</div>
        <span class="ml-2 text-[10px] px-2 py-0.5 rounded-full bg-gray-900 text-white dark:bg-white dark:text-gray-900">by Cibens</span>
      </div>
      <div class="flex items-center gap-2">
        <button @click="toggleTheme" class="rounded-lg px-3 py-1.5 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 text-sm btn-trans">
          <span x-show="!darkMode">🌙</span><span x-show="darkMode">☀️</span>
        </button>
      </div>
    </div>
  </header>

  <!-- Main -->
  <main class="max-w-4xl mx-auto px-4 pb-28 pt-6">
    <!-- Card -->
    <div class="rounded-2xl border border-gray-200/70 dark:border-gray-800/70 surface">
      <form id="mainForm" method="POST" class="p-4 sm:p-6 space-y-4" @submit="onSubmit">
        <!-- URL input -->
        <div>
          <label class="block text-sm font-semibold mb-1">URL YouTube</label>
          <div class="flex gap-2">
            <input type="text" name="url" x-model="url" @input="onUrlInput" placeholder="https://www.youtube.com/watch?v=..." value="{{ url or '' }}"
                   class="w-full px-3 py-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white/80 dark:bg-gray-800/70 focus:outline-none focus:ring-2 focus:ring-red-400" required>
            <button type="button" @click="pasteUrl" title="Tempel"
              class="shrink-0 px-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white/70 dark:bg-gray-800/70 hover:bg-gray-50 dark:hover:bg-gray-800 btn-trans">📋</button>
          </div>
          <p class="mt-1 text-xs text-gray-700/80 dark:text-gray-300/80">Preview thumbnail muncul otomatis.</p>
        </div>

        <!-- Mode selector -->
        <div>
          <label class="block text-sm font-semibold mb-1">Mode</label>
          <div class="grid grid-cols-2 gap-2">
            <label class="border rounded-xl p-2 text-sm flex items-center justify-center gap-2 cursor-pointer btn-trans"
                   :class="mode==='easy' ? 'bg-red-50/70 border-red-200 dark:bg-red-900/20 dark:border-red-800' : 'border-gray-200 dark:border-gray-700'">
              <input type="radio" class="hidden" name="mode" value="easy" x-model="mode">
              <span>🔥 Mudah (≤720p, video+audio)</span>
            </label>
            <label class="border rounded-xl p-2 text-sm flex items-center justify-center gap-2 cursor-pointer btn-trans"
                   :class="mode==='max' ? 'bg-blue-50/70 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800' : 'border-gray-200 dark:border-gray-700'">
              <input type="radio" class="hidden" name="mode" value="max" x-model="mode">
              <span>💎 Maks (hingga 4K)</span>
            </label>
          </div>
          <p class="mt-1 text-xs text-gray-700/80 dark:text-gray-300/80" x-show="mode==='max'">
            Menggunakan stream adaptive. <span x-text="ffmpeg ? 'FFmpeg terdeteksi: akan otomatis merge.' : 'FFmpeg tidak terdeteksi: unduhan bisa video-only.'"></span>
          </p>
        </div>

        <!-- Quality selector -->
        <div class="grid sm:grid-cols-2 gap-3 items-end">
          <div>
            <label class="block text-sm font-semibold mb-1">Kualitas</label>
            <select name="quality" x-model="quality"
                    class="w-full px-3 py-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white/80 dark:bg-gray-800/70 focus:outline-none focus:ring-2 focus:ring-red-400">
              <optgroup label="Mudah (progressive)">
              {% for r in progressive_res %}
                <option value="p:{{ r }}" {% if ('p:'+r)==quality %}selected{% endif %}>{{ r }} (video+audio)</option>
              {% endfor %}
              <option value="a:audio" {% if quality=='a:audio' %}selected{% endif %}>Audio saja</option>
              </optgroup>
              {% if adaptive_res %}
              <optgroup label="Maks (adaptive)">
              {% for r in adaptive_res %}
                <option value="v:{{ r }}" {% if ('v:'+r)==quality %}selected{% endif %}>{{ r }} (hingga 4K)</option>
              {% endfor %}
              </optgroup>
              {% endif %}
            </select>
          </div>
          <button type="submit" :disabled="loading" class="w-full bg-red-500 hover:bg-red-600 disabled:opacity-60 disabled:cursor-not-allowed text-white px-4 py-3 rounded-xl font-semibold transition flex items-center justify-center gap-2 btn-trans">
            <svg x-show="loading" class="w-5 h-5 animate-spin" viewBox="0 0 24 24" fill="none"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path></svg>
            <span x-text="loading ? 'Memproses...' : 'Download'"></span>
          </button>
        </div>

        <!-- Live Preview -->
        <template x-if="videoId">
          <div class="rounded-xl overflow-hidden border border-gray-200 dark:border-gray-800 bg-gray-50/70 dark:bg-gray-800/70">
            <img :src="thumbnailUrl" class="w-full object-cover max-h-60" alt="Preview video" loading="lazy" decoding="async">
            <div class="p-3">
              <div class="text-xs text-gray-700/80 dark:text-gray-300/80">Preview</div>
              <div class="font-semibold truncate" x-text="serverTitle || 'Judul akan muncul setelah diproses'"></div>
              <div class="mt-1 flex flex-wrap gap-2 text-[11px]">
                <span class="px-2 py-0.5 rounded-full bg-gray-200/70 dark:bg-gray-700/70" x-text="mode==='easy' ? 'Mudah' : 'Maks'"></span>
                <span class="px-2 py-0.5 rounded-full bg-gray-200/70 dark:bg-gray-700/70" x-text="qualityLabel"></span>
              </div>
            </div>
          </div>
        </template>

        <!-- Server messages -->
        {% if error %}
        <div class="p-3 rounded-lg bg-red-100/90 text-red-900 border border-red-200">{{ error }}</div>
        {% endif %}

        {% if file_path %}
        <div class="p-3 rounded-lg bg-green-100/90 text-green-900 border border-green-200">
          <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div>
              <p class="font-semibold">Berhasil diproses!</p>
              {% if yt_title %}<p class="text-sm opacity-80 truncate">{{ yt_title }}</p>{% endif %}
              {% if note %}<p class="text-xs mt-1 text-emerald-800/90">{{ note }}</p>{% endif %}
            </div>
            <a href="{{ file_path }}" class="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold btn-trans">⬇️ Unduh</a>
          </div>
        </div>
        {% endif %}
      </form>
    </div>

    <!-- Footer / GitHub -->
    <section class="mt-6 text-xs text-gray-800/90 dark:text-gray-300/90 text-center">
      <p>
        Semoga Bermanfaat, support
        <a href="https://teer.id/iben21" target="_blank" rel="noopener" class="underline underline-offset-4 hover:text-red-500">Trakteer</a>
      </p>
    </section>
  </main>

  <!-- Bottom Actions (mobile) -->
  <div class="fixed bottom-0 inset-x-0 z-40 md:hidden">
    <div class="mx-3 mb-3 rounded-2xl border border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-900/80 px-4 py-3 shadow-lg backdrop-blur surface">
      <div class="flex items-center justify-between">
        <div class="text-sm font-semibold">Aksi Cepat</div>
        <div class="text-[11px] px-2 py-0.5 rounded-full border border-gray-200 dark:border-gray-700" x-text="mode==='easy' ? 'Mudah' : 'Maks'"></div>
      </div>
      <div class="mt-2 grid grid-cols-3 gap-2 text-sm">
        <button @click="pasteUrl" class="px-3 py-2 rounded-xl bg-gray-100/70 dark:bg-gray-800/70 btn-trans">Tempel</button>
        <a href="#"
           @click.prevent="scrollToTop"
           class="px-3 py-2 rounded-xl bg-gray-100/70 dark:bg-gray-800/70 text-center btn-trans">Ke Atas</a>
        <button form="mainForm" @click="$root.querySelector('button[type=submit]').click()" class="px-3 py-2 rounded-xl bg-red-500 text-white btn-trans">Download</button>
      </div>
    </div>
  </div>

  <script>
    function app() {
      return {
        url: "{{ url or '' }}",
        quality: "{{ quality or 'p:720p' }}",
        mode: "{{ 'easy' if (quality or '').startswith('p:') or (quality=='a:audio') else 'max' }}",
        loading: false,
        darkMode: (() => {
          const saved = localStorage.getItem('theme');
          if (saved === 'dark') return true;
          if (saved === 'light') return false;
          return window.matchMedia('(prefers-color-scheme: dark)').matches;
        })(),
        serverTitle: {{ (yt_title|tojson) if yt_title else 'null' }},
        ffmpeg: {{ 'true' if ffmpeg_ok else 'false' }},
        get videoId() {
          const m = (this.url||'').match(/(?:v=|youtu\\.be\\/)([\\w-]{6,})/);
          return m ? m[1] : '';
        },
        get thumbnailUrl() {
          return this.videoId ? `https://img.youtube.com/vi/${this.videoId}/maxresdefault.jpg` : '';
        },
        get qualityLabel(){
          if(!this.quality) return '';
          if(this.quality.startsWith('p:')) return this.quality.slice(2) + ' (prog)';
          if(this.quality.startsWith('v:')) return this.quality.slice(2) + ' (adaptive)';
          if(this.quality==='a:audio') return 'Audio';
          return this.quality;
        },
        onUrlInput(){ this.serverTitle = null; },
        onSubmit(){ this.loading = true; setTimeout(()=>{},0); },
        pasteUrl(){
          if(navigator.clipboard){
            navigator.clipboard.readText().then(t=>{ if(t) this.url=t.trim(); });
          }
        },
        scrollToTop(){ window.scrollTo({top:0, behavior:'smooth'}); },
        toggleTheme(){
          this.darkMode = !this.darkMode;
          localStorage.setItem('theme', this.darkMode ? 'dark' : 'light');
          // sinkronkan meta theme-color agar status bar Android enak dilihat
          const meta = document.querySelector('meta[name="theme-color"]');
          if (meta) meta.setAttribute('content', this.darkMode ? '#111827' : '#ffffff');
        }
      }
    }

    // ==== Poké Ball bubbles generator (ringan) ====
    (function(){
      const layer = document.getElementById('bubbleLayer');
      if(!layer) return;
      const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      const count = prefersReduced ? 4 : 10 + Math.floor(Math.random()*5); // 10-14 bola
      for(let i=0;i<count;i++){
        const b = document.createElement('div');
        const size = (Math.random()*8 + 6) * (window.innerWidth<480?3.5:5); // responsive
        const left = Math.random()*100;
        const top  = Math.random()*100;
        const fy = (Math.random()*8 + 10).toFixed(1) + 's';
        const fx = (Math.random()*8 + 12).toFixed(1) + 's';
        const op = (Math.random()*0.35 + 0.2).toFixed(2); // 0.2 - 0.55
        b.className = 'poke floatY driftX';
        b.style.width = size+'px';
        b.style.height = size+'px';
        b.style.left = left+'%';
        b.style.top = top+'%';
        b.style.setProperty('--fy', fy);
        b.style.setProperty('--fx', fx);
        b.style.opacity = op;
        layer.appendChild(b);
      }
    })();

    // sinkronkan theme-color awal
    (function(){
      const saved = localStorage.getItem('theme');
      const isDark = saved ? saved==='dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
      const meta = document.querySelector('meta[name="theme-color"]');
      if (meta) meta.setAttribute('content', isDark ? '#111827' : '#ffffff');
    })();
  </script>
</body>
</html>
"""

# ---------- Routes ----------
@app.route("/", methods=["GET", "POST"])
def index():
    file_path = None
    error = None
    note = None
    url = ""
    quality = "p:720p"
    yt_title = None

    progressive_res = ["720p", "480p", "360p"]
    adaptive_res = []

    if request.method == "POST":
        url = clean_youtube_url(request.form.get("url", "").strip())
        quality = request.form.get("quality", "p:720p")

        if not valid_youtube_url(url):
            error = "URL YouTube tidak valid!"
        else:
            try:
                yt = YouTube(url)
                yt_title = yt.title

                # Kumpulkan progressive & adaptive
                prog_streams = yt.streams.filter(progressive=True, file_extension='mp4')
                progressive_res = sorted(
                    list({s.resolution for s in prog_streams if s.resolution}),
                    key=lambda x: int(x.replace('p','')), reverse=True
                )
                # Adaptive video-only (hingga 4K)
                adapt_streams = yt.streams.filter(adaptive=True, only_video=True)
                adaptive_res = sorted(
                    list({s.resolution for s in adapt_streams if s.resolution}),
                    key=lambda x: int(x.replace('p','')), reverse=True
                )

                # Eksekusi berdasarkan pilihan
                if quality.startswith("p:"):
                    res = quality.split(":",1)[1]
                    stream = prog_streams.filter(res=res).first()
                    if not stream:
                        stream = yt.streams.get_highest_resolution()
                    ext = ".mp4"
                    filename = safe_filename(yt_title) + ext
                    output = stream.download(output_path=DOWNLOAD_FOLDER, filename=filename)
                    file_name = os.path.basename(output)
                    file_path = f"/download/{file_name}"
                    note = "Mode Mudah (progressive): video+audio dalam satu file."

                elif quality == "a:audio":
                    a_stream = yt.streams.filter(only_audio=True).order_by("abr").desc().first()
                    if not a_stream:
                        raise RuntimeError("Stream audio tidak ditemukan.")
                    # simpan dengan ekstensi asli
                    ext = "." + (a_stream.mime_type.split("/")[-1] if a_stream.mime_type else "m4a")
                    filename = safe_filename(yt_title) + ext
                    output = a_stream.download(output_path=DOWNLOAD_FOLDER, filename=filename)
                    file_name = os.path.basename(output)
                    file_path = f"/download/{file_name}"
                    note = "Audio saja. Jika ingin MP3, aktifkan FFmpeg dan saya bisa konversi otomatis."

                elif quality.startswith("v:"):
                    # Adaptive: ambil video-only pada resolusi dipilih + audio terbaik
                    res = quality.split(":",1)[1]
                    v_stream = yt.streams.filter(adaptive=True, only_video=True, res=res).first()
                    if not v_stream:
                        # fallback ke resolusi adaptif tertinggi
                        v_stream = yt.streams.filter(adaptive=True, only_video=True).order_by("resolution").desc().first()
                        res = v_stream.resolution if v_stream else res
                    if not v_stream:
                        raise RuntimeError("Stream video adaptive tidak tersedia.")

                    a_stream = yt.streams.filter(only_audio=True).order_by("abr").desc().first()
                    if not a_stream:
                        raise RuntimeError("Stream audio tidak ditemukan.")

                    base = safe_filename(f"{yt_title} [{res}]")
                    # unduh ke temp lalu merge jika ffmpeg ada
                    with tempfile.TemporaryDirectory() as td:
                        v_ext = "." + (v_stream.mime_type.split("/")[-1] if v_stream.mime_type else "mp4")
                        a_ext = "." + (a_stream.mime_type.split("/")[-1] if a_stream.mime_type else "m4a")
                        v_tmp = os.path.join(td, "v"+v_ext)
                        a_tmp = os.path.join(td, "a"+a_ext)
                        v_stream.download(output_path=td, filename=os.path.basename(v_tmp))
                        a_stream.download(output_path=td, filename=os.path.basename(a_tmp))

                        if ffmpeg_available():
                            out_path = merge_av(v_tmp, a_tmp, base, v_stream.mime_type, a_stream.mime_type)
                            file_name = os.path.basename(out_path)
                            file_path = f"/download/{file_name}"
                            note = f"Mode Maks: {res} digabung otomatis dengan FFmpeg."
                        else:
                            # tanpa ffmpeg: simpan video-only agar tetap bisa diunduh cepat
                            out_path = os.path.join(DOWNLOAD_FOLDER, base + v_ext)
                            shutil.move(v_tmp, out_path)
                            file_name = os.path.basename(out_path)
                            file_path = f"/download/{file_name}"
                            note = f"Mode Maks: {res} (video-only). Install FFmpeg untuk menggabungkan audio."
                else:
                    raise RuntimeError("Pilihan kualitas tidak dikenal.")

            except Exception as e:
                error = f"Terjadi kesalahan: {e}"

    return render_template_string(
        html_form,
        file_path=file_path,
        error=error,
        note=note,
        url=url,
        quality=quality,
        yt_title=yt_title,
        progressive_res=progressive_res,
        adaptive_res=adaptive_res,
        ffmpeg_ok=ffmpeg_available(),
        download_folder=DOWNLOAD_FOLDER
    )

@app.route("/download/<filename>")
def download_file(filename):
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return "File tidak ditemukan", 404

if __name__ == "__main__":
    # akses jaringan lokal (dan mobile) mudah
    app.run(debug=True, host="0.0.0.0", port=5001)
