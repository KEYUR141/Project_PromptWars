import bleach
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
from state import ZONE_DEFINITIONS

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
# RESPONSE MODELS
# ─────────────────────────────────────────────────────────

class ZoneStateResponse(BaseModel):
    """Represents the current state of a single zone."""
    id: str
    name: str
    capacity: int
    description: str
    lat: float
    lng: float
    color: str
    current: int
    percentage: int
    status: str

class CrowdStatusResponse(BaseModel):
    """Response model for /api/crowd-status."""
    success: bool
    zones: List[ZoneStateResponse]
    timestamp: str
    event: str

class AnnouncementItem(BaseModel):
    id: int
    text: str
    timestamp: str
    type: str
    text_hi: Optional[str] = None
    text_es: Optional[str] = None

class AnnouncementsResponse(BaseModel):
    """Response model for /api/announcements."""
    success: bool
    announcements: List[AnnouncementItem]

class PostAnnouncementResponse(BaseModel):
    """Response model for posting an announcement."""
    success: bool
    announcement: AnnouncementItem

class UpdateCrowdResponse(BaseModel):
    success: bool
    zone_id: str
    new_count: int

class ChatMessagePart(BaseModel):
    role: str
    parts: str

class ChatResponseModel(BaseModel):
    success: bool
    reply: str
    history: List[ChatMessagePart]
    stats_snapshot: Dict[str, int]

class AIAlertItem(BaseModel):
    level: str
    zone: str
    message: str
    icon: str
    timestamp: str

class AIAlertsResponse(BaseModel):
    success: bool
    alerts: List[AIAlertItem]

