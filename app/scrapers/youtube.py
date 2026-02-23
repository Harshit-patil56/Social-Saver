import re
import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _extract_video_id(url: str) -> str | None:
    """
    Extract the YouTube video ID from any YouTube URL format:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/shorts/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    Returns None if no video ID found.
    """
    patterns = [
        r"(?:youtube\.com/watch\?.*v=)([a-zA-Z0-9_-]{11})",       # watch?v=
        r"(?:youtu\.be/)([a-zA-Z0-9_-]{11})",                      # youtu.be/
        r"(?:youtube\.com/shorts/)([a-zA-Z0-9_-]{11})",            # /shorts/
        r"(?:youtube\.com/embed/)([a-zA-Z0-9_-]{11})",             # /embed/
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


async def scrape_youtube(url: str) -> dict:
    """
    Extract title and thumbnail from any YouTube URL (watch, Shorts, youtu.be).

    Strategy:
    1. Extract video ID from URL.
    2. Thumbnail: always construct from ytimg.com CDN using video ID — this CDN
       is never blocked regardless of where the server runs (Render, local, etc.).
    3. Title: try YouTube oEmbed API with watch?v=VIDEO_ID — requires no API key,
       works from any IP. Returns 403 only if the video has embedding disabled.
    4. If oEmbed fails (403, network error, etc.) — text stays empty → triggers
       MCQ category fallback in the webhook.
    """
    result = {"text": "", "thumbnail_url": None}

    video_id = _extract_video_id(url)

    if not video_id:
        print(f"[YOUTUBE] Could not extract video ID from: {url}")
        return result

    # ── Always set thumbnail from ytimg CDN (never blocked) ───────────────────
    result["thumbnail_url"] = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    print(f"[YOUTUBE] Thumbnail set from ytimg CDN: {video_id}")

    # ── oEmbed API for title (works from any IP, no auth required) ────────────
    watch_url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            resp = await client.get(
                f"https://www.youtube.com/oembed?url={watch_url}&format=json"
            )
            if resp.status_code == 200:
                data = resp.json()
                title = data.get("title", "").strip()
                author = data.get("author_name", "").strip()
                if title:
                    result["text"] = f"{title} — {author}" if author else title
                    print(f"[YOUTUBE] oEmbed title: {title[:80]}")
            else:
                print(f"[YOUTUBE] oEmbed status {resp.status_code} for {video_id}")
    except Exception as e:
        print(f"[YOUTUBE] oEmbed failed: {e}")

    return result
