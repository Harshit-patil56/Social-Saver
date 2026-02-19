# Social Saver Bot — PRD
**Hackathon Project — v1.0 | 19 February 2026**

---

## 1. Problem Statement (From Hackathon Brief)

**Theme:** Turning Your Instagram Saves into a Knowledge Base.

You're scrolling through Instagram, you see a Reel with a great workout routine, a design tip, or a coding hack. You hit "Save," but you never look at it again. It gets buried in a hidden folder, lost forever.

**The Mission:** Build a WhatsApp Bot that fixes this.

The bot takes Instagram links (and other social links) you send it, automatically understands them, and saves them to a personal website.

---

## 2. What The System Must Do (From Problem Statement)

The user sends a link on WhatsApp → the system:

1. **Reads** the link
2. **Extracts** the caption or vibe
3. **Saves** it to a clean, searchable dashboard

---

## 3. Supported Inputs (From Problem Statement)

| # | Platform | What To Extract | Priority |
|---|---|---|---|
| 1 | **Instagram (Primary Focus)** | Caption, hashtags. Accept Reel or Post URL. | ⭐ Star |
| 2 | **Twitter/X Threads** | Tweet text | Secondary |
| 3 | **YouTube** | Video title, description | Secondary (if feasible) |
| 4 | **Blogs/Articles** | Title and main text | Secondary |

---

## 4. The Pipeline (From Problem Statement)

### A. Input — Link Ingestion via WhatsApp
- User sends a link (e.g. `https://instagram.com/p/xyz...`) to the bot's WhatsApp number.
- Bot replies: *"Got it! Saved to your 'Design' bucket."*

### B. Content Extraction (Scraping)
- **Instagram:** Extract caption and hashtags. Challenge: can you actually get them?
- **Twitter/X:** Extract tweet text.
- **Blogs:** Extract title and main text.

### C. AI Intelligence
- **Auto-Tag:** Categorize the content — e.g. "Fitness", "Coding", "Food", "Travel"
- **Summarize:** Write a 1-sentence summary of the caption/content.

### D. Dashboard (Web Page)
- **Cards layout** displaying saved content.
- **Visuals:** Show the Instagram link (embed it if you can!) and the AI summary.
- **Search:** Let the user type "Pasta" and find that recipe Reel they saved 2 weeks ago.

---

## 5. Technology Stack (From Problem Statement)

> *"You have total freedom. Use the tools you know best."*

| Layer | Options Given by Hackathon | Our Choice | Status |
|---|---|---|---|
| **Bot Interface** | Twilio Sandbox, Meta API, any Python library. *Telegram allowed as backup if WhatsApp is too hard.* | Twilio WhatsApp Sandbox | ❌ Need to set up |
| **Backend** | Python (Flask/FastAPI), Node.js, or No-Code tools | FastAPI (Python) | ✅ Python installed |
| **AI/LLM** | OpenAI API, Gemini, Claude, or open-source models | Google Gemini API (free tier) | ✅ API key available |
| **Database** | Firebase, MongoDB, SQLite, or Google Sheets | SQLite (zero setup, free) | ✅ Built into Python |
| **Scraping** | Not specified — open choice | httpx + BeautifulSoup4 | ✅ pip install |
| **Dashboard** | Not specified — "a simple web page" | HTML/CSS + Jinja2 templates | ✅ pip install |
| **Tunnel** | Not specified — needed for webhook | ngrok (free static dev domain) | ❌ Need to install |

**Total cost: $0** — Everything runs on localhost + ngrok.

---

## 6. Evaluation Criteria (From Problem Statement)

> *"We are judging your creativity and functionality."*

| Criteria | Weight | What Judges Check |
|---|---|---|
| **"WhatsApp → Insta" Flow** | **40%** | If I forward a Reel to your bot, does it actually end up on the website? Does the bot reply to me? |
| **AI Smarts** | **30%** | Did the AI correctly guess the category (e.g., tagging a workout video as "Fitness")? |
| **User Experience** | **20%** | Is the dashboard clean? Is it easy to find old links? |
| **"Wow" Factor** | **10%** | Did you embed the video player? Did you add a "Random Inspiration" button? |

---

## 7. Deliverables (From Problem Statement)

| # | Deliverable | Required |
|---|---|---|
| 1 | A working demo — screen recording of sending a link on WhatsApp and it appearing on the web | Yes |
| 2 | A link to your code repository | Yes |
| 3 | A simple diagram showing how you connected WhatsApp to your Database | Yes |

---

## 8. Technical Implementation Plan

### 8.1 WhatsApp Bot (Twilio Sandbox)
- Twilio Sandbox provides a free WhatsApp number for development.
- Incoming messages hit a webhook POST endpoint on our FastAPI server (exposed via ngrok).
- Bot detects if message contains a URL → routes to correct scraper.
- Bot replies with confirmation: *"Got it! Saved to your '[Category]' bucket."*
- If URL can't be fetched → reply with error message.

### 8.2 Content Extraction

**Instagram (Primary — 40% of score depends on this):**
- Attempt OG metadata extraction (`og:image`, `og:description`) via httpx — this is the most reliable method in 2026 without login.
- If caption is weak/empty (under 10 chars, emoji-only) → trigger MCQ fallback.
- Always extract `og:image` as thumbnail.

**Twitter/X:**
- Extract OG metadata from tweet URL via httpx.
- Alternative: Twikit Python library (free, no API key, uses internal API).
- If no media → show text-only card with platform icon.

**Blogs/Articles:**
- Extract page title, meta description, first 500 chars of body text using BeautifulSoup.

### 8.3 MCQ Fallback (When Scraping Fails)
When caption extraction yields weak results, bot sends:
```
Couldn't read this post. What's it about?
1. Fitness / Workout
2. Food / Recipe
3. Travel / Lifestyle
4. Tech / Coding
5. Other / Misc
Reply with a number (1–5).
```
- Pending link stored in-memory (or SQLite) keyed by WhatsApp number.
- Valid reply (1–5) → maps to category text → sent to Gemini for summary.
- Invalid reply → re-prompt once → discard if invalid again.

### 8.4 AI Processing (Google Gemini — Free Tier)
- Send extracted text to Gemini with prompt: *"Given this content, return JSON with `category` (Fitness/Food/Travel/Tech/Design/Finance/Entertainment/Other) and `summary` (one sentence, max 25 words)."*
- If Gemini fails or returns garbage → default: `category='Other'`, `summary='Saved link.'`
- Free tier: 15 requests/minute — more than enough for demo.

### 8.5 Database (SQLite)
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    whatsapp_number TEXT NOT NULL UNIQUE,  -- e.g. +91XXXXXXXXXX
    password_hash TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE saved_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    original_url TEXT NOT NULL,
    platform TEXT NOT NULL,  -- instagram, twitter, youtube, blog
    extracted_text TEXT,
    ai_summary TEXT,
    category TEXT,
    thumbnail_url TEXT,
    saved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```
- **User identity:** WhatsApp number + password. No email required.
- Bot identifies user by sender's WhatsApp number (Twilio provides this).
- Dashboard login: phone number + password.
- Duplicate URL check per user → reply "You've already saved this link!"

### 8.6 Dashboard (Simple Web Page)

**Authentication:**
- **Login page:** WhatsApp number + password. No email.
- **Registration page:** WhatsApp number + password. This number links bot messages to the user.
- Session managed via server-side session (Flask-style) — no JWT needed.

**Main dashboard (after login):**
- **Cards layout** — each saved link displayed as a card with:
  - Thumbnail (or platform icon if none)
  - Platform badge
  - Category tag
  - AI summary (1 line)
  - Link to original URL
- **Instagram embed** — use `<iframe src="https://www.instagram.com/p/{shortcode}/embed/">` for inline video/post display. No API key needed. This is the **Wow Factor**.
- **Search bar** — keyword search across extracted_text, ai_summary, category.
- **"Random Inspiration" button** — fetches one random saved link and highlights it. This is the other **Wow Factor**.
- **Dark mode** — default theme. Follows UI rules in Section 11.

**Stretch goal (if time allows):**
- "You may also like" — show 3 links from the same category at the bottom of the page.

### 8.7 ngrok Setup
- Claim free static dev domain (e.g. `your-name.ngrok-free.dev`).
- Set this as Twilio webhook URL once — no need to update between restarts.
- Free tier: 20,000 requests/month, 1 GB data — sufficient for hackathon.

---

## 9. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Instagram blocks scraping (403/bot detection) | Use OG metadata only (most reliable). MCQ fallback catches all failures. |
| Twitter/X restricts scraping | Use OG metadata. If blocked, save link with platform icon + no summary. |
| Gemini returns malformed response | try/except → default category='Other', summary='Saved link.' |
| ngrok URL changes | Use free static dev domain — persists across restarts. |
| In-memory session lost on restart | Store MCQ pending links in SQLite instead. |
| Instagram iframe embed doesn't load | Show thumbnail image as fallback + link to original post. |

---

## 10. Architecture (For Deliverable #3)

```
User's WhatsApp
      │
      ▼
Twilio Sandbox (Cloud)
      │
      ▼ POST /webhook/whatsapp
ngrok tunnel (free static domain)
      │
      ▼
FastAPI Backend (localhost)
      │
      ├──► Scraper (httpx + BeautifulSoup)
      │         │
      │         ▼
      ├──► Google Gemini API (free tier)
      │         │
      │         ▼
      ├──► SQLite Database (local file)
      │
      ▼
Jinja2 Dashboard (localhost)
    ├── Cards with AI summary
    ├── Instagram iframe embed
    ├── Search bar
    └── Random Inspiration button
```

---

## 11. Dashboard UI Design Rules

> Adapted from project UI rules. These are the constraints for building the dashboard.

### 11.1 Color System — 60-30-10 Rule

Only 3 color roles across the entire dashboard:

| Role | Usage | Guideline |
|---|---|---|
| **60% — Dominant (Neutral)** | Page background, card backgrounds | Neutral gray (`#f5f5f5` light / `#1a1a2e` dark). Never a bright color. |
| **30% — Secondary** | Card borders, section dividers, secondary text | Muted tones. Use borders or subtle backgrounds instead of colored fills where possible. |
| **10% — Accent** | Category tags, "Random Inspiration" button, active search state | One accent color only. Use sparingly. |

**Rules:**
- Icons do NOT get color unless they communicate status (e.g., platform badge).
- No pure white (`#fff`) or pure black (`#000`) — use off-white (`#fafafa`) and dark gray (`#1a1a1a`) instead.
- Category tags use muted, desaturated versions of the accent — not bright primary colors.

### 11.2 Dark Mode (If Implemented)

- Not a simple color inversion. Build a separate palette.
- Text: light gray (`#e0e0e0`), not pure white — reduces eye strain.
- Card backgrounds: slightly lighter than page background to create depth.
- Accent color stays the same in both modes.

### 11.3 Icons — Professional Library

- Use **Lucide** or **Phosphor** icon library — no emojis, no custom SVGs.
- Platform badges (Instagram, Twitter, Blog) use the respective platform's recognizable icon from the library.
- Keep icons monochrome (inherit text color) unless they are platform badges.

### 11.4 Card Layout Rules

Each saved link card must contain (in this order):

1. **Thumbnail** — `og:image` or platform icon fallback. No empty image placeholders.
2. **Platform badge** — small icon + label (e.g., Instagram, Twitter).
3. **Category tag** — pill/chip style, muted color.
4. **AI summary** — 1 line, truncated with ellipsis if overflow.
5. **Original link** — clickable, opens in new tab.
6. **Instagram embed** (if Instagram) — `<iframe>` below the card or in a modal on click.

**Card rules:**
- No unnecessary borders or shadows stacking. Pick one: subtle shadow OR thin border.
- Cards should have consistent spacing and sizing — use CSS Grid, not manual widths.
- Remove backgrounds entirely where possible for a cleaner look.

### 11.5 Semantic Colors

| Action/State | Color | Usage |
|---|---|---|
| Delete/Remove a saved link | Red (`#e53e3e`) | Delete button only — never for decorative purposes. |
| Success (link saved) | Green — only in WhatsApp reply text, not on dashboard | Bot reply confirmation. |
| Error/Warning | Amber/Orange | "Couldn't reach link" states. |
| Notification badge | Red dot | If implementing unread/new indicators. |

### 11.6 Element States

Every interactive element (buttons, search bar, cards) must have:

| State | Visual Change |
|---|---|
| **Default** | Base style |
| **Hover** | Slightly lighter background or subtle border change |
| **Active/Pressed** | Slightly darker than default |
| **Disabled** | Reduced opacity (`0.5`), `cursor: not-allowed` |

The "Random Inspiration" button and search bar are the primary interactive elements — these must have clear hover/active states.

### 11.7 Search Bar

- Full width at the top of the dashboard.
- Placeholder text: *"Search your saved links..."*
- No real-time search — results update on form submit (Enter key or search button).
- Empty results: show a centered message — *"Nothing found. Try a different keyword."*

### 11.8 Layout Principles

- **No sidebar.** Single-column or responsive grid (2-3 columns on desktop, 1 on mobile).
- **No repetitive layouts** — if all cards look identical with no visual hierarchy, add category grouping or a filter bar.
- **Hide advanced options** — the dashboard is simple: search bar + cards + random inspiration button. No settings panels, no menus.
- Cards should be the hero — the dashboard is a content wall, not a SaaS app.

---

*— End of PRD —*