import json
import bleach
import asyncio
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from google.cloud import firestore

from config import db, gemini_model, MAPS_API_KEY, MAX_ANNOUNCEMENTS, logger
from state import EVENT_CONFIG, crowd_state, announcements, ai_alerts_cache
from schemas import ChatRequest, AnnouncementRequest, CrowdUpdateRequest
from utils import serialize_zones, build_crowd_context
from security import limiter, get_current_user, create_access_token

# ─────────────────────────────────────────────────────────
# PAGE ROUTER
# ─────────────────────────────────────────────────────────
page_router = APIRouter()

@page_router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request):
    """Landing page — choose Organizer or Attendee role."""
    try:
        return request.app.state.templates.TemplateResponse(request, "index.html", {
            "event": EVENT_CONFIG,
            "maps_key": MAPS_API_KEY,
        })
    except Exception as exc:
        logger.error("Failed to render index page: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Page temporarily unavailable.")

@page_router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request):
    """Login page for Organizer."""
    return request.app.state.templates.TemplateResponse(request, "login.html", {})

@page_router.post("/login", include_in_schema=False)
async def login(response: Response, username: str = Form(...), password: str = Form(...)):
    """Authenticate and set JWT cookie."""
    if username == "admin" and password == "venueiq2026":
        access_token = create_access_token(data={"sub": username})
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            max_age=7200,
            samesite="lax",
        )
        return {"success": True}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@page_router.post("/logout", include_in_schema=False)
async def logout(response: Response):
    """Clear JWT cookie."""
    response.delete_cookie("access_token")
    return RedirectResponse(url="/", status_code=303)

@page_router.get("/organizer", response_class=HTMLResponse, include_in_schema=False)
async def organizer_view(request: Request):
    """Organizer dashboard — protected by JWT."""
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login", status_code=303)
    try:
        get_current_user(token)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=303)

    try:
        zones = serialize_zones()
        logger.info("Organizer dashboard served | zones=%d", len(zones))
        return request.app.state.templates.TemplateResponse(request, "organizer.html", {
            "event": EVENT_CONFIG,
            "zones": zones,
            "maps_key": MAPS_API_KEY,
        })
    except Exception as exc:
        logger.error("Failed to render organizer dashboard: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Dashboard temporarily unavailable.")

@page_router.get("/attendee", response_class=HTMLResponse, include_in_schema=False)
async def attendee_view(request: Request):
    """Attendee smart guide — AI chat, zone status, venue map."""
    try:
        zones = serialize_zones()
        return request.app.state.templates.TemplateResponse(request, "attendee.html", {
            "event": EVENT_CONFIG,
            "zones": zones,
            "maps_key": MAPS_API_KEY,
        })
    except Exception as exc:
        logger.error("Failed to render attendee page: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Page temporarily unavailable.")


# ─────────────────────────────────────────────────────────
# API ROUTER
# ─────────────────────────────────────────────────────────
api_router = APIRouter(prefix="/api")

@api_router.get("/crowd-status", summary="Get live crowd status for all zones")
@limiter.limit("60/minute")
async def get_crowd_status(request: Request):
    """Returns real-time crowd occupancy data for all venue zones."""
    try:
        zones = serialize_zones()
        logger.debug("Crowd status API served | zones=%d", len(zones))
        return {
            "success": True,
            "zones": zones,
            "timestamp": datetime.now().isoformat(),
            "event": EVENT_CONFIG["name"],
        }
    except Exception as exc:
        logger.error("Failed to serve crowd status: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Could not retrieve crowd data.")

@api_router.get("/announcements", summary="Get event announcements")
@limiter.limit("30/minute")
async def get_announcements(request: Request):
    """Returns recent announcements from Firestore or memory."""
    try:
        if db is not None:
            docs = (
                db.collection("announcements")
                .order_by("id", direction=firestore.Query.DESCENDING)
                .limit(MAX_ANNOUNCEMENTS)
                .stream()
            )
            result = [doc.to_dict() for doc in docs]
            logger.debug("Announcements fetched from Firestore | count=%d", len(result))
        else:
            result = sorted(announcements, key=lambda x: x["id"], reverse=True)[:MAX_ANNOUNCEMENTS]
        return {"success": True, "announcements": result}
    except Exception as exc:
        logger.error("Failed to fetch announcements: %s", exc, exc_info=True)
        result = sorted(announcements, key=lambda x: x["id"], reverse=True)[:MAX_ANNOUNCEMENTS]
        return {"success": True, "announcements": result}

@api_router.post("/announce", status_code=201, summary="Post a new announcement (Organizer)", dependencies=[Depends(get_current_user)])
@limiter.limit("10/hour")
async def post_announcement(request: Request, body: AnnouncementRequest):
    """Broadcast a new announcement to all attendees. Protected by JWT."""
    try:
        new_item = {
            "id": len(announcements) + 1,
            "text": body.text,
            "timestamp": datetime.now().strftime("%H:%M"),
            "type": body.type,
        }
        announcements.append(new_item)

        if db is not None:
            try:
                db.collection("announcements").document(str(new_item["id"])).set(new_item)
                logger.info("Announcement persisted to Firestore | id=%s", new_item['id'])
            except Exception as fs_exc:
                logger.warning("Firestore write failed, in-memory only: %s", fs_exc)

        logger.info("Announcement posted | type=%s | text_len=%d", body.type, len(body.text))
        return {"success": True, "announcement": new_item}
    except Exception as exc:
        logger.error("Failed to post announcement: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Could not post announcement.")

@api_router.post("/update-crowd", summary="Manually update zone crowd count (Organizer)", dependencies=[Depends(get_current_user)])
@limiter.limit("30/hour")
async def update_crowd(request: Request, body: CrowdUpdateRequest):
    """Manually correct the crowd count. Protected by JWT."""
    try:
        cap = crowd_state[body.zone_id]["capacity"]
        new_count = max(0, min(cap, body.count))
        crowd_state[body.zone_id]["current"] = new_count
        logger.info("Crowd updated manually | zone=%s | count=%d", body.zone_id, new_count)
        return {"success": True, "zone_id": body.zone_id, "new_count": new_count}
    except KeyError as exc:
        logger.warning("update_crowd: zone not found: %s", exc)
        raise HTTPException(status_code=404, detail=f"Zone not found: {body.zone_id}")
    except Exception as exc:
        logger.error("Failed to update crowd count: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Could not update crowd count.")

@api_router.post("/chat", summary="Attendee AI chat powered by Gemini")
@limiter.limit("20/hour")
async def chat_with_ai(request: Request, body: ChatRequest):
    """Gemini-powered chat context-aware of the crowd state."""
    if not gemini_model:
        raise HTTPException(status_code=503, detail="AI service not configured.")
    
    crowd_context = build_crowd_context()
    sys_prompt = f"""You are the VenueIQ Smart Guide for the {EVENT_CONFIG['name']} at {EVENT_CONFIG['venue']}.
Your goal is to help attendees navigate the venue and find sessions.
Keep responses concise (1-3 sentences). Use emojis. Be helpful and polite.

{crowd_context}

If asked about crowdedness, guide them to quieter zones.
"""
    try:
        chat = gemini_model.start_chat(history=body.history[-MAX_HISTORY_ITEMS:])
        response = await asyncio.to_thread(chat.send_message, sys_prompt + "\n\nUser: " + body.message)
        return {
            "success": True,
            "reply": bleach.clean(response.text, tags=[], strip=True),
            "history": [
                {"role": "user", "parts": body.message},
                {"role": "model", "parts": response.text}
            ],
            "stats_snapshot": {zid: z["current"] for zid, z in crowd_state.items()},
        }
    except Exception as exc:
        logger.error("Gemini chat error: %s", exc, exc_info=True)
        raise HTTPException(status_code=503, detail="AI service temporarily unavailable. Please try again.")

@api_router.post("/analyze-crowd", summary="Generate AI crowd management alerts (Organizer)", dependencies=[Depends(get_current_user)])
@limiter.limit("10/hour")
async def analyze_crowd(request: Request):
    """Trigger Gemini to analyze crowd state. Protected by JWT."""
    if not gemini_model:
        raise HTTPException(status_code=503, detail="AI service not configured.")

    crowd_context = build_crowd_context()
    prompt = f"""{crowd_context}

You are VenueIQ, an AI crowd management system. Analyze the data above and generate exactly 3 specific, actionable operational alerts for the event organizer.

Respond with ONLY a valid JSON array (no markdown, no extra text):
[
  {{"level": "critical|warning|info", "zone": "Zone Name", "message": "Specific action to take now", "icon": "single emoji"}},
  {{"level": "...", "zone": "...", "message": "...", "icon": "..."}},
  {{"level": "...", "zone": "...", "message": "...", "icon": "..."}}
]
"""
    try:
        response = await asyncio.to_thread(gemini_model.generate_content, prompt)
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        alerts = json.loads(raw)
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

        if db is not None:
            try:
                doc_ref = db.collection("ai_alerts").document("latest")
                doc_ref.set({"alerts": validated, "generated_at": datetime.now().isoformat()})
                logger.info("AI alerts persisted to Firestore | count=%d", len(validated))
            except Exception as fs_exc:
                logger.warning("Firestore write failed for AI alerts: %s", fs_exc)

        logger.info("AI crowd analysis complete | alerts=%d", len(validated))
        return {"success": True, "alerts": validated}
    except json.JSONDecodeError as exc:
        logger.error("JSON parse error from Gemini response: %s", exc)
        raise HTTPException(status_code=500, detail="AI response format error.")
    except Exception as exc:
        logger.error("Crowd analysis error: %s", exc, exc_info=True)
        raise HTTPException(status_code=503, detail="Analysis service temporarily unavailable.")

@api_router.get("/ai-alerts", summary="Get cached AI alerts")
@limiter.limit("60/minute")
async def get_ai_alerts(request: Request):
    """Returns generated AI alerts from Firestore or in-memory cache."""
    try:
        if db is not None:
            doc = db.collection("ai_alerts").document("latest").get()
            if doc.exists:
                data = doc.to_dict()
                return {"success": True, "alerts": data.get("alerts", [])}
        return {"success": True, "alerts": ai_alerts_cache}
    except Exception as exc:
        logger.warning("Failed to fetch AI alerts from Firestore, using cache: %s", exc)
        return {"success": True, "alerts": ai_alerts_cache}
