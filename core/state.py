import random
from datetime import datetime
from core.config import INITIAL_FILL_FRACTION

EVENT_CONFIG = {
    "name": "Hack2Skill PromptWars 2026",
    "venue": "India Expo Centre, Greater Noida",
    "date": "April 19, 2026",
    "lat": 28.4744,
    "lng": 77.3914,
    "total_capacity": 1400,
}

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

crowd_state: dict[str, dict] = {
    zone_id: {
        **zone,
        "current": random.randint(20, int(zone["capacity"] * INITIAL_FILL_FRACTION)),
    }
    for zone_id, zone in ZONE_DEFINITIONS.items()
}

announcements: list[dict] = [
    {
        "id": 1,
        "text": "🎉 Welcome to Hack2Skill PromptWars 2026! Registration is open at the Entry Gate.",
        "timestamp": datetime.now().strftime("%H:%M"),
        "type": "info",
    }
]

import threading
ai_alerts_cache: list[dict] = []
ai_alerts_lock = threading.Lock()
