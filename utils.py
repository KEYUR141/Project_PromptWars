from datetime import datetime
from state import crowd_state, EVENT_CONFIG

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
