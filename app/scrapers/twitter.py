import re
import httpx
from bs4 import BeautifulSoup

# Twitter must serve OG metadata to the Facebook crawler because
# WhatsApp link previews of tweets have to work — this is the same
# technique used by Telegram, Slack, and every link-preview service.
_FB_HEADERS = {
    "User-Agent": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uagent.php)",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


async def scrape_twitter(url: str) -> dict:
    """
    Strategy (in order — no browser, no API key):
    1. Twitter/X public oEmbed API  — full tweet text in HTML, zero auth.
    2. facebookexternalhit OG meta  — Twitter serves og:description to FB crawler.
    3. Empty result                 — triggers MCQ fallback.
    """
    result = {"text": "", "thumbnail_url": None}

    # oEmbed only accepts twitter.com, not x.com
    oembed_url_input = url.replace("https://x.com/", "https://twitter.com/") \
                          .replace("http://x.com/", "https://twitter.com/")

    async with httpx.AsyncClient(follow_redirects=True, timeout=12.0) as client:

        # ── 1. oEmbed API ──────────────────────────────────────────────────────
        try:
            oembed_api = (
                f"https://publish.twitter.com/oembed"
                f"?url={oembed_url_input}&omit_script=true"
            )
            resp = await client.get(oembed_api, headers=_FB_HEADERS)
            if resp.status_code == 200:
                data = resp.json()
                html_content = data.get("html", "")
                if html_content:
                    soup = BeautifulSoup(html_content, "html.parser")
                    # Drop the footer <p> ("— Author (@handle) Date") — no lang attr
                    for tag in soup.find_all("p"):
                        if not tag.get("lang"):
                            tag.decompose()
                    text = soup.get_text(separator=" ", strip=True)
                    text = re.sub(r"pic\.twitter\.com\S+", "", text).strip()
                    if text and len(text) > 5:
                        result["text"] = text
                        print(f"[TWITTER] oEmbed text ({len(text)} chars)")
                        return result
        except Exception as e:
            print(f"[TWITTER] oEmbed failed: {e}")

        # ── 2. facebookexternalhit OG metadata ─────────────────────────────────
        try:
            resp = await client.get(url, headers=_FB_HEADERS)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")

                og_desc = soup.find("meta", property="og:description")
                if og_desc and og_desc.get("content") and len(og_desc["content"]) > 5:
                    result["text"] = og_desc["content"]
                    print(f"[TWITTER] OG desc ({len(result['text'])} chars)")

                og_img = soup.find("meta", property="og:image")
                if og_img and og_img.get("content"):
                    result["thumbnail_url"] = og_img["content"]
                    print("[TWITTER] OG thumbnail OK")

                if not result["text"]:
                    og_title = soup.find("meta", property="og:title")
                    if og_title and og_title.get("content"):
                        result["text"] = og_title["content"]
                        print(f"[TWITTER] OG title fallback ({len(result['text'])} chars)")
        except Exception as e:
            print(f"[TWITTER] FB crawler fallback failed: {e}")

    print(
        f"[TWITTER] Done — text_len={len(result['text'])}, "
        f"has_thumb={result['thumbnail_url'] is not None}"
    )
    return result
