import json
import time
import httpx
import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv(override=True)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

PROMPT_TEMPLATE = """You are a content analyzer. Given the following text extracted from a social media post or article, return a JSON object with exactly three keys:
- "category": one of these values ONLY: Fitness, Coding, Tech, Food, Travel, Design, Business, Gaming, Other
- "summary": a one-sentence summary, maximum 25 words
- "tags": a JSON array of 3 to 5 lowercase keyword strings that best describe the content (e.g. ["yoga", "morning routine", "flexibility", "beginners"]). These are used for search — pick specific, meaningful words a user would search for.

Category guidance:
- Coding: programming tutorials, coding projects, developer tools, coding challenges
- Tech: smartphones, gadgets, hardware reviews, AI news, software news, science/technology
- Fitness: gym, workout, yoga, running, diet, health
- Food: recipes, restaurants, cooking, food reviews
- Travel: trips, destinations, hotels, itineraries
- Design: UI/UX, graphic design, art, aesthetics, brand/logo, animation
- Business: entrepreneurship, startups, marketing, finance, investing, productivity, career
- Gaming: video games, esports, gaming hardware, game reviews, game trailers
- Other: anything that does not fit above

Text to analyze:
{text}

Return ONLY the JSON object, no markdown, no code fences, no explanation."""

VALID_CATEGORIES = ["Fitness", "Coding", "Tech", "Food", "Travel", "Design", "Business", "Gaming", "Other"]

# Try these Gemini models in order
GEMINI_MODELS = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.0-flash-lite"]


def parse_ai_response(response_text: str) -> dict:
    """Parse AI response text into category + summary dict."""
    text = response_text.strip()

    # Remove markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]).strip()

    result = json.loads(text)

    category = result.get("category", "Other")
    if category not in VALID_CATEGORIES:
        category = "Other"

    summary = result.get("summary", "Saved link.")
    if not summary or len(summary) < 3:
        summary = "Saved link."

    # Parse tags — must be a list of strings
    raw_tags = result.get("tags", [])
    if isinstance(raw_tags, list):
        tags = ", ".join(str(t).lower().strip() for t in raw_tags if t)[:200]
    else:
        tags = ""

    return {"category": category, "summary": summary, "tags": tags}


async def try_gemini(text: str) -> dict | None:
    """Try Gemini API with multiple models. Returns result or None if all fail."""
    for model_name in GEMINI_MODELS:
        try:
            print(f"[AI] Trying Gemini model: {model_name}")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(PROMPT_TEMPLATE.format(text=text))
            print(f"[AI] Gemini response: {response.text[:200]}")
            return parse_ai_response(response.text)
        except Exception as e:
            error_msg = str(e)
            print(f"[AI] Gemini {model_name} failed: {error_msg[:150]}")
            if "quota" in error_msg.lower() or "429" in error_msg:
                time.sleep(0.5)
                continue
            else:
                break
    return None


async def try_groq(text: str) -> dict | None:
    """Try Groq API (free Llama). Returns result or None if fails."""
    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        print("[AI] No GROQ_API_KEY set, skipping Groq")
        return None

    try:
        print("[AI] Trying Groq (Llama)...")
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "user", "content": PROMPT_TEMPLATE.format(text=text)}],
                    "temperature": 0.3,
                    "max_tokens": 150,
                },
            )
            response.raise_for_status()
            data = response.json()
            reply = data["choices"][0]["message"]["content"]
            print(f"[AI] Groq response: {reply[:200]}")
            return parse_ai_response(reply)
    except Exception as e:
        print(f"[AI] Groq failed: {e}")
        return None


async def try_keyword_fallback(text: str) -> dict:
    """Simple keyword-based categorization when all AI APIs fail."""
    text_lower = text.lower()

    keyword_map = {
        "Fitness":  ["gym", "workout", "exercise", "fitness", "muscle", "weight", "yoga", "run",
                    "training", "health", "diet", "calories", "strength", "cardio", "stretching"],
        "Coding":   ["code", "coding", "programming", "developer", "python", "javascript", "html",
                    "css", "git", "sql", "api", "backend", "frontend", "algorithm", "debugging",
                    "tutorial", "project", "github", "deployment", "resume"],
        "Tech":     ["phone", "laptop", "computer", "software", "app", "tech", "ai", "robot",
                    "gadget", "device", "smartphone", "specs", "review", "unboxing", "hardware",
                    "processor", "camera", "battery", "science", "innovation"],
        "Food":     ["food", "recipe", "cook", "restaurant", "eat", "meal", "kitchen", "dish",
                    "chef", "bake", "taste", "cuisine", "flavor", "craving", "delicious"],
        "Travel":   ["travel", "trip", "flight", "hotel", "destination", "tour", "vacation",
                    "explore", "adventure", "beach", "city", "country", "passport", "itinerary"],
        "Design":   ["design", "ui", "ux", "figma", "color", "typography", "brand", "logo",
                    "creative", "art", "illustration", "aesthetic", "inspiration", "portfolio",
                    "visual", "animation", "graphic"],
        "Business": ["money", "invest", "stock", "finance", "bank", "crypto", "trading", "budget",
                    "income", "wealth", "market", "business", "startup", "productivity",
                    "entrepreneur", "marketing", "sales", "career", "hustle", "growth"],
        "Gaming":   ["game", "gaming", "gamer", "esports", "xbox", "playstation", "ps5", "ps4",
                    "nintendo", "pc gaming", "steam", "fortnite", "minecraft", "fps", "rpg",
                    "twitch", "console", "controller", "gameplay", "level"],
    }

    best_category = "Other"
    best_score = 0

    for category, keywords in keyword_map.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > best_score:
            best_score = score
            best_category = category

    # Generate a simple summary from the first sentence
    first_sentence = text.split(".")[0].strip()
    if len(first_sentence) > 80:
        first_sentence = first_sentence[:77] + "..."
    summary = first_sentence if first_sentence else "Saved link."

    print(f"[AI] Keyword fallback: category={best_category} (score={best_score})")
    return {"category": best_category, "summary": summary, "tags": best_category.lower()}


async def categorize_and_summarize(text: str) -> dict:
    """Categorize and summarize text. Tries Gemini → Groq → keyword fallback."""
    clean_text = text.strip()
    if len(clean_text) < 5:
        return {"category": "Other", "summary": "Saved link.", "tags": ""}

    # Try Gemini first
    result = await try_gemini(clean_text)
    if result:
        return result

    # Try Groq as backup
    result = await try_groq(clean_text)
    if result:
        return result

    # Last resort: keyword matching
    return await try_keyword_fallback(clean_text)
