from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from app.database import init_db
from app.routes import auth, dashboard, webhook
from app.routes import chat

app = FastAPI(title="Social Saver Bot")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(webhook.router)
app.include_router(chat.router)


@app.on_event("startup")
def startup():
    """Initialize database on app startup."""
    init_db()


@app.get("/health")
async def health():
    """Lightweight health check for UptimeRobot pinging."""
    return JSONResponse({"status": "ok"})


@app.get("/")
async def root(request: Request):
    """Redirect to dashboard if logged in, else to login."""
    user = auth.get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return RedirectResponse(url="/login", status_code=302)
