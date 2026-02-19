import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


async def scrape_blog(url: str) -> dict:
    """Extract title, meta description, and first 500 chars of body from a blog/article URL."""
    result = {"text": "", "thumbnail_url": None}

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            response = await client.get(url, headers=HEADERS)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        parts = []

        # Page title
        if soup.title and soup.title.string:
            parts.append(soup.title.string.strip())

        # Meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            parts.append(meta_desc["content"].strip())

        # First 500 chars of body text
        # Remove script and style tags first
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        body_text = soup.get_text(separator=" ", strip=True)
        if body_text:
            # Take first 500 chars of body that aren't already in title/description
            body_snippet = body_text[:500].strip()
            if body_snippet:
                parts.append(body_snippet)

        result["text"] = " | ".join(parts) if parts else ""

        # og:image as thumbnail
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            result["thumbnail_url"] = og_image["content"]

    except Exception:
        pass

    return result
