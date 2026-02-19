"""Re-process existing saved links through the AI pipeline.

Usage:
    python reprocess.py          # Only fill in missing tags (safe, fast)
    python reprocess.py --all    # Re-run AI on every link (refreshes category + summary + tags)
"""
import asyncio
import sqlite3
import sys
from app.ai import categorize_and_summarize

DB_PATH = "social_saver.db"

ALL_MODE = "--all" in sys.argv


async def reprocess():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    if ALL_MODE:
        rows = conn.execute("SELECT id, extracted_text, category, ai_summary, tags FROM saved_links").fetchall()
        print(f"[--all] Re-processing ALL {len(rows)} links...\n")
    else:
        rows = conn.execute(
            "SELECT id, extracted_text, category, ai_summary, tags FROM saved_links "
            "WHERE tags IS NULL OR tags = ''"
        ).fetchall()
        print(f"Found {len(rows)} links missing tags (use --all to refresh everything)\n")

    if not rows:
        print("Nothing to do.")
        conn.close()
        return

    updated = 0
    skipped = 0

    for r in rows:
        link_id = r["id"]
        text = r["extracted_text"] or ""

        print(f"--- Link {link_id} ---")
        print(f"  Text snippet : {text[:80]}")
        print(f"  Old          : cat={r['category']}, tags={r['tags']!r}")

        if len(text.strip()) < 5:
            print("  Skipped: no usable text.\n")
            skipped += 1
            continue

        result = await categorize_and_summarize(text)
        print(f"  New          : cat={result['category']}, tags={result['tags']!r}\n")

        if ALL_MODE:
            conn.execute(
                "UPDATE saved_links SET category = ?, ai_summary = ?, tags = ? WHERE id = ?",
                (result["category"], result["summary"], result["tags"], link_id),
            )
        else:
            # Only patch missing tags — leave category/summary untouched
            conn.execute(
                "UPDATE saved_links SET tags = ? WHERE id = ?",
                (result["tags"], link_id),
            )
        updated += 1

    conn.commit()
    conn.close()
    print(f"\nDone. Updated: {updated}  |  Skipped (no text): {skipped}")


asyncio.run(reprocess())
