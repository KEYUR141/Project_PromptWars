/**
 * VenueIQ — organizer.js
 * Organizer dashboard logic: AI alerts, announcements, stats computation.
 */

'use strict';

/** Compute and render headline stats from zone data */
function renderStats(zones) {
  let total = 0, critical = 0, busy = 0, quiet = 0;
  zones.forEach(z => {
    total += z.current;
    if (z.status === 'critical') critical++;
    else if (z.status === 'busy') busy++;
    else if (z.status === 'quiet') quiet++;
  });
  const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  set('stat-total', total.toLocaleString());
  set('stat-critical', critical);
  set('stat-busy', busy);
  set('stat-quiet', quiet);
}

/** Render AI alerts into the feed panel */
function renderAlerts(alerts) {
  const feed = document.getElementById('alerts-feed');
  if (!feed) return;

  if (!alerts.length) {
    feed.innerHTML = '<p style="color:var(--muted);font-size:.85rem;text-align:center;padding:1rem;">No alerts generated.</p>';
    return;
  }

  feed.innerHTML = alerts.map(a => `
    <div class="alert-item alert-${a.level}" role="alert"
         aria-label="${a.level} alert for ${a.zone}: ${a.message}">
      <span class="alert-icon" aria-hidden="true">${a.icon}</span>
      <div class="alert-body">
        <div class="alert-msg">${a.message}</div>
        <div class="alert-zone">${a.zone} · ${a.timestamp}</div>
      </div>
    </div>
  `).join('');
}

/** Trigger Gemini crowd analysis */
async function analyzeCrowd() {
  const btn = document.getElementById('btn-analyze');
  const feed = document.getElementById('alerts-feed');
  if (btn) { btn.disabled = true; btn.textContent = 'Analyzing…'; }
  if (feed) feed.innerHTML = `
    <div style="text-align:center;padding:1.5rem;color:var(--muted);">
      <span class="material-symbols-rounded" style="font-size:2rem;display:block;margin-bottom:.5rem;animation:pulse 1s infinite;" aria-hidden="true">psychology</span>
      Gemini is analyzing crowd patterns…
    </div>`;

  try {
    const data = await apiFetch('/api/analyze-crowd', { method: 'POST' });
    if (data.success) {
      renderAlerts(data.alerts);
      showToast('✅ AI analysis complete');
    } else {
      showToast('AI analysis failed. Is GEMINI_API_KEY set?', 'error');
      renderAlerts([]);
    }
  } catch (err) {
    showToast(err.message, 'error');
    renderAlerts([]);
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = '<span class="material-symbols-rounded" aria-hidden="true" style="font-size:1rem;">refresh</span> Analyze'; }
  }
}

/** Manually update crowd count for a zone */
async function updateCrowd(zoneId) {
  const input = document.getElementById(`input-${zoneId}`);
  if (!input) return;
  const count = parseInt(input.value, 10);
  if (isNaN(count) || count < 0) { showToast('Please enter a valid number', 'error'); return; }

  try {
    await apiFetch('/api/update-crowd', {
      method: 'POST',
      body: JSON.stringify({ zone_id: zoneId, count }),
    });
    showToast(`✅ ${zoneId.replace('_', ' ')} updated`);
    // Immediately refresh stats
    const data = await apiFetch('/api/crowd-status');
    if (data.success) renderStats(data.zones);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

/** Send broadcast announcement */
async function sendAnnouncement() {
  const textEl   = document.getElementById('announce-text');
  const typeEl   = document.getElementById('announce-type');
  const statusEl = document.getElementById('announce-status');
  const btn      = document.getElementById('btn-announce');
  if (!textEl || !typeEl) return;

  const text = textEl.value.trim();
  if (text.length < 5) { showToast('Announcement must be at least 5 characters', 'error'); return; }

  if (btn) btn.disabled = true;
  try {
    const data = await apiFetch('/api/announce', {
      method: 'POST',
      body: JSON.stringify({ text, type: typeEl.value }),
    });
    if (data.success) {
      textEl.value = '';
      if (statusEl) {
        statusEl.innerHTML = `<span style="color:var(--success);">✅ Sent at ${data.announcement.timestamp}</span>`;
        setTimeout(() => { statusEl.innerHTML = ''; }, 4000);
      }
      showToast('📢 Announcement sent!');
    }
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    if (btn) btn.disabled = false;
  }
}

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
  // Wire up Analyze button
  document.getElementById('btn-analyze')?.addEventListener('click', analyzeCrowd);

  // Initial stats render from server-side data
  if (window.ZONES_DATA) renderStats(window.ZONES_DATA);

  // Re-render stats when crowd is updated globally
  document.addEventListener('crowdUpdated', (e) => {
    renderStats(e.detail);
  });
});
