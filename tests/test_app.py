"""
VenueIQ — Test Suite
=====================
Tests for all FastAPI endpoints. Uses httpx's TestClient (ASGI-compatible).
Run with: pytest tests/ -v
"""

import pytest
from httpx import AsyncClient, ASGITransport

# Import app after setting test env vars
import os
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("GOOGLE_MAPS_API_KEY", "test-maps-key")
os.environ.setdefault("SECRET_KEY", "test-secret")

from app import app, crowd_state, announcements, ZONE_DEFINITIONS


# ─────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────

@pytest.fixture
def transport():
    return ASGITransport(app=app)


# ─────────────────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint(transport):
    """Health endpoint returns 200 with expected fields."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["service"] == "venueiq"
    assert "timestamp" in body


# ─────────────────────────────────────────────────────────
# Page Routes
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_landing_page(transport):
    """Landing page returns 200 HTML."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    assert b"VenueIQ" in resp.content


@pytest.mark.asyncio
async def test_organizer_page(transport):
    """Organizer dashboard returns 200 HTML."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/organizer")
    assert resp.status_code == 200
    assert b"Dashboard" in resp.content


@pytest.mark.asyncio
async def test_attendee_page(transport):
    """Attendee guide returns 200 HTML."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/attendee")
    assert resp.status_code == 200
    assert b"VenueIQ" in resp.content


# ─────────────────────────────────────────────────────────
# Crowd Status API
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_crowd_status_structure(transport):
    """Crowd status returns all zones with required fields."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/crowd-status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["zones"]) == len(ZONE_DEFINITIONS)

    for zone in body["zones"]:
        assert "id" in zone
        assert "name" in zone
        assert "current" in zone
        assert "capacity" in zone
        assert "percentage" in zone
        assert "status" in zone
        assert 0 <= zone["percentage"] <= 100
        assert zone["status"] in ("quiet", "moderate", "busy", "critical")


@pytest.mark.asyncio
async def test_crowd_status_percentage_accuracy(transport):
    """Verify percentage is computed correctly."""
    # Force a known state
    crowd_state["main_hall"]["current"] = 250
    crowd_state["main_hall"]["capacity"] = 500

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/crowd-status")
    body = resp.json()
    hall = next(z for z in body["zones"] if z["id"] == "main_hall")
    assert hall["percentage"] == 50
    assert hall["status"] == "moderate"


# ─────────────────────────────────────────────────────────
# Announcements API
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_announcements(transport):
    """Announcements endpoint returns list."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/announcements")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["announcements"], list)


@pytest.mark.asyncio
async def test_post_announcement_valid(transport):
    """Valid announcement is created and returned."""
    payload = {"text": "Workshop B session starting now!", "type": "info"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/announce", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    assert "Workshop B" in body["announcement"]["text"]
    assert body["announcement"]["type"] == "info"


@pytest.mark.asyncio
async def test_post_announcement_too_short(transport):
    """Announcement shorter than 5 chars is rejected."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/announce", json={"text": "Hi"})
    assert resp.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_post_announcement_invalid_type(transport):
    """Invalid announcement type is rejected by Pydantic."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/announce", json={"text": "Valid text here", "type": "unknown"})
    assert resp.status_code == 422


# ─────────────────────────────────────────────────────────
# Crowd Update API
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_crowd_valid(transport):
    """Valid crowd update is applied and clamped to capacity."""
    payload = {"zone_id": "food_court", "count": 100}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/update-crowd", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["new_count"] == 100


@pytest.mark.asyncio
async def test_update_crowd_clamped_to_capacity(transport):
    """Count exceeding capacity is clamped to max."""
    cap = crowd_state["food_court"]["capacity"]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/update-crowd", json={"zone_id": "food_court", "count": cap + 9999})
    body = resp.json()
    assert body["new_count"] == cap


@pytest.mark.asyncio
async def test_update_crowd_invalid_zone(transport):
    """Invalid zone_id is rejected with validation error."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/update-crowd", json={"zone_id": "nonexistent", "count": 10})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_crowd_negative_clamped(transport):
    """Negative count is rejected (ge=0 constraint)."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/update-crowd", json={"zone_id": "main_hall", "count": -5})
    assert resp.status_code == 422


# ─────────────────────────────────────────────────────────
# Security Headers
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_security_headers_present(transport):
    """Security headers are set on every response."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("x-xss-protection") == "1; mode=block"


# ─────────────────────────────────────────────────────────
# AI Endpoints (mocked — no real API key in tests)
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_chat_no_api_key(transport):
    """Chat endpoint returns 503 when Gemini is not configured."""
    import app as app_module
    original = app_module.gemini_model
    app_module.gemini_model = None  # Simulate missing key

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/chat", json={"message": "Hello?"})
    assert resp.status_code == 503

    app_module.gemini_model = original  # Restore


@pytest.mark.asyncio
async def test_chat_empty_message_rejected(transport):
    """Empty message is rejected by Pydantic."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/chat", json={"message": ""})
    assert resp.status_code == 422


# ─────────────────────────────────────────────────────────
# Helper Functions Tests
# ─────────────────────────────────────────────────────────

def test_status_label_boundaries():
    """Verify status_label function at exact boundary conditions."""
    from app import status_label
    assert status_label(39) == "quiet"
    assert status_label(40) == "moderate"
    assert status_label(69) == "moderate"
    assert status_label(70) == "busy"
    assert status_label(89) == "busy"
    assert status_label(90) == "critical"
    assert status_label(100) == "critical"

def test_build_crowd_context():
    """Verify build_crowd_context generates expected string structure."""
    from app import build_crowd_context, EVENT_CONFIG
    context = build_crowd_context()
    assert isinstance(context, str)
    assert "LIVE CROWD STATUS" in context
    assert EVENT_CONFIG['name'] in context
    assert "Main Hall:" in context
    assert "%" in context


# ─────────────────────────────────────────────────────────
# Integration Chains
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_announce_chain(transport):
    """Verify posting an announcement makes it available in the get list."""
    payload = {"text": "Chain test announcement!", "type": "warning"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Post it
        post_resp = await client.post("/api/announce", json=payload)
        assert post_resp.status_code == 201
        
        # Get it
        get_resp = await client.get("/api/announcements")
        assert get_resp.status_code == 200
        get_body = get_resp.json()
        
        # Verify it's in the list
        found = any(a["text"] == payload["text"] and a["type"] == payload["type"] 
                    for a in get_body["announcements"])
        assert found is True
