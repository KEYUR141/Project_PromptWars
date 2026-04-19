/**
 * VenueIQ — app.js
 * Shared utilities used across all pages.
 */

'use strict';

/** Format a percentage into a CSS fill class */
function statusClass(pct) {
  if (pct >= 90) return 'critical';
  if (pct >= 70) return 'busy';
  if (pct >= 40) return 'moderate';
  return 'quiet';
}

/** Update a capacity bar element */
function updateBar(zoneId, current, capacity) {
  const pct = Math.round((current / capacity) * 100);
  const status = statusClass(pct);

  const bar = document.getElementById(`bar-${zoneId}`);
  const pctEl = document.getElementById(`pct-${zoneId}`);
  const badge = document.querySelector(`#zone-${zoneId} .badge`);
  const wrap = document.getElementById(`zone-${zoneId}`);

  if (bar) {
    bar.style.width = `${pct}%`;
    bar.className = `capacity-bar-fill fill-${status}`;
  }
  if (pctEl) pctEl.textContent = `${current}/${capacity}`;
  if (badge) {
    badge.className = `badge badge-${status}`;
    badge.textContent = status.charAt(0).toUpperCase() + status.slice(1);
  }
  if (wrap) {
    wrap.setAttribute('aria-label',
      `${wrap.querySelector('.zone-name')?.textContent}: ${current} of ${capacity} (${pct}%)`
    );
  }
}

/** Show a temporary toast notification */
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.setAttribute('role', 'status');
  toast.setAttribute('aria-live', 'polite');
  Object.assign(toast.style, {
    position: 'fixed', bottom: '1.5rem', right: '1.5rem',
    background: type === 'error' ? 'var(--danger)' : 'var(--primary)',
    color: '#fff', padding: '.75rem 1.25rem',
    borderRadius: 'var(--radius-sm)', fontSize: '.88rem',
    fontWeight: '600', zIndex: '9999',
    boxShadow: 'var(--shadow)', animation: 'msg-in .25s ease-out',
  });
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

/** Generic API fetch wrapper with error handling */
async function apiFetch(url, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (options.method && options.method.toUpperCase() === 'POST') {
    headers['X-CSRF-Token'] = 'venueiq-csrf-token';
  }
  
  const resp = await fetch(url, {
    ...options,
    headers
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || `HTTP ${resp.status}`);
  }
  return resp.json();
}

/** Poll crowd status and update all zone bars */
async function pollCrowdStatus() {
  try {
    const data = await apiFetch('/api/crowd-status');
    if (!data.success) return;

    data.zones.forEach(zone => {
      updateBar(zone.id, zone.current, zone.capacity);
      // Also update attendee view bars if present
      const attBar = document.getElementById(`att-bar-${zone.id}`);
      const attBadge = document.getElementById(`att-badge-${zone.id}`);
      if (attBar) {
        attBar.style.width = `${zone.percentage}%`;
        attBar.className = `capacity-bar-fill fill-${zone.status}`;
      }
      if (attBadge) {
        attBadge.className = `badge badge-${zone.status}`;
        attBadge.textContent = zone.status.charAt(0).toUpperCase() + zone.status.slice(1);
      }
    });

    const updEl = document.getElementById('last-updated');
    if (updEl) updEl.textContent = `Updated ${new Date().toLocaleTimeString()}`;

    // Emit event for other scripts to update without re-fetching
    document.dispatchEvent(new CustomEvent('crowdUpdated', { detail: data.zones }));

  } catch (e) {
    console.warn('Crowd status poll error:', e.message);
  }
}

// Start polling every 30 seconds
setInterval(pollCrowdStatus, 30_000);
