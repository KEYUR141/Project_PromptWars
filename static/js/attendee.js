/**
 * VenueIQ — attendee.js
 * Attendee page logic: announcement ticker and zone status live-refresh.
 */

'use strict';

let tickerAnnouncements = [];
let tickerIndex = 0;

/** Update the announcement ticker text */
function rotateTicker() {
  const el = document.getElementById('ticker-text');
  if (!el || !tickerAnnouncements.length) return;
  const ann = tickerAnnouncements[tickerIndex % tickerAnnouncements.length];
  el.textContent = ann.text;
  tickerIndex++;
}

/** Fetch latest announcements and start ticker rotation */
async function loadAnnouncements() {
  try {
    const data = await apiFetch('/api/announcements');
    if (data.success && data.announcements.length) {
      tickerAnnouncements = data.announcements;
      rotateTicker();
      setInterval(rotateTicker, 6000);
    }
  } catch (e) {
    console.warn('Announcement fetch failed:', e.message);
  }
}

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
  loadAnnouncements();
  // Poll announcements every 60s for new broadcasts
  setInterval(loadAnnouncements, 60_000);
});
