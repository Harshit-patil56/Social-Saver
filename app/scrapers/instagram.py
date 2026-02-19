import re
import httpx
from bs4 import BeautifulSoup

# Instagram and Facebook are the same company.
# Instagram MUST serve OG metadata to Facebook's own crawler so that
# WhatsApp / Facebook link previews work on every post.
# This is the same technique used by Slack, Telegram, and Discord.
_FB_HEADERS = {
    "User-Agent": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uagent.php)",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def extract_shortcode(url: str) -> str:
    """Extract the Instagram shortcode from a URL."""
    match = re.search(r"/(p|reel|reels)/([^/?]+)", url)
    return match.group(2) if match else ""


async def scrape_instagram(url: str) -> dict:
    """
    Strategy (in order — no Playwright, no browser):
    1. Instagram public oEmbed API  — returns caption + thumbnail, zero auth needed.
    2. facebookexternalhit OG meta  — Instagram must serve og:description to FB crawler.
    3. Empty result                 — triggers MCQ category fallback.
    """
    result = {"text": "", "thumbnail_url": None}

    async with httpx.AsyncClient(follow_redirects=True, timeout=12.0) as client:

        # ── 1. oEmbed API ──────────────────────────────────────────────────────
        try:
            oembed_url = f"https://api.instagram.com/oembed/?url={url}&omitscript=true"
            resp = await client.get(oembed_url, headers=_FB_HEADERS)
            if resp.status_code == 200:
                data = resp.json()
                caption = data.get("title", "").strip()
                thumb   = data.get("thumbnail_url", "")
                if caption and len(caption) > 5:
                    result["text"] = caption
                    print(f"[INSTAGRAM] oEmbed caption ({len(caption)} chars)")
                if thumb:
                    result["thumbnail_url"] = thumb
                    print("[INSTAGRAM] oEmbed thumbnail OK")
                if result["text"]:
                    return result
        except Exception as e:
            print(f"[INSTAGRAM] oEmbed failed: {e}")

        # ── 2. facebookexternalhit OG metadata ─────────────────────────────────
        try:
            resp = await client.get(url, headers=_FB_HEADERS)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")

                og_desc = soup.find("meta", property="og:description")
                if og_desc and og_desc.get("content") and len(og_desc["content"]) > 5:
                    result["text"] = og_desc["content"]
                    print(f"[INSTAGRAM] OG desc ({len(result['text'])} chars)")

                if not result["thumbnail_url"]:
                    og_img = soup.find("meta", property="og:image")
                    if og_img and og_img.get("content"):
                        result["thumbnail_url"] = og_img["content"]
                        print("[INSTAGRAM] OG thumbnail OK")

                if not result["text"]:
                    og_title = soup.find("meta", property="og:title")
                    if og_title and og_title.get("content"):
                        t = og_title["content"]
                        if "instagram" not in t.lower():
                            result["text"] = t
                            print(f"[INSTAGRAM] OG title fallback ({len(t)} chars)")
        except Exception as e:
            print(f"[INSTAGRAM] FB crawler fallback failed: {e}")

    print(
        f"[INSTAGRAM] Done — text_len={len(result['text'])}, "
        f"has_thumb={result['thumbnail_url'] is not None}"
    )
    return result
