import { mapConfig } from './map-config.js';

const resourcePromises = new Map();
const integer = value => value.toLocaleString('en-US');

async function responseJson(response) {
  if (!response.ok) throw new Error('Map data unavailable');
  if (typeof response.arrayBuffer !== 'function') return response.json();
  const bytes = new Uint8Array(await response.arrayBuffer());
  const stream = bytes[0] === 0x1f && bytes[1] === 0x8b
    ? new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))
    : new Blob([bytes]).stream();
  return JSON.parse(await new Response(stream).text());
}

export function validateGeometry(data, manifest, properties) {
  if (data?.version !== 1 || data.indexSha256 !== manifest.indexSha256 ||
      data.coordinateOrder !== 'latitude,longitude' || data.locationType !== 'parcel-centroid' ||
      !data.locations || Array.isArray(data.locations) || typeof data.locations !== 'object' ||
      !data.excluded || Array.isArray(data.excluded) || typeof data.excluded !== 'object') throw new Error('Invalid map release');
  const pins = new Set(properties.map(property => property.pin));
  const locations = new Map();
  for (const [pin, point] of Object.entries(data.locations)) {
    if (!pins.has(pin) || !Array.isArray(point) || point.length !== 2 ||
        !point.every(Number.isFinite) || point[0] < 47 || point[0] > 47.9 ||
        point[1] < -122.6 || point[1] > -121) throw new Error('Invalid parcel location');
    locations.set(pin, point);
  }
  const excluded = Object.keys(data.excluded);
  if (excluded.some(pin => !pins.has(pin) || locations.has(pin)) ||
      locations.size !== manifest.mappedPropertyCount || excluded.length !== manifest.unmappedPropertyCount ||
      locations.size + excluded.length !== pins.size) throw new Error('Map coverage does not reconcile');
  return locations;
}

export function matchMapProperties(properties, locations) {
  const mapped = properties.filter(property => locations.has(property.pin));
  return { mapped, missing: properties.length - mapped.length };
}

function loadResource(path, style = false) {
  if (resourcePromises.has(path)) return resourcePromises.get(path);
  const promise = new Promise((resolve, reject) => {
    const element = document.createElement(style ? 'link' : 'script');
    if (style) { element.rel = 'stylesheet'; element.href = new URL(path, import.meta.url).href; }
    else element.src = new URL(path, import.meta.url).href;
    const timer = setTimeout(() => fail(), 15000);
    function fail() { clearTimeout(timer); element.remove(); resourcePromises.delete(path); reject(new Error('Map assets unavailable')); }
    element.onload = () => { clearTimeout(timer); resolve(); };
    element.onerror = fail;
    document.head.append(element);
  });
  resourcePromises.set(path, promise);
  return promise;
}

async function loadLibraries() {
  await Promise.all([
    loadResource('./vendor/leaflet-1.9.4/leaflet.css', true),
    loadResource('./vendor/leaflet.markercluster-1.5.3/MarkerCluster.css', true),
    loadResource('./vendor/leaflet-1.9.4/leaflet.js'),
  ]);
  await loadResource('./vendor/leaflet.markercluster-1.5.3/leaflet.markercluster.js');
  if (!window.L?.markerClusterGroup) throw new Error('Map library unavailable');
  return window.L;
}

export function createPropertyMap({ manifest, properties, onOpen, elements }) {
  const { canvas, status, error, retry, fit, tileNotice } = elements;
  let map = null;
  let clusters = null;
  let tiles = null;
  let locations = null;
  let library = null;
  let pending = null;
  let visible = false;
  let latest = [];
  let signature = null;
  let renderTimer;
  let bounds = null;
  const markers = new Map();

  function fitResults() {
    if (visible && bounds?.isValid()) map.fitBounds(bounds, { padding: [34, 34], maxZoom: 17, animate: false });
  }

  function markerFor(property) {
    if (markers.has(property.pin)) return markers.get(property.pin);
    const label = `${property.address}, ${property.city}. Open property record.`;
    const marker = library.marker(locations.get(property.pin), {
      icon: library.divIcon({ className: 'property-map-pin', html: '<span aria-hidden="true"></span>', iconSize: [24, 24], iconAnchor: [12, 12] }),
      title: label, alt: label, keyboard: true,
    });
    const tooltip = document.createElement('span');
    tooltip.textContent = `${property.address} · ${property.city}`;
    marker.bindTooltip(tooltip, { direction: 'top', offset: [0, -12] });
    marker.on('click', () => onOpen(property.pin));
    marker.on('add', () => marker.getElement()?.setAttribute('aria-label', label));
    markers.set(property.pin, marker);
    return marker;
  }

  function render() {
    if (!visible || !map || !locations) return;
    const { mapped, missing } = matchMapProperties(latest, locations);
    status.textContent = latest.length
      ? `${integer(mapped.length)} of ${integer(latest.length)} matching homes mapped${missing ? ` · ${integer(missing)} without a checked location remain in the list` : ''}.`
      : 'No matching homes. Change the search or filters to see parcel locations.';
    fit.disabled = mapped.length === 0;
    // Sorting or moving between list pages must not reset a user's map position.
    const nextSignature = mapped.map(property => property.pin).sort().join(',');
    if (signature === nextSignature) return;
    clusters.clearLayers();
    const nextMarkers = mapped.map(markerFor);
    clusters.addLayers(nextMarkers);
    bounds = clusters.getBounds();
    fitResults();
    signature = nextSignature;
  }

  function showError() {
    status.textContent = 'Map unavailable. Search results are still available below.';
    error.hidden = false;
    retry.hidden = false;
  }

  async function initialize() {
    if (map) return;
    if (pending) return pending;
    status.textContent = 'Loading parcel locations and map…';
    error.hidden = true;
    retry.hidden = true;
    fit.disabled = true;
    pending = (async () => {
      const url = new URL(manifest.geometryUrl, document.baseURI);
      if (url.origin !== window.location.origin) throw new Error('Invalid geometry source');
      const [L, response] = await Promise.all([loadLibraries(), fetch(url, { credentials: 'same-origin', signal: AbortSignal.timeout(15000) })]);
      const data = await responseJson(response);
      locations = validateGeometry(data, manifest, properties);
      library = L;
      map = L.map(canvas, { scrollWheelZoom: false, minZoom: 8, maxZoom: mapConfig.maxZoom, zoomControl: true });
      map.setView([47.62, -122.1], 10);
      tiles = L.tileLayer(mapConfig.tileUrl, {
        attribution: mapConfig.attribution, maxZoom: mapConfig.maxZoom,
        // Override the document's no-referrer for tiles only; never send q/PIN.
        referrerPolicy: 'origin', updateWhenIdle: true, keepBuffer: 0,
      });
      let tileErrors = 0;
      tiles.on('loading', () => { tileErrors = 0; });
      tiles.on('tileerror', () => {
        tileErrors += 1;
        tileNotice.hidden = false;
        tileNotice.textContent = 'Some background map tiles are unavailable. Parcel markers and the result list still work.';
      });
      tiles.on('load', () => { if (!tileErrors) tileNotice.hidden = true; });
      // Adding tiles is delayed if the user hides the map while it is loading.
      clusters = L.markerClusterGroup({
        showCoverageOnHover: false, animate: false, maxClusterRadius: 48,
        spiderfyOnMaxZoom: true, zoomToBoundsOnClick: true,
        iconCreateFunction: cluster => {
          const count = cluster.getChildCount();
          const label = `${integer(count)} properties. Zoom in to explore.`;
          const html = document.createElement('span');
          html.textContent = integer(count);
          html.setAttribute('aria-label', label);
          return L.divIcon({ html, className: 'property-map-cluster', iconSize: [44, 44] });
        },
      }).addTo(map);
    })().catch(reason => {
      if (map) { map.remove(); map = null; }
      clusters = null;
      signature = null;
      showError();
      throw reason;
    }).finally(() => { pending = null; });
    return pending;
  }

  return {
    async show() {
      visible = true;
      try {
        await initialize();
        if (!visible) return;
        map.invalidateSize({ animate: false });
        if (!map.hasLayer(tiles)) tiles.addTo(map);
        render();
      } catch { showError(); }
    },
    hide() {
      visible = false;
      clearTimeout(renderTimer);
      if (tiles && map?.hasLayer(tiles)) map.removeLayer(tiles);
    },
    setProperties(next) {
      latest = next;
      clearTimeout(renderTimer);
      if (visible) renderTimer = setTimeout(() => { try { render(); } catch { showError(); } }, 150);
    },
    fit: fitResults,
  };
}
