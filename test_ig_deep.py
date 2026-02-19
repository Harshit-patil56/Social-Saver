import httpx, re, json

# Get the main page HTML which is 766KB - Instagram embeds post data in it
HEADERS = {'User-Agent': 'facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)'}
r = httpx.get('https://www.instagram.com/p/C8wCLtmNfjq/', headers=HEADERS, follow_redirects=True, timeout=15)
text = r.text

print("HTML length:", len(text))

# Look for requireLazy / ServerJS or react initial state that contains post data
# Instagram embeds post data inside script tags as JSON
scripts = re.findall(r'<script[^>]*>(.*?)</script>', text, re.DOTALL)
print(f"Total script tags: {len(scripts)}")

for i, s in enumerate(scripts):
    s = s.strip()
    if '"caption"' in s and len(s) > 100:
        print(f"\nScript {i} has 'caption' ({len(s)} chars):")
        # Find caption text
        m = re.search(r'"caption"\s*:\s*\{[^}]*"text"\s*:\s*"([^"]{10,})"', s)
        if m:
            print("Caption:", m.group(1)[:300])
        else:
            # Show snippet around caption
            idx = s.find('"caption"')
            print(s[max(0,idx-20):idx+200])
        break

# Also check for og tags in raw HTML (case variants)
og_matches = re.findall(r'(?:property|name)=["\']og:(?:description|title)["\'][^>]+content=["\']([^"\']{10,})["\']', text, re.IGNORECASE)
print("\nOG matches (raw search):", og_matches[:3] if og_matches else "NONE")

# Check for PolarisContext / __additionalData
for keyword in ['__additionalData', 'PolarisContext', 'window.__data', 'xdt_api__v1__media__shortcode']:
    if keyword in text:
        idx = text.find(keyword)
        print(f"\nFound '{keyword}' at {idx}:")
        print(text[idx:idx+300])
