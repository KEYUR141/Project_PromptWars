import os
import logging
import google.generativeai as genai
import google.cloud.logging as cloud_logging
from google.cloud import firestore
from google.cloud import translate_v2 as translate
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────
# LOGGING SETUP
# ─────────────────────────────────────────────────────────
try:
    _cloud_log_client = cloud_logging.Client()
    _cloud_log_client.setup_logging(log_level=logging.INFO)
    logger = logging.getLogger("venueiq")
    logger.info("Google Cloud Logging initialised")
except Exception:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger("venueiq")
    logger.info("Falling back to stdlib logging (not running on GCP)")

# ─────────────────────────────────────────────────────────
# ENVIRONMENT & CONSTANTS
# ─────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MAPS_API_KEY   = os.getenv("GOOGLE_MAPS_API_KEY", "")
SECRET_KEY     = os.getenv("SECRET_KEY", "")
if not SECRET_KEY:
    import sys
    logger.critical("SECRET_KEY is required but not set. Exiting.")
    sys.exit(1)

ORGANIZER_USERNAME = os.getenv("ORGANIZER_USERNAME", "admin")
ORGANIZER_PASSWORD = os.getenv("ORGANIZER_PASSWORD", "venueiq2026")

SIMULATION_INTERVAL_SECS: int   = 30
CROWD_DRIFT_FACTOR:       float = 0.15
CROWD_DELTA_RANGE:        int   = 20
INITIAL_FILL_FRACTION:    float = 0.50
MAX_ANNOUNCEMENTS:        int   = 10
MAX_AI_ALERTS:            int   = 3
MAX_HISTORY_ITEMS:        int   = 6

# ─────────────────────────────────────────────────────────
# GOOGLE SERVICES CLIENTS
# ─────────────────────────────────────────────────────────
gemini_model = None
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel("gemini-2.0-flash")
        logger.info("Gemini AI configured successfully")
    except Exception as exc:
        logger.error("Failed to configure Gemini: %s", exc)
else:
    logger.warning("GEMINI_API_KEY not set — AI features will be disabled")

db = None
try:
    db = firestore.Client()
    logger.info("Firestore client initialised")
except Exception as exc:
    logger.warning("Firestore unavailable (%s) — using in-memory store", exc)

translate_client = None
try:
    translate_client = translate.Client()
    logger.info("Cloud Translation client initialised successfully")
except Exception as exc:
    logger.warning("Translation unavailable (%s)", exc)

bq_client = None
try:
    bq_client = bigquery.Client()
    logger.info("BigQuery client initialised successfully")
except Exception as exc:
    logger.warning("BigQuery unavailable (%s) — analytics streaming disabled", exc)
