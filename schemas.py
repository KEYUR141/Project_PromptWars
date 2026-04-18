import bleach
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
