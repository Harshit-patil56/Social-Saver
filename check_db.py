import sqlite3

conn = sqlite3.connect("social_saver.db")
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT id, platform, category, ai_summary, extracted_text, thumbnail_url FROM saved_links ORDER BY id").fetchall()

for r in rows:
    print("=" * 60)
    print(f"ID: {r['id']}")
    print(f"Platform: {r['platform']}")
    print(f"Category: {r['category']}")
    print(f"Summary: {r['ai_summary']}")
    print(f"Text: {str(r['extracted_text'])[:100] if r['extracted_text'] else 'EMPTY'}")
    print(f"Thumb: {str(r['thumbnail_url'])[:80] if r['thumbnail_url'] else 'NONE'}")

conn.close()
