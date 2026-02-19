import re
from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl
from app.scrapers.instagram import scrape_instagram
from app.scrapers.twitter import scrape_twitter
from app.scrapers.youtube import scrape_youtube
from app.scrapers.blog import scrape_blog

# Query params to strip (tracking/analytics noise)
_STRIP_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "mc_eid", "ref", "igsh", "igshid",
    "s", "si",  # Twitter/X share params
}


def normalize_url(url: str) -> str:
    """Normalize a URL for reliable duplicate detection.
    Strips tracking params, trailing slashes, and lowercases scheme+host.
    """
    try:
        parsed = urlparse(url.strip())
        # Lowercase scheme and host
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        # Remove trailing slash from path
        path = parsed.path.rstrip("/") or "/"
        # Drop tracking query params, keep the rest sorted for consistency
        clean_params = sorted(
            (k, v) for k, v in parse_qsl(parsed.query)
            if k.lower() not in _STRIP_PARAMS
        )
        query = urlencode(clean_params)
        # Drop fragment entirely
        return urlunparse((scheme, netloc, path, "", query, ""))
    except Exception:
        return url.strip()


def detect_platform(url: str) -> str:
    """Detect the social media platform from a URL."""
    if re.search(r"(instagram\.com|instagr\.am)", url, re.IGNORECASE):
        return "instagram"
    elif re.search(r"(twitter\.com|x\.com)", url, re.IGNORECASE):
        return "twitter"
    elif re.search(r"(youtube\.com|youtu\.be)", url, re.IGNORECASE):
        return "youtube"
    elif re.search(r"https?://", url, re.IGNORECASE):
        return "blog"
    return ""


async def scrape_url(url: str, platform: str) -> dict:
    """Route to the correct scraper based on platform. Returns dict with text, thumbnail_url."""
    if platform == "instagram":
        return await scrape_instagram(url)
    elif platform == "twitter":
        return await scrape_twitter(url)
    elif platform == "youtube":
        return await scrape_youtube(url)
    elif platform == "blog":
        return await scrape_blog(url)
    return {"text": "", "thumbnail_url": None}


def extract_url(message: str) -> str:
    """Extract the first URL from a WhatsApp message text."""
    url_pattern = r"(https?://[^\s]+)"
    match = re.search(url_pattern, message)
    return match.group(1) if match else ""
