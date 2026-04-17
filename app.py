"""
VenueIQ — AI-Powered Real-Time Crowd Intelligence Platform
===========================================================
Hack2Skill PromptWars 2026 | Physical Event Experience Vertical

Author: VenueIQ Team
Version: 1.0.0

Architecture:
  - FastAPI backend with async endpoints
  - Gemini 2.0 Flash for context-aware AI decisions
  - In-memory crowd simulation with background updates
  - Jinja2 templates for server-side rendering
  - Deployed on Google Cloud Run via Docker
"""

import os
import json
import random
import asyncio
import bleach
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional

import google.generativeai as genai
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(24).hex())

# Configure Gemini
gemini_model = None
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-2.0-flash")
    logger.info("Gemini AI configured successfully")
else:
    logger.warning("GEMINI_API_KEY not set — AI features will be disabled")

# ─────────────────────────────────────────────────────────
# VENUE & EVENT DATA
# ─────────────────────────────────────────────────────────

EVENT_CONFIG = {
    "name": "Hack2Skill PromptWars 2026",
    "venue": "India Expo Centre, Greater Noida",
    "date": "April 19, 2026",
    "lat": 28.4744,
    "lng": 77.3914,
    "total_capacity": 1400,
}

# Zone definitions — single source of truth
ZONE_DEFINITIONS: dict[str, dict] = {
    "main_hall": {
        "id": "main_hall",
        "name": "Main Hall",
        "capacity": 500,
        "description": "Keynote presentations and main stage sessions",
        "lat": 28.4748, "lng": 77.3918,
        "color": "#6366f1",
    },
    "workshop_a": {
        "id": "workshop_a",
        "name": "Workshop Room A",
        "capacity": 150,
        "description": "Hands-on coding and development workshops",
        "lat": 28.4744, "lng": 77.3910,
        "color": "#10b981",
    },
    "workshop_b": {
        "id": "workshop_b",
        "name": "Workshop Room B",
        "capacity": 150,
        "description": "AI/ML and prompt engineering workshops",
        "lat": 28.4740, "lng": 77.3914,
        "color": "#06b6d4",
    },
    "food_court": {
        "id": "food_court",
        "name": "Food Court",
        "capacity": 300,
        "description": "Dining, refreshments and sponsor stalls",
        "lat": 28.4744, "lng": 77.3920,
        "color": "#f59e0b",
    },
    "networking_lounge": {
        "id": "networking_lounge",
        "name": "Networking Lounge",
        "capacity": 200,
        "description": "Networking zone and sponsor booths",
        "lat": 28.4748, "lng": 77.3910,
        "color": "#8b5cf6",
    },
    "entry_gate": {
        "id": "entry_gate",
        "name": "Entry Gate",
        "capacity": 100,
        "description": "Main entry, registration and badge pickup",
        "lat": 28.4740, "lng": 77.3918,
        "color": "#ef4444",
    },
}

# Mutable crowd state (shallow copy so we can update "current" independently)
crowd_state: dict[str, dict] = {
    zone_id: {**zone, "current": random.randint(20, int(zone["capacity"] * 0.5))}
    for zone_id, zone in ZONE_DEFINITIONS.items()
}

# In-memory stores
announcements: list[dict] = [
    {
        "id": 1,
        "text": "🎉 Welcome to Hack2Skill PromptWars 2026! Registration is open at the Entry Gate.",
        "timestamp": datetime.now().strftime("%H:%M"),
        "type": "info",
    }
]

ai_alerts_cache: list[dict] = []

# ─────────────────────────────────────────────────────────
# BACKGROUND CROWD SIMULATION
# ─────────────────────────────────────────────────────────

async def run_crowd_simulation() -> None:
    """
    Simulate realistic crowd fluctuations every 30 seconds.
    Models natural event patterns: busy entry at open, lunch peak at food court, etc.
    """
    while True:
        await asyncio.sleep(30)
        hour = datetime.now().hour

        targets = {
            "entry_gate":        0.8 if 9 <= hour <= 10 else 0.15,
            "main_hall":         0.85 if 10 <= hour <= 12 or 14 <= hour <= 16 else 0.4,
            "food_court":        0.9 if 13 <= hour <= 14 else 0.3,
            "workshop_a":        0.75 if 11 <= hour <= 13 else 0.45,
            "workshop_b":        0.7 if 14 <= hour <= 16 else 0.35,
            "networking_lounge": 0.6 if 16 <= hour <= 18 else 0.4,
        }

        for zone_id, zone in crowd_state.items():
            target = int(zone["capacity"] * targets.get(zone_id, 0.5))
            delta = random.randint(-20, 20)
            drift = int((target - zone["current"]) * 0.15)
            new_val = zone["current"] + delta + drift
            crowd_state[zone_id]["current"] = max(0, min(zone["capacity"], new_val))

        logger.info("Crowd simulation updated")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan: start background tasks on startup."""
    task = asyncio.create_task(run_crowd_simulation())
    logger.info("VenueIQ started — crowd simulation running")
    yield
    task.cancel()
    logger.info("VenueIQ shutting down")


# ─────────────────────────────────────────────────────────
# APP INITIALIZATION
# ─────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="VenueIQ",
    description="AI-Powered Real-Time Crowd Intelligence Platform for Physical Events",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


# ─────────────────────────────────────────────────────────
# PYDANTIC MODELS (Input Validation)
# ─────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500, description="User's question")
    history: list[dict] = Field(default=[], description="Conversation history (max 6 items)")

    @field_validator("message")
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        return bleach.clean(v, tags=[], strip=True).strip()


class AnnouncementRequest(BaseModel):
    text: str = Field(..., min_length=5, max_length=300, description="Announcement text")
    type: str = Field(default="info", pattern="^(info|warning|critical)$")

    @field_validator("text")
    @classmethod
    def sanitize_text(cls, v: str) -> str:
        return bleach.clean(v, tags=[], strip=True).strip()


class CrowdUpdateRequest(BaseModel):
    zone_id: str = Field(..., description="Zone identifier")
    count: int = Field(..., ge=0, description="New crowd count (non-negative)")

    @field_validator("zone_id")
    @classmethod
    def validate_zone(cls, v: str) -> str:
        clean = bleach.clean(v, tags=[], strip=True).strip()
        if clean not in ZONE_DEFINITIONS:
            raise ValueError(f"Invalid zone_id: {clean}")
        return clean


# ─────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────

def capacity_percent(zone: dict) -> int:
    """Calculate occupancy as an integer percentage."""
    return int((zone["current"] / zone["capacity"]) * 100)


def status_label(pct: int) -> str:
    """Return a human-readable crowd status label."""
    if pct >= 90:
        return "critical"
    if pct >= 70:
        return "busy"
    if pct >= 40:
        return "moderate"
    return "quiet"


def build_crowd_context() -> str:
    """Build a natural language crowd summary to inject into Gemini prompts."""
    lines = [f"LIVE CROWD STATUS — {EVENT_CONFIG['name']} ({datetime.now().strftime('%H:%M')} IST):"]
    for zone in crowd_state.values():
        pct = capacity_percent(zone)
        label = status_label(pct).upper()
        lines.append(f"  • {zone['name']}: {zone['current']}/{zone['capacity']} ({pct}%) [{label}]")
    return "\n".join(lines)


def serialize_zones() -> list[dict]:
    """Return all zones with computed fields for API/template consumption."""
    result = []
    for zone in crowd_state.values():
        pct = capacity_percent(zone)
        result.append({
            **zone,
            "percentage": pct,
            "status": status_label(pct),
        })
    return result


# ─────────────────────────────────────────────────────────
# SECURITY HEADERS MIDDLEWARE
# ─────────────────────────────────────────────────────────

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to every response."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# ─────────────────────────────────────────────────────────
# PAGE ROUTES
# ─────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request):
    """Landing page — choose Organizer or Attendee role."""
    return templates.TemplateResponse(request, "index.html", {
        "event": EVENT_CONFIG,
        "maps_key": MAPS_API_KEY,
    })


@app.get("/organizer", response_class=HTMLResponse, include_in_schema=False)
async def organizer_view(request: Request):
    """Organizer dashboard — live crowd heatmap, capacity bars, AI alerts."""
    return templates.TemplateResponse(request, "organizer.html", {
        "event": EVENT_CONFIG,
        "zones": serialize_zones(),
        "maps_key": MAPS_API_KEY,
    })


@app.get("/attendee", response_class=HTMLResponse, include_in_schema=False)
async def attendee_view(request: Request):
    """Attendee smart guide — AI chat, zone status, venue map."""
    return templates.TemplateResponse(request, "attendee.html", {
        "event": EVENT_CONFIG,
        "zones": serialize_zones(),
        "maps_key": MAPS_API_KEY,
    })


# ─────────────────────────────────────────────────────────
# DATA API ROUTES
# ─────────────────────────────────────────────────────────

@app.get("/api/crowd-status", summary="Get live crowd status for all zones")
@limiter.limit("60/minute")
async def get_crowd_status(request: Request):
    """
    Returns real-time crowd occupancy data for all venue zones.
    Polled by the frontend every 30 seconds for live updates.
    """
    return {
        "success": True,
        "zones": serialize_zones(),
        "timestamp": datetime.now().isoformat(),
        "event": EVENT_CONFIG["name"],
    }


@app.get("/api/announcements", summary="Get event announcements")
@limiter.limit("30/minute")
async def get_announcements(request: Request):
    """Returns the 10 most recent event announcements, newest first."""
    return {
        "success": True,
        "announcements": sorted(announcements, key=lambda x: x["id"], reverse=True)[:10],
    }


@app.post("/api/announce", status_code=201, summary="Post a new announcement (Organizer)")
@limiter.limit("10/hour")
async def post_announcement(request: Request, body: AnnouncementRequest):
    """
    Organizer action: broadcast a new announcement to all attendees.
    Rate limited to 10 per hour per IP.
    """
    new_item = {
        "id": len(announcements) + 1,
        "text": body.text,
        "timestamp": datetime.now().strftime("%H:%M"),
        "type": body.type,
    }
    announcements.append(new_item)
    return {"success": True, "announcement": new_item}


@app.post("/api/update-crowd", summary="Manually update zone crowd count (Organizer)")
@limiter.limit("30/hour")
async def update_crowd(request: Request, body: CrowdUpdateRequest):
    """
    Organizer action: manually correct the crowd count for a specific zone.
    Count is clamped to [0, zone capacity].
    """
    cap = crowd_state[body.zone_id]["capacity"]
    crowd_state[body.zone_id]["current"] = max(0, min(cap, body.count))
    return {
        "success": True,
        "zone_id": body.zone_id,
        "new_count": crowd_state[body.zone_id]["current"],
    }


# ─────────────────────────────────────────────────────────
# AI API ROUTES
# ─────────────────────────────────────────────────────────

@app.post("/api/chat", summary="Attendee AI chat powered by Gemini")
@limiter.limit("20/hour")
async def chat(request: Request, body: ChatRequest):
    """
    Context-aware conversational AI for attendees.
    Injects live crowd data into every Gemini request so answers
    reflect the current venue state (e.g., recommending less-crowded zones).
    """
    if not gemini_model:
        raise HTTPException(
            status_code=503,
            detail="AI service not configured. Please set GEMINI_API_KEY in environment.",
        )

    crowd_context = build_crowd_context()

    system_prompt = f"""You are VenueIQ, the official AI assistant for {EVENT_CONFIG['name']} \
at {EVENT_CONFIG['venue']}.

{crowd_context}

VENUE ZONES:
- Main Hall (Cap: 500): Keynote and main stage sessions
- Workshop Room A (Cap: 150): Hands-on coding workshops
- Workshop Room B (Cap: 150): AI/ML and prompt engineering workshops
- Food Court (Cap: 300): Dining and refreshments
- Networking Lounge (Cap: 200): Networking and sponsor booths
- Entry Gate (Cap: 100): Registration and badge pickup

ROLE: Friendly attendee assistant
RULES:
1. Always factor in the LIVE crowd data above when answering
2. Suggest less-crowded alternatives when a zone is busy (>70%)
3. Warn clearly if a zone is CRITICAL (>90%)
4. Keep answers to 2-4 sentences — be concise and warm
5. Use 1-2 relevant emojis per response
6. If asked about non-event topics, politely redirect to event help"""

    # Build safe conversation history (last 3 exchanges)
    safe_history = []
    for item in body.history[-6:]:
        if isinstance(item, dict) and item.get("role") in ("user", "model"):
            content = bleach.clean(str(item.get("content", "")), tags=[], strip=True)[:500]
            safe_history.append({"role": item["role"], "parts": [content]})

    try:
        chat_session = gemini_model.start_chat(history=safe_history)
        full_message = f"{system_prompt}\n\nATTENDEE: {body.message}"
        response = await asyncio.to_thread(chat_session.send_message, full_message)

        return {
            "success": True,
            "response": response.text,
            "crowd_snapshot": {
                zid: {
                    "pct": capacity_percent(z),
                    "status": status_label(capacity_percent(z)),
                }
                for zid, z in crowd_state.items()
            },
        }

    except Exception as e:
        logger.error(f"Gemini chat error: {e}")
        raise HTTPException(status_code=503, detail="AI service temporarily unavailable. Please try again.")


@app.post("/api/analyze-crowd", summary="Generate AI crowd management alerts (Organizer)")
@limiter.limit("10/hour")
async def analyze_crowd(request: Request):
    """
    Organizer action: trigger Gemini to analyze current crowd state and
    generate 3 specific, actionable operational alerts.
    Response is cached and served to the organizer dashboard.
    """
    if not gemini_model:
        raise HTTPException(
            status_code=503,
            detail="AI service not configured. Please set GEMINI_API_KEY in environment.",
        )

    crowd_context = build_crowd_context()

    prompt = f"""{crowd_context}

You are VenueIQ, an AI crowd management system. Analyze the data above and generate \
exactly 3 specific, actionable operational alerts for the event organizer.

Respond with ONLY a valid JSON array (no markdown, no extra text):
[
  {{"level": "critical|warning|info", "zone": "Zone Name", "message": "Specific action to take now", "icon": "single emoji"}},
  {{"level": "...", "zone": "...", "message": "...", "icon": "..."}},
  {{"level": "...", "zone": "...", "message": "...", "icon": "..."}}
]

Prioritize: safety first, then crowd flow, then attendee experience."""

    try:
        response = await asyncio.to_thread(gemini_model.generate_content, prompt)
        raw = response.text.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        alerts: list[dict] = json.loads(raw)
        validated = []
        for alert in alerts[:3]:
            if isinstance(alert, dict) and "message" in alert:
                validated.append({
                    "level": alert.get("level", "info"),
                    "zone": bleach.clean(str(alert.get("zone", "")), tags=[], strip=True),
                    "message": bleach.clean(str(alert.get("message", "")), tags=[], strip=True),
                    "icon": alert.get("icon", "ℹ️"),
                    "timestamp": datetime.now().strftime("%H:%M"),
                })

        ai_alerts_cache.clear()
        ai_alerts_cache.extend(validated)

        return {"success": True, "alerts": validated}

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error from Gemini: {e}")
        raise HTTPException(status_code=500, detail="AI response format error. Please try again.")
    except Exception as e:
        logger.error(f"Crowd analysis error: {e}")
        raise HTTPException(status_code=503, detail="Analysis service temporarily unavailable.")


@app.get("/api/ai-alerts", summary="Get cached AI alerts")
async def get_ai_alerts():
    """Returns the most recently generated AI alerts for the organizer dashboard."""
    return {"success": True, "alerts": ai_alerts_cache}


# ─────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────

@app.get("/health", summary="Health check for Cloud Run")
async def health():
    """
    Lightweight health check endpoint.
    Google Cloud Run uses this to verify service availability.
    """
    return {
        "status": "healthy",
        "service": "venueiq",
        "version": "1.0.0",
        "ai_configured": bool(GEMINI_API_KEY),
        "maps_configured": bool(MAPS_API_KEY),
        "timestamp": datetime.now().isoformat(),
    }
