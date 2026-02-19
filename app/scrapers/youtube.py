import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


async def scrape_youtube(url: str) -> dict:
    """Extract OG metadata from a YouTube URL. Returns dict with text and thumbnail_url."""
    result = {"text": "", "thumbnail_url": None}

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            response = await client.get(url, headers=HEADERS)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Extract og:title (video title)
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            result["text"] = og_title["content"]

        # Append og:description if available
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            desc = og_desc["content"]
            if result["text"]:
                result["text"] += " — " + desc
            else:
                result["text"] = desc

        # Extract og:image (video thumbnail)
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            result["thumbnail_url"] = og_image["content"]

    except Exception:
        pass

    return result
