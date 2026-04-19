# VenueIQ — AI-Powered Crowd Intelligence for Physical Events

> **Hack2Skill PromptWars 2026 | Physical Event Experience Vertical**

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Google-Gemini%202.0-orange?logo=google)](https://ai.google.dev)
[![Cloud Run](https://img.shields.io/badge/Google-Cloud%20Run-blue?logo=googlecloud)](https://cloud.google.com/run)

---



---

## 🎯 Chosen Vertical: Physical Event Experience

VenueIQ addresses the three core challenges of large-scale physical events:

| Problem | VenueIQ Solution |
|---|---|
| **Crowd Management** | Real-time zone occupancy tracking + AI-generated operational alerts |
| **Waiting Times** | Live capacity bars + AI recommends least-crowded alternatives |
| **Real-time Coordination** | Dual-persona platform: Organizer dashboard + Attendee smart guide |

---

## 💡 Approach & Logic

### The Core Insight
Most event apps are **reactive** — they answer questions. VenueIQ is **proactive** — it thinks ahead.

### How AI Makes Decisions
Every Gemini API call is injected with the **live crowd state** of all venue zones. This means:

- When an attendee asks *"Where should I eat?"* — the AI knows Food Court A has a 40-min queue and Food Court B is quiet, and answers accordingly.
- When an organizer clicks **Analyze** — Gemini reads all zone percentages and generates specific operational commands (*"Open secondary gate — Entry Gate at 92%"*).

### Dual Persona Design
```
Organizer View                    Attendee View
──────────────                    ─────────────
• Live heatmap (Google Maps)      • AI chat (Gemini-powered)
• Zone capacity bars              • Quick prompt suggestions
• AI operational alerts           • Zone status cards
• Manual crowd count override     • Venue map navigation
• Broadcast announcements         • Live announcement ticker
```

---

## 🛠 How It Works

### Architecture
```
Browser ──→ FastAPI (Cloud Run) ──→ Gemini 2.0 Flash
                 │
                 ├── GET /          → Landing (role selector)
                 ├── GET /organizer → Organizer dashboard
                 ├── GET /attendee  → Attendee guide
                 ├── GET /api/crowd-status   → Live zone data
                 ├── POST /api/chat          → AI attendee chat
                 ├── POST /api/analyze-crowd → AI organizer alerts
                 └── POST /api/announce      → Broadcast message
```

### Crowd Simulation
An async background task (`asyncio`) simulates realistic crowd patterns:
- Entry gate peaks at 9–10 AM (event opening)
- Main Hall peaks at 10 AM–12 PM (keynote) and 2–4 PM (sessions)
- Food Court peaks at 1–2 PM (lunch)
- Networking Lounge peaks at 4–6 PM (post-sessions)

### Gemini Prompt Engineering
Each AI call receives a structured context payload:
```
LIVE CROWD STATUS:
  • Main Hall: 425/500 (85%) [BUSY]
  • Food Court: 270/300 (90%) [CRITICAL]
  ...
ROLE: attendee | organizer
RULES: [role-specific behaviour instructions]
```

This ensures responses are always grounded in current venue reality.

---

## 🔧 Setup & Running Locally

### Prerequisites
- Python 3.11+
- Gemini API key ([Get free key](https://aistudio.google.com/app/apikey))
- Google Maps API key (optional — map renders without it)

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/Keyur141/Project_PromptWars.git
cd Project_PromptWars

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 5. Run the app
uvicorn app:app --reload --port 8080

# Visit http://localhost:8080
```

### Run Tests
```bash
pytest tests/ -v
```

**Frontend Testing:** The frontend JavaScript layer is tested via manual QA. (Cypress/Playwright tests can be integrated here for E2E).

---

## 🐳 Docker & Google Cloud Run Deployment

### Build & Run Locally with Docker
```bash
docker build -t venueiq .
docker run -p 8080:8080 \
  -e GEMINI_API_KEY=your_key \
  -e GOOGLE_MAPS_API_KEY=your_maps_key \
  -e SECRET_KEY=your_secret \
  venueiq
```

### Deploy to Google Cloud Run
```bash
# 1. Authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 2. Enable required APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com

# 3. Deploy from source
gcloud run deploy venueiq \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your_key,GOOGLE_MAPS_API_KEY=your_maps_key,SECRET_KEY=your_secret
```

---

## 🔒 Security

| Measure | Implementation |
|---|---|
| Secret management | All API keys via environment variables — never in code |
| Input validation | Pydantic models with field validators on every endpoint |
| Input sanitisation | `bleach` strips HTML/script tags from all user input |
| Rate limiting | `slowapi` — 20 chat req/hour, 10 announce/hour per IP |
| Security headers | `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection` on all responses |
| Error handling | Structured JSON errors — no stack traces exposed to client |

---

## ♿ Accessibility

- **Skip link** — `Skip to main content` for keyboard/screen reader users
- **ARIA labels** — all interactive elements, live regions, and progress bars
- **`aria-live="polite"`** — chat responses and crowd updates announced to screen readers
- **Semantic HTML** — `<nav>`, `<main>`, `<section>`, `role="list"`, `role="log"`
- **Keyboard navigation** — Enter to send chat, full tab order
- **Focus styles** — visible `:focus-visible` ring on all interactive elements
- **Responsive design** — mobile-first, works from 320px to 4K

---

## 🌐 Google Services Used

| Service | Role |
|---|---|
| **Gemini 2.0 Flash** | Core AI: crowd-aware attendee chat + organizer decision alerts |
| **Google Cloud Logging** | Structured production logs — auto-shipped to Cloud Logging on GCP |
| **Google Cloud Firestore** | Persistent storage: announcements + AI alerts survive restarts |
| **Google Maps Embed** | Interactive venue map on organizer and attendee views |
| **Google Fonts** | Outfit (headings) + Inter (body) — loaded from fonts.googleapis.com |
| **Google Material Symbols** | All UI icons via fonts.googleapis.com |
| **Google Cloud Run** | Production deployment (containerised, serverless, auto-scaling) |

---

## 📁 Project Structure

```
Project_PromptWars/
├── app.py                  # FastAPI app — routes, AI, crowd simulation
├── requirements.txt        # Python dependencies
├── Dockerfile              # Cloud Run container definition
├── pytest.ini              # Test configuration
├── .env.example            # Environment variable template
├── .gitignore
├── tests/
│   └── test_app.py         # 18 async pytest test cases
├── static/
│   ├── css/main.css        # Full design system (dark theme, glassmorphism)
│   └── js/
│       ├── app.js          # Shared utilities + crowd polling
│       ├── chat.js         # AI chat interface
│       ├── organizer.js    # Organizer dashboard logic
│       └── attendee.js     # Attendee announcement ticker
└── templates/
    ├── base.html           # Jinja2 base template
    ├── index.html          # Landing / role selector
    ├── organizer.html      # Organizer dashboard
    └── attendee.html       # Attendee smart guide
```

---

## 📌 Assumptions

1. **Crowd data** is simulated via a background async task — in production, this would integrate with IoT sensors or entry/exit scanners.
2. **Authentication** is not implemented — in production, organizers would log in separately from attendees.
3. **Single-instance state** — crowd data is in-memory; a production system would use a database like Firestore.
4. The mock event is **Hack2Skill PromptWars 2026** at India Expo Centre, Greater Noida.

---

## 📊 API Documentation

Interactive API docs available at `/docs` (Swagger UI) when the app is running.

---

*Built with ❤️ for Hack2Skill PromptWars 2026*