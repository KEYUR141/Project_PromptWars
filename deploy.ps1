# ═══════════════════════════════════════════════════════════
# VenueIQ — Google Cloud Run Deployment Command
# ═══════════════════════════════════════════════════════════
# Run this from the Project_PromptWars directory after 
# replacing YOUR_GEMINI_KEY and YOUR_MAPS_KEY with real values.
# ═══════════════════════════════════════════════════════════

gcloud run deploy venueiq `
  --source . `
  --region us-central1 `
  --allow-unauthenticated `
  --project project-zoo-agent-489715 `
  --set-env-vars "GEMINI_API_KEY=YOUR_GEMINI_KEY,GOOGLE_MAPS_API_KEY=YOUR_MAPS_KEY,SECRET_KEY=venueiq-hackskill-2026-secret" `
  --memory 512Mi `
  --cpu 1 `
  --min-instances 0 `
  --max-instances 3 `
  --port 8080

# After deployment, gcloud will print your Cloud Run URL like:
# Service URL: https://venueiq-xxxxxx-uc.a.run.app
# That URL is your submission live preview link!
