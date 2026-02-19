from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.database import get_db
from app.routes.auth import get_current_user
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
templates = Jinja2Templates(directory="app/templates")


class ChatMessage(BaseModel):
    message: str


def _session_key(user_id: int) -> str:
    """Unique key for the in-memory MCQ session store, separate from WhatsApp keys."""
    return f"chat:{user_id}"


@router.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("chat.html", {"request": request, "user": user})


@router.post("/chat/send")
async def chat_send(request: Request, body: ChatMessage):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    key = _session_key(user["id"])
    incoming = body.message.strip()

    conn = get_db()

    # ── MCQ reply flow ──────────────────────────────────────────────
    pending = get_pending(key)
    if pending:
        mcq_opts = pending.get("mcq_opts", {})
        if incoming in mcq_opts:
            pending_data = resolve_pending(key)
            category = mcq_opts[incoming]
            conn.execute(
                """INSERT INTO saved_links
                   (user_id, original_url, platform, extracted_text, ai_summary, category, thumbnail_url, tags)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    user["id"],
                    pending_data["url"],
                    pending_data["platform"],
                    category,
                    f"User-categorized as {category}.",
                    category,
                    pending_data["thumbnail_url"],
                    category.lower(),
                ),
            )
            conn.commit()
            conn.close()
            return JSONResponse({
                "reply": f"✅ Saved to your *{category}* collection!",
                "mcq_options": None,
                "saved": True,
                "category": category,
                "platform": pending_data["platform"],
            })
        else:
            if pending["retries"] < 1:
                increment_retry(key)
                n = len(mcq_opts)
                opts_list = [{"key": k, "label": v} for k, v in mcq_opts.items()]
                conn.close()
                return JSONResponse({
                    "reply": f"Please pick one of the options below (1–{n}).",
                    "mcq_options": opts_list,
                    "saved": False,
                })
            else:
                resolve_pending(key)
                conn.close()
                return JSONResponse({
                    "reply": "❌ Couldn't save that one. Try sending the link again.",
                    "mcq_options": None,
                    "saved": False,
                })

    # ── New message — must contain a URL ────────────────────────────
    url = extract_url(incoming)
    if not url:
        conn.close()
        return JSONResponse({
            "reply": "Please send a valid social media or article link. 🔗",
            "mcq_options": None,
            "saved": False,
        })

    url = normalize_url(url)

    # Duplicate check
    existing = conn.execute(
        "SELECT id FROM saved_links WHERE user_id = ? AND original_url = ?",
        (user["id"], url),
    ).fetchone()
    if existing:
        conn.close()
        return JSONResponse({
            "reply": "You've already saved this link! 📌",
            "mcq_options": None,
            "saved": False,
        })

    # Platform detect
    platform = detect_platform(url)
    if not platform:
        conn.close()
        return JSONResponse({
            "reply": "Couldn't identify this link. Send an Instagram, Twitter, YouTube, or blog URL.",
            "mcq_options": None,
            "saved": False,
        })

    # Scrape
    scraped = await scrape_url(url, platform)

    # Weak text → MCQ fallback
    if is_weak_text(scraped.get("text", "")):
        store_pending(key, url, scraped.get("thumbnail_url"), platform)
        fresh_pending = get_pending(key)
        opts_list = [{"key": k, "label": v} for k, v in fresh_pending["mcq_opts"].items()]
        conn.close()
        return JSONResponse({
            "reply": "Couldn't read this post automatically. What's it about?",
            "mcq_options": opts_list,
            "saved": False,
        })

    # AI categorize
    ai_result = await categorize_and_summarize(scraped["text"])

    conn.execute(
        """INSERT INTO saved_links
           (user_id, original_url, platform, extracted_text, ai_summary, category, thumbnail_url, tags)
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

    return JSONResponse({
        "reply": f"✅ Saved to your *{ai_result['category']}* collection!",
        "summary": ai_result.get("summary", ""),
        "category": ai_result.get("category", ""),
        "tags": ai_result.get("tags", ""),
        "platform": platform,
        "mcq_options": None,
        "saved": True,
    })
