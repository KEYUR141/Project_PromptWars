import asyncio
import random
import logging
from datetime import datetime
from state import crowd_state
from config import SIMULATION_INTERVAL_SECS, CROWD_DELTA_RANGE, CROWD_DRIFT_FACTOR

logger = logging.getLogger("venueiq")

async def run_crowd_simulation() -> None:
    """
    Simulate realistic crowd fluctuations every SIMULATION_INTERVAL_SECS seconds.
    Models natural event patterns: busy entry at open, lunch peak at food court, etc.
    """
    while True:
        try:
            await asyncio.sleep(SIMULATION_INTERVAL_SECS)
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
                target  = int(zone["capacity"] * targets.get(zone_id, 0.5))
                delta   = random.randint(-CROWD_DELTA_RANGE, CROWD_DELTA_RANGE)
                drift   = int((target - zone["current"]) * CROWD_DRIFT_FACTOR)
                new_val = zone["current"] + delta + drift
                crowd_state[zone_id]["current"] = max(0, min(zone["capacity"], new_val))

            snapshot = {zid: z["current"] for zid, z in crowd_state.items()}
            logger.info("Crowd simulation updated | totals=%s", snapshot)

        except asyncio.CancelledError:
            logger.info("Crowd simulation task cancelled — shutting down gracefully")
            raise
        except Exception as exc:
            logger.error("Crowd simulation error (task will continue): %s", exc, exc_info=True)
