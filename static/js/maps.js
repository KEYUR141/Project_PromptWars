/**
 * VenueIQ — maps.js
 * Interactive Google Maps with Advanced Markers reflecting real-time crowd status.
 */

'use strict';

let map;
let markers = {};

// Status colors matching our CSS tokens
const statusColors = {
  critical: '#ef4444',
  busy: '#f59e0b',
  moderate: '#10b981',
  quiet: '#6366f1',
};

async function initMap() {
  if (!window.MAPS_API_KEY) return;

  const { Map } = await google.maps.importLibrary("maps");
  const { AdvancedMarkerElement, PinElement } = await google.maps.importLibrary("marker");

  const center = { lat: window.EVENT_LAT, lng: window.EVENT_LNG };

  map = new Map(document.getElementById("venue-map"), {
    zoom: 18,
    center: center,
    mapId: "VENUEIQ_MAP_ID", // Required for Advanced Markers
    disableDefaultUI: true,
    zoomControl: true,
  });

  // Render initial markers
  if (window.ZONES_DATA) {
    window.ZONES_DATA.forEach(zone => {
      createMarker(zone, AdvancedMarkerElement, PinElement);
    });
  }
}

function createMarker(zone, AdvancedMarkerElement, PinElement) {
  const pin = new PinElement({
    background: statusColors[zone.status],
    borderColor: '#ffffff',
    glyphColor: '#ffffff',
    scale: 1.2,
  });

  const marker = new AdvancedMarkerElement({
    map,
    position: { lat: zone.lat, lng: zone.lng },
    content: pin.element,
    title: `${zone.name} (${zone.percentage}%)`,
  });

  markers[zone.id] = { marker, pin };
}

// Intercept the pollCrowdStatus to update marker colors live
document.addEventListener('DOMContentLoaded', () => {
  if (!window.MAPS_API_KEY) return;
  initMap();

  document.addEventListener('crowdUpdated', (e) => {
    if (!map) return;
    e.detail.forEach(zone => {
      const m = markers[zone.id];
      if (m) {
        m.pin.background = statusColors[zone.status];
        m.marker.title = `${zone.name} (${zone.percentage}%)`;
      }
    });
  });
});
