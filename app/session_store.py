# In-memory session store for MCQ fallback flow.
# Key: WhatsApp number (str), Value: dict with url, thumbnail_url, platform, mcq_opts, retries
# This resets on server restart — acceptable for hackathon demo.

pending_links: dict = {}

ALL_CATEGORIES = [
    "Fitness", "Coding", "Tech", "Food", "Travel",
    "Design", "Business", "Gaming", "Other",
]

# Top-6 category suggestions per platform — most likely first
_PLATFORM_HINTS: dict[str, list[str]] = {
    "instagram": ["Fitness", "Food", "Travel", "Design", "Gaming", "Other"],
    "youtube":   ["Gaming", "Tech", "Coding", "Fitness", "Business", "Other"],
    "twitter":   ["Tech", "Business", "Coding", "Gaming", "Design", "Other"],
    "blog":      ["Coding", "Tech", "Business", "Travel", "Design", "Other"],
}
_DEFAULT_HINTS = ["Gaming", "Fitness", "Food", "Tech", "Coding", "Other"]


def build_mcq(platform: str) -> tuple[str, dict[str, str]]:
    """
    Build a WhatsApp-friendly MCQ message and the options dict {digit: category}.
    Returns (message_text, options_map).
    Shows the 6 most likely categories for the given platform.
    """
    hints = _PLATFORM_HINTS.get(platform, _DEFAULT_HINTS)
    opts: dict[str, str] = {}
    lines = ["Couldn't read this post automatically. What's it about?"]
    for i, cat in enumerate(hints, start=1):
        opts[str(i)] = cat
        lines.append(f"{i}. {cat}")
    lines.append(f"\nReply with a number (1\u2013{len(hints)}).")
    return "\n".join(lines), opts


def store_pending(whatsapp_number: str, url: str, thumbnail_url: str | None, platform: str):
    """Store a pending link while waiting for MCQ reply."""
    mcq_msg, mcq_opts = build_mcq(platform)
    pending_links[whatsapp_number] = {
        "url": url,
        "thumbnail_url": thumbnail_url,
        "platform": platform,
        "mcq_opts": mcq_opts,   # {digit: category_name}
        "mcq_msg": mcq_msg,
        "retries": 0,
    }


def get_pending(whatsapp_number: str) -> dict | None:
    return pending_links.get(whatsapp_number)


def get_mcq_message(whatsapp_number: str) -> str:
    """Return the MCQ message for a pending link."""
    pending = pending_links.get(whatsapp_number)
    return pending["mcq_msg"] if pending else ""


def resolve_pending(whatsapp_number: str) -> dict | None:
    return pending_links.pop(whatsapp_number, None)


def increment_retry(whatsapp_number: str):
    if whatsapp_number in pending_links:
        pending_links[whatsapp_number]["retries"] += 1


def is_weak_text(text: str) -> bool:
    """Check if extracted text is too weak to send to Gemini."""
    if not text:
        return True
    clean = text.strip()
    if len(clean) < 10:
        return True
    alpha_chars = sum(1 for c in clean if c.isalpha())
    if alpha_chars < 5:
        return True
    return False
