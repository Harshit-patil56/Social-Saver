import re
from fastapi import APIRouter, Request, Form
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse

from app.database import get_db
from app.scrapers import detect_platform, scrape_url, extract_url, normalize_url
from app.ai import categorize_and_summarize
from app.session_store import (
    get_pending,
    get_mcq_message,
    store_pending,
    resolve_pending,
    increment_retry,
    is_weak_text,
)

router = APIRouter()


def make_reply(message: str) -> str:
    """Create a TwiML response string."""
    resp = MessagingResponse()
    resp.message(message)
    return str(resp)


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """Handle incoming WhatsApp messages from Twilio."""
    form_data = await request.form()
    incoming_msg = form_data.get("Body", "").strip()
    sender = form_data.get("From", "")  # e.g., "whatsapp:+91XXXXXXXXXX"

    # Extract the phone number from Twilio format
    whatsapp_number = sender.replace("whatsapp:", "")

    print(f"[WEBHOOK] Message from {whatsapp_number}: {incoming_msg[:100]}")

    # Check if user exists in database
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE whatsapp_number = ?", (whatsapp_number,)).fetchone()

    if not user:
        conn.close()
        print(f"[WEBHOOK] User {whatsapp_number} not registered")
        return PlainTextResponse(
            make_reply("You're not registered yet! Please sign up on our website first, then send your link again."),
            media_type="text/xml",
        )

    # Check if this is an MCQ reply (user has a pending link)
    pending = get_pending(whatsapp_number)
    if pending:
        mcq_opts = pending.get("mcq_opts", {})
        if incoming_msg in mcq_opts:
            # Valid MCQ reply — resolve the pending link
            pending_data = resolve_pending(whatsapp_number)
            category = mcq_opts[incoming_msg]   # e.g. "Gaming"
            summary = f"User-categorized as {category}."

            print(f"[WEBHOOK] MCQ resolved: {category}")

            conn.execute(
                """INSERT INTO saved_links
                   (user_id, original_url, platform, extracted_text, ai_summary, category, thumbnail_url, tags)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    user["id"],
                    pending_data["url"],
                    pending_data["platform"],
                    category,
                    summary,
                    category,
                    pending_data["thumbnail_url"],
                    category.lower(),
                ),
            )
            conn.commit()
            conn.close()

            return PlainTextResponse(
                make_reply(f"Got it! Saved to your *{category}* collection. \u2705"),
                media_type="text/xml",
            )
        else:
            # Invalid MCQ reply — give one retry
            if pending["retries"] < 1:
                increment_retry(whatsapp_number)
                retry_msg = get_mcq_message(whatsapp_number)
                n = len(pending.get("mcq_opts", {}))
                conn.close()
                return PlainTextResponse(
                    make_reply(f"Please reply with a number 1\u2013{n}.\n\n{retry_msg}"),
                    media_type="text/xml",
                )
            else:
                resolve_pending(whatsapp_number)
                conn.close()
                return PlainTextResponse(
                    make_reply("Couldn't save this one. Please try sending the link again."),
                    media_type="text/xml",
                )

    # Not an MCQ reply — check for URL in message
    url = extract_url(incoming_msg)
    if not url:
        conn.close()
        return PlainTextResponse(
            make_reply("Please send a valid social media or article link. 🔗"),
            media_type="text/xml",
        )

    # Normalize URL to strip tracking params / trailing slashes
    url = normalize_url(url)

    # Check for duplicate URL
    existing = conn.execute(
        "SELECT id FROM saved_links WHERE user_id = ? AND original_url = ?",
        (user["id"], url),
    ).fetchone()
    if existing:
        conn.close()
        return PlainTextResponse(
            make_reply("You've already saved this link! 📌"),
            media_type="text/xml",
        )

    # Detect platform
    platform = detect_platform(url)
    if not platform:
        conn.close()
        return PlainTextResponse(
            make_reply("Couldn't identify this link. Please send an Instagram, Twitter, YouTube, or blog URL."),
            media_type="text/xml",
        )

    # Scrape the URL
    print(f"[WEBHOOK] Scraping {platform} URL: {url}")
    scraped = await scrape_url(url, platform)
    print(f"[WEBHOOK] Scraped text length: {len(scraped.get('text', ''))}, has thumbnail: {scraped.get('thumbnail_url') is not None}")

    # Check if text is weak — trigger MCQ fallback
    if is_weak_text(scraped.get("text", "")):
        print(f"[WEBHOOK] Weak text detected, triggering MCQ")
        store_pending(whatsapp_number, url, scraped.get("thumbnail_url"), platform)
        mcq_msg = get_mcq_message(whatsapp_number)
        conn.close()
        return PlainTextResponse(
            make_reply(mcq_msg),
            media_type="text/xml",
        )

    # Text is strong — send to Gemini
    print(f"[WEBHOOK] Sending to Gemini AI...")
    ai_result = await categorize_and_summarize(scraped["text"])
    print(f"[WEBHOOK] AI result: {ai_result}")

    # Save to database
    conn.execute(
        """INSERT INTO saved_links (user_id, original_url, platform, extracted_text, ai_summary, category, thumbnail_url, tags)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user["id"],
            url,
            platform,
            scraped["text"],
            ai_result["summary"],
            ai_result["category"],
            scraped.get("thumbnail_url"),
            ai_result.get("tags", ""),
        ),
    )
    conn.commit()
    conn.close()

    return PlainTextResponse(
        make_reply(f"Got it! Saved to your *{ai_result['category']}* collection. \u2705"),
        media_type="text/xml",
    )
