import json
import bleach
import asyncio
from datetime import datetime
from fastapi import HTTPException

from config import logger, gemini_model, translate_client
from state import EVENT_CONFIG, crowd_state, ai_alerts_cache
from utils import build_crowd_context
from config import db

MAX_HISTORY_ITEMS = 6

async def process_chat(message: str, history: list[dict]) -> tuple[str, list[dict], dict]:
    """Process user message using Gemini with crowd context."""
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
        chat = gemini_model.start_chat(history=history[-MAX_HISTORY_ITEMS:])
        response = await asyncio.to_thread(chat.send_message, sys_prompt + "\n\nUser: " + message)
        
        reply = bleach.clean(response.text, tags=[], strip=True)
        new_history = [
            {"role": "user", "parts": message},
            {"role": "model", "parts": response.text}
        ]
        stats_snapshot = {zid: z["current"] for zid, z in crowd_state.items()}
        return reply, new_history, stats_snapshot
    except Exception as exc:
        logger.error("Gemini chat error: %s", exc, exc_info=True)
        raise HTTPException(status_code=503, detail="AI service temporarily unavailable. Please try again.")


async def generate_crowd_alerts() -> list[dict]:
    """Analyze crowd state and return list of actionable alerts."""
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

        # Update cache
        ai_alerts_cache.clear()
        ai_alerts_cache.extend(validated)

        # Update Firestore
        if db is not None:
            try:
                doc_ref = db.collection("ai_alerts").document("latest")
                doc_ref.set({"alerts": validated, "generated_at": datetime.now().isoformat()})
                logger.info("AI alerts persisted to Firestore | count=%d", len(validated))
            except Exception as fs_exc:
                logger.warning("Firestore write failed for AI alerts: %s", fs_exc)

        logger.info("AI crowd analysis complete | alerts=%d", len(validated))
        return validated
    except json.JSONDecodeError as exc:
        logger.error("JSON parse error from Gemini response: %s", exc)
        raise HTTPException(status_code=500, detail="AI response format error.")
    except Exception as exc:
        logger.error("Crowd analysis error: %s", exc, exc_info=True)
        raise HTTPException(status_code=503, detail="Analysis service temporarily unavailable.")


async def translate_announcement(text: str) -> dict:
    """Translates text into Hindi and Spanish if Google Cloud Translation is configured."""
    if not translate_client:
        return {"text_hi": None, "text_es": None}
    
    try:
        # Run synchronous translate API calls in a thread pool
        def do_translation():
            hi_res = translate_client.translate(text, target_language="hi")
            es_res = translate_client.translate(text, target_language="es")
            return {
                "text_hi": hi_res["translatedText"],
                "text_es": es_res["translatedText"]
            }
        
        translations = await asyncio.to_thread(do_translation)
        return translations
    except Exception as exc:
        logger.error("Translation API error: %s", exc, exc_info=True)
        return {"text_hi": None, "text_es": None}
