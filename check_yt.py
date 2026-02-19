import sqlite3
conn = sqlite3.connect("social_saver.db")
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT id, platform, ai_summary, extracted_text FROM saved_links WHERE platform='youtube'").fetchall()
for r in rows:
    print(f"ID: {r['id']}")
    print(f"SUMMARY: {r['ai_summary']}")
    print(f"EXTRACTED: {r['extracted_text'][:300]}")
    print("---")
