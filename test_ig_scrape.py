import httpx, re, json

HEADERS = {'User-Agent': 'facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)'}
r = httpx.get('https://www.instagram.com/p/C8wCLtmNfjq/', headers=HEADERS, follow_redirects=True, timeout=15)
text = r.text

print("HTML length:", len(text))
print()

# Pattern 1: edge_media_to_caption
m = re.search(r'"edge_media_to_caption".*?"text":"(.*?)"', text, re.DOTALL)
print("edge_media_to_caption:", m.group(1)[:150] if m else "NOT FOUND")

# Pattern 2: accessibility_caption
m2 = re.search(r'"accessibility_caption":"(.*?)"', text)
print("accessibility_caption:", m2.group(1)[:150] if m2 else "NOT FOUND")

# Pattern 3: any og tags anywhere raw
og_matches = re.findall(r'og:[a-z:_]+.*?content="([^"]{10,})"', text)
print("og: tags found:", og_matches[:5] if og_matches else "NONE")

# Pattern 4: ld+json
ld_json_blocks = re.findall(r'application/ld\+json[^>]*>(.*?)</script>', text, re.DOTALL)
print("ld+json blocks:", len(ld_json_blocks))
for b in ld_json_blocks[:2]:
    try:
        d = json.loads(b)
        print("  ld+json keys:", list(d.keys())[:8])
        if "description" in d:
            print("  description:", str(d["description"])[:200])
    except Exception as e:
        print("  parse error:", e)

# Pattern 5: First 1200 chars of HTML after <head>
head_start = text.find('<head>')
if head_start != -1:
    print("\n--- HEAD snippet ---")
    print(text[head_start:head_start+1500])

# Check if redirected to login
print("\nContains 'Log in':", 'Log in' in text)
print("Contains 'login':", 'login' in text.lower()[:500])
