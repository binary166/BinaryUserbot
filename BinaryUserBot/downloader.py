"""
Скачивание видео с YouTube и TikTok через yt-dlp.
"""
import asyncio
import os
import tempfile
from utils import html


async def _yt_download(url: str, fmt_str: str) -> tuple[str | None, str | None]:
    try:
        import yt_dlp
    except ImportError:
        return None, "❌ pip install yt-dlp"

    tmp_dir  = tempfile.mkdtemp()
    out_tmpl = os.path.join(tmp_dir, "%(title)s.%(ext)s")
    ydl_opts = {
        "format": fmt_str,
        "outtmpl": out_tmpl,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    def _do():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info     = ydl.extract_info(url, download=True)
            title    = info.get("title", "video")
            filename = ydl.prepare_filename(info)
            if not os.path.exists(filename):
                base = filename.rsplit(".", 1)[0]
                for ext in ("mp4", "webm", "mkv", "m4v", "mov"):
                    c = f"{base}.{ext}"
                    if os.path.exists(c):
                        filename = c
                        break
                else:
                    files = os.listdir(tmp_dir)
                    if files:
                        filename = os.path.join(tmp_dir, files[0])
            return filename, title

    try:
        filename, title = await asyncio.get_event_loop().run_in_executor(None, _do)
        if os.path.exists(filename):
            return filename, title
        return None, "❌ Файл не найден"
    except Exception as e:
        return None, f"❌ Ошибка: <code>{html(str(e)[:200])}</code>"


async def download_youtube(url: str, quality: int = 720) -> tuple[str | None, str | None]:
    fmt = (
        f"best[height<={quality}][ext=mp4]/best[height<={quality}][ext=webm]"
        f"/best[height<={quality}]/best"
    )
    return await _yt_download(url, fmt)


async def download_tiktok(url: str) -> tuple[str | None, str | None]:
    return await _yt_download(url, "best[ext=mp4]/best[height<=720]/best")
