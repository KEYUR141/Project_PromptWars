"""
VenueIQ — Test Suite
=====================
Tests for all FastAPI endpoints. Uses httpx's TestClient (ASGI-compatible).
Includes mock tests for external services to ensure 100% boundary coverage.
Run with: pytest tests/ -v
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport

import os
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("GOOGLE_MAPS_API_KEY", "test-maps-key")
os.environ.setdefault("SECRET_KEY", "test-secret")

from app import app
from state import crowd_state, announcements, ZONE_DEFINITIONS, EVENT_CONFIG
import config
from utils import status_label, build_crowd_context
from security import create_access_token


# ─────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────

@pytest.fixture
def transport():
    return ASGITransport(app=app)

@pytest.fixture
def auth_cookies():
    """Return cookies dictionary containing a valid JWT."""
    token = create_access_token({"sub": "admin"})
    return {"access_token": token}


# ─────────────────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert "timestamp" in body


# ─────────────────────────────────────────────────────────
# Auth & Page Routes
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_landing_page(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    assert b"VenueIQ" in resp.content

@pytest.mark.asyncio
async def test_organizer_page_unauthorized_redirects(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/organizer", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"

@pytest.mark.asyncio
async def test_organizer_page_authorized(transport, auth_cookies):
    async with AsyncClient(transport=transport, base_url="http://test", cookies=auth_cookies) as client:
        resp = await client.get("/organizer")
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_login_success(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/login", data={"username": "admin", "password": "venueiq2026"})
    assert resp.status_code == 200
    assert "access_token" in resp.cookies

@pytest.mark.asyncio
async def test_login_failure(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/login", data={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_attendee_page(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/attendee")
    assert resp.status_code == 200


# ─────────────────────────────────────────────────────────
# Crowd Status API
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_crowd_status_structure(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/crowd-status")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["zones"]) == len(ZONE_DEFINITIONS)


# ─────────────────────────────────────────────────────────
# Announcements API (With Firestore Mock)
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_announcements_with_mock_db(transport):
    """Test getting announcements via mocked firestore."""
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_doc = MagicMock()
    mock_doc.to_dict.return_value = {"id": 99, "text": "Mock DB announcement", "timestamp": "12:00", "type": "info"}
    mock_query.stream.return_value = [mock_doc]
    mock_db.collection().order_by().limit.return_value = mock_query

    with patch("routes.db", mock_db):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/announcements")
            
    assert resp.status_code == 200
    body = resp.json()
    assert body["announcements"][0]["id"] == 99

@pytest.mark.asyncio
async def test_post_announcement_unauthorized(transport):
    payload = {"text": "Workshop B session starting now!", "type": "info"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/announce", json=payload)
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_post_announcement_authorized(transport, auth_cookies):
    payload = {"text": "Workshop B session starting now!", "type": "info"}
    async with AsyncClient(transport=transport, base_url="http://test", cookies=auth_cookies) as client:
        resp = await client.post("/api/announce", json=payload)
    assert resp.status_code == 201


# ─────────────────────────────────────────────────────────
# Crowd Update API
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_crowd_unauthorized(transport):
    payload = {"zone_id": "food_court", "count": 100}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/update-crowd", json=payload)
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_update_crowd_authorized(transport, auth_cookies):
    payload = {"zone_id": "food_court", "count": 100}
    async with AsyncClient(transport=transport, base_url="http://test", cookies=auth_cookies) as client:
        resp = await client.post("/api/update-crowd", json=payload)
    assert resp.status_code == 200


# ─────────────────────────────────────────────────────────
# Security Headers
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_security_headers_present(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.headers.get("x-content-type-options") == "nosniff"


# ─────────────────────────────────────────────────────────
# Helper Functions Tests
# ─────────────────────────────────────────────────────────

def test_status_label_boundaries():
    assert status_label(39) == "quiet"
    assert status_label(70) == "busy"
    assert status_label(90) == "critical"

def test_build_crowd_context():
    context = build_crowd_context()
    assert "LIVE CROWD STATUS" in context


# ─────────────────────────────────────────────────────────
# AI Endpoints (With Gemini Mock)
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analyze_crowd_with_mock_gemini(transport, auth_cookies):
    mock_model = MagicMock()
    mock_response = MagicMock()
    # Provide a valid JSON string wrapped in markdown formatting (Gemini style)
    mock_response.text = '```json\n[{"level": "info", "zone": "Main Hall", "message": "Test action", "icon": "ℹ️"}]\n```'
    
    # We must patch asyncio.to_thread since routes.py calls `await asyncio.to_thread(gemini_model.generate_content, prompt)`
    async def mock_to_thread(func, *args, **kwargs):
        return mock_response
        
    with patch("services.ai_service.gemini_model", mock_model):
        with patch("asyncio.to_thread", mock_to_thread):
            async with AsyncClient(transport=transport, base_url="http://test", cookies=auth_cookies) as client:
                resp = await client.post("/api/analyze-crowd")
                
    assert resp.status_code == 200
    body = resp.json()
    assert body["alerts"][0]["zone"] == "Main Hall"

@pytest.mark.asyncio
async def test_post_announcement_translation(transport, auth_cookies):
    """Test that posting an announcement triggers translation and saves it."""
    payload = {"text": "Test translation", "type": "info"}
    
    async def mock_translate(*args, **kwargs):
        return {"text_hi": "परीक्षण", "text_es": "Prueba"}
        
    with patch("services.ai_service.translate_announcement", side_effect=mock_translate):
        async with AsyncClient(transport=transport, base_url="http://test", cookies=auth_cookies) as client:
            resp = await client.post("/api/announce", json=payload)
            
    assert resp.status_code == 201
    body = resp.json()
    assert body["announcement"]["text"] == "Test translation"
    assert body["announcement"]["text_hi"] == "परीक्षण"
    assert body["announcement"]["text_es"] == "Prueba"

