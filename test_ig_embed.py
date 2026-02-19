import httpx, re
from bs4 import BeautifulSoup

shortcode = "C8wCLtmNfjq"
EMBED_URL = f"https://www.instagram.com/p/{shortcode}/embed/captioned/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://example.com/",  # pretend we're an embedded page
}

r = httpx.get(EMBED_URL, headers=HEADERS, follow_redirects=True, timeout=15)
print("Status:", r.status_code)
print("URL:", r.url)
print("Length:", len(r.text))

soup = BeautifulSoup(r.text, "html.parser")

# Check for caption div
caption_div = soup.find("div", class_=re.compile("Caption|caption|CaptionText"))
print("\nCaption div:", caption_div.get_text()[:200] if caption_div else "NOT FOUND")

# Scan all text content in paragraphs / spans
print("\n--- All non-empty text nodes ---")
for tag in soup.find_all(["p", "span", "div"], string=True):
    t = tag.get_text(strip=True)
    if len(t) > 20 and "instagram" not in t.lower() and "cookie" not in t.lower():
        print(" ", repr(t[:150]))

print("\n--- HTML snippet (first 2000 chars) ---")
print(r.text[:2000])
