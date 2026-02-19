from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeSerializer
from dotenv import load_dotenv
import bcrypt
import os

from app.database import get_db

load_dotenv()

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
serializer = URLSafeSerializer(os.getenv("SECRET_KEY", "fallback-secret-key"))


def get_current_user(request: Request) -> dict | None:
    """Get the current logged-in user from the session cookie."""
    session_token = request.cookies.get("session")
    if not session_token:
        return None
    try:
        user_id = serializer.loads(session_token)
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        if user:
            return dict(user)
        return None
    except Exception:
        return None


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, whatsapp_number: str = Form(...), password: str = Form(...)):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE whatsapp_number = ?", (whatsapp_number,)).fetchone()
    conn.close()

    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Phone number not found. Please register first."})

    if not bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Incorrect password."})

    # Create session
    token = serializer.dumps(user["id"])
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(key="session", value=token, httponly=True, max_age=86400)
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("register.html", {"request": request, "error": None})


@router.post("/register", response_class=HTMLResponse)
async def register_submit(request: Request, name: str = Form(...), whatsapp_number: str = Form(...), password: str = Form(...)):
    if not name or not whatsapp_number or not password:
        return templates.TemplateResponse("register.html", {"request": request, "error": "All fields are required."})

    name = name.strip()
    if len(name) < 2:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Name must be at least 2 characters."})

    if len(password) < 4:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Password must be at least 4 characters."})

    # Normalize phone number — ensure it starts with +
    if not whatsapp_number.startswith("+"):
        whatsapp_number = "+" + whatsapp_number

    conn = get_db()

    # Check if number already exists
    existing = conn.execute("SELECT id FROM users WHERE whatsapp_number = ?", (whatsapp_number,)).fetchone()
    if existing:
        conn.close()
        return templates.TemplateResponse("register.html", {"request": request, "error": "This phone number is already registered."})

    # Hash password and create user
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    conn.execute("INSERT INTO users (name, whatsapp_number, password_hash) VALUES (?, ?, ?)", (name, whatsapp_number, password_hash))
    conn.commit()

    # Get the new user ID
    user = conn.execute("SELECT id FROM users WHERE whatsapp_number = ?", (whatsapp_number,)).fetchone()
    conn.close()

    # Auto-login after registration
    token = serializer.dumps(user["id"])
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(key="session", value=token, httponly=True, max_age=86400)
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session")
    return response
