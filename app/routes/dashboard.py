from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app.routes.auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


CATEGORIES = [
    "Fitness",
    "Coding",
    "Tech",
    "Food",
    "Travel",
    "Design",
    "Business",
    "Gaming",
    "Other",
]

# Columns searched and their relevance weights (higher = surfaces to top when matched)
_SEARCH_COLS = [
    ("tags",           8),   # hand-curated keywords — highest signal
    ("category",       4),   # exact semantic bucket
    ("platform",       3),   # lets "youtube" / "instagram" searches work
    ("ai_summary",     2),   # one-sentence AI description
    ("extracted_text", 1),   # raw scraped text — lowest weight, most noise
]


def _build_search_query(q: str, base_where: str, base_params: list) -> tuple[str, list]:
    """
    Build a relevance-ranked query.

    Each whitespace-separated token must match at least ONE searchable column (AND of ORs).
    Rows are scored by summing per-column weights for every matching token, then ordered
    score DESC, saved_at DESC — so the closest match always floats to the top.

    Returns (sql, params).
    """
    tokens = [t.strip().lower() for t in q.split() if t.strip()]
    if not tokens:
        sql = f"SELECT * FROM saved_links WHERE {base_where} ORDER BY saved_at DESC"
        return sql, base_params[:]

    filter_parts = []   # AND-joined, one clause per token
    filter_params = []

    score_parts = []    # summable CASE expressions for SELECT
    score_params = []   # params consumed by the SELECT score expression

    for token in tokens:
        term = f"%{token}%"
        # Filter: token must appear in at least one column
        col_checks = " OR ".join(f"LOWER({col}) LIKE ?" for col, _ in _SEARCH_COLS)
        filter_parts.append(f"({col_checks})")
        filter_params.extend([term] * len(_SEARCH_COLS))

        # Score: weighted CASE per column
        for col, weight in _SEARCH_COLS:
            score_parts.append(f"CASE WHEN LOWER({col}) LIKE ? THEN {weight} ELSE 0 END")
            score_params.append(term)

    score_expr = " + ".join(score_parts)
    full_where = f"{base_where} AND {' AND '.join(filter_parts)}"

    # Score params precede WHERE params because they appear earlier in the SQL
    all_params = score_params + base_params + filter_params

    sql = (
        f"SELECT *, ({score_expr}) AS _score "
        f"FROM saved_links "
        f"WHERE {full_where} "
        f"ORDER BY _score DESC, saved_at DESC"
    )
    return sql, all_params


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, q: str = "", cat: str = ""):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    conn = get_db()

    base_params: list = [user["id"]]
    base_where = "user_id = ?"

    if cat:
        base_where += " AND LOWER(category) = LOWER(?)"
        base_params.append(cat)

    if q:
        sql, params = _build_search_query(q, base_where, base_params)
    else:
        sql = f"SELECT * FROM saved_links WHERE {base_where} ORDER BY saved_at DESC"
        params = base_params

    links = conn.execute(sql, params).fetchall()
    conn.close()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "links": [dict(l) for l in links],
        "search_query": q,
        "active_category": cat,
        "categories": CATEGORIES,
    })


@router.get("/dashboard/random")
async def random_link(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not logged in"}, status_code=401)

    conn = get_db()
    link = conn.execute(
        "SELECT * FROM saved_links WHERE user_id = ? ORDER BY RANDOM() LIMIT 1",
        (user["id"],),
    ).fetchone()
    conn.close()

    if not link:
        return JSONResponse({"error": "No saved links yet"}, status_code=404)

    return JSONResponse(dict(link))


@router.delete("/links/{link_id}")
async def delete_link(request: Request, link_id: int):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not logged in"}, status_code=401)

    conn = get_db()
    # Only delete if the link belongs to this user
    conn.execute("DELETE FROM saved_links WHERE id = ? AND user_id = ?", (link_id, user["id"]))
    conn.commit()
    conn.close()

    return JSONResponse({"success": True})
