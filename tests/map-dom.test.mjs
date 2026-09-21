// DOM integration, using the real vendored map libraries without requesting tiles.
// This verifies behavior; it is not a visual browser or mobile rendering test.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { gunzipSync } from 'node:zlib';
import { JSDOM } from 'jsdom';

test('real app and map recover from geometry failure, share filters, open evidence and keep list usable', async () => {
  const root = new URL('../', import.meta.url);
  const manifest = JSON.parse(readFileSync(new URL('data/manifest.json', root), 'utf8'));
  const total = manifest.verifiedPropertyCount.toLocaleString('en-US');
  const dom = new JSDOM(readFileSync(new URL('index.html', root), 'utf8'), {
    url: 'http://localhost:8765/?from=1900&review=flagged', runScripts: 'outside-only', pretendToBeVisual: true,
  });
  const { window } = dom;
  const { document } = window;
  const saved = new Map(['window', 'document', 'navigator', 'fetch'].map(k => [k, Object.getOwnPropertyDescriptor(globalThis, k)]));
  let failGeometry = true;
  const requested = [];
  const fetchLocal = async input => {
    const path = new URL(String(input)).pathname.slice(1);
    requested.push(path);
    if (path.includes('geometry.') && failGeometry) return { ok: false };
    const bytes = readFileSync(new URL(path, root));
    const content = JSON.parse(path.endsWith('.gz') ? gunzipSync(bytes) : bytes);
    return { ok: true, json: async () => structuredClone(content) };
  };
  Object.defineProperties(globalThis, {
    window: { value: window, configurable: true }, document: { value: document, configurable: true },
    navigator: { value: window.navigator, configurable: true }, fetch: { value: fetchLocal, configurable: true },
  });
  window.matchMedia = () => ({ matches: true });
  window.HTMLElement.prototype.scrollIntoView = function () {};
  window.HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); };
  window.HTMLDialogElement.prototype.close = function () { this.removeAttribute('open'); this.dispatchEvent(new window.Event('close')); };
  window.SVGSVGElement.prototype.createSVGRect = () => ({});
  const canvas = document.getElementById('property-map');
  Object.defineProperties(canvas, { clientWidth: { value: 960 }, clientHeight: { value: 460 } });
  const append = document.head.append.bind(document.head);
  document.head.append = (...nodes) => {
    append(...nodes);
    for (const node of nodes) queueMicrotask(() => {
      try {
        if (node.tagName === 'SCRIPT') window.eval(readFileSync(fileURLToPath(node.src), 'utf8'));
        node.onload?.();
      } catch (error) { node.onerror?.(error); }
    });
  };
  const byId = id => document.getElementById(id);
  const until = async predicate => {
    const deadline = Date.now() + 7000;
    while (!predicate()) {
      if (Date.now() > deadline) throw new Error('Timed out: ' + predicate.toString());
      await new Promise(resolve => setTimeout(resolve, 25));
    }
  };
  const change = (id, value, event = 'change') => { byId(id).value = value; byId(id).dispatchEvent(new window.Event(event, { bubbles: true })); };
  try {
    await import('../app.js');
    await until(() => !byId('toggle-map').disabled);
    assert.equal(document.querySelectorAll('.property-item').length, 50);
    assert.equal(requested.some(path => path.includes('geometry.')), false, 'geometry stays lazy');
    byId('toggle-map').click();
    await until(() => !byId('retry-map').hidden);
    assert.equal(document.querySelectorAll('.property-item').length, 50, 'map failure preserves list');
    failGeometry = false;
    byId('retry-map').click();
    await until(() => byId('map-status').textContent.startsWith(`${total} of ${total}`));
    assert.ok(canvas.querySelector('.property-map-cluster'), 'real library creates clusters');
    assert.ok(canvas.querySelector('img.leaflet-tile').referrerPolicy === 'origin');
    assert.ok(canvas.querySelector('.leaflet-control-attribution').textContent.includes('OpenStreetMap'));
    assert.equal(byId('collection').querySelector('option[value=burnstead]').disabled, false);
    assert.equal(byId('collection').querySelector('option[value=quadrant]').disabled, false);
    assert.equal(byId('review'), null, 'data-note review is not a primary search filter');
    assert.equal(byId('year-from').options.length, 49);
    assert.equal(byId('year-to').options.length, 49);
    assert.equal(byId('year-from').options[1].value, '2026');
    assert.equal(byId('year-from').options[48].value, '1979');
    assert.equal(window.location.search, '', 'legacy review and unavailable year parameters are cleared');
    assert.equal(document.querySelector('details.source-note').open, false, 'county source details start collapsed');
    const beforeZoom = canvas.querySelector('.leaflet-marker-pane').innerHTML;
    canvas.querySelector('.property-map-cluster').dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
    await until(() => canvas.querySelector('.leaflet-marker-pane').innerHTML !== beforeZoom);
    change('collection', 'mainvue'); change('city', 'RENTON'); change('year-from', '2020'); change('year-to', '2021');
    await until(() => byId('map-status').textContent.startsWith('86 of 86'));
    const markersBeforePage = canvas.querySelector('.leaflet-marker-pane').innerHTML;
    byId('next-page').click();
    assert.equal(document.querySelectorAll('.property-item').length, 36);
    await new Promise(resolve => setTimeout(resolve, 250));
    assert.equal(byId('map-status').textContent.startsWith('86 of 86'), true);
    assert.equal(canvas.querySelector('.leaflet-marker-pane').innerHTML, markersBeforePage);
    byId('clear-filters').click();
    change('search', '0292000050', 'input');
    await until(() => byId('map-status').textContent.startsWith('1 of 1'));
    canvas.querySelector('.property-map-pin').dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
    await until(() => byId('detail-body').textContent.includes('County record references'));
    assert.equal(byId('detail-title').textContent, '1071 102ND PL SE');
    const countyLinks = [...byId('detail-body').querySelectorAll('.detail-source-links a')];
    assert.equal(countyLinks.length, 1);
    assert.equal(countyLinks[0].textContent, 'View King County property details ↗');
    assert.equal(countyLinks[0].href, 'https://blue.kingcounty.com/Assessor/eRealProperty/Detail.aspx?ParcelNbr=0292000050');
    assert.equal(byId('property-dialog').open, true);
    byId('close-detail').click();
    for (const collection of manifest.collections.filter(c => ['burnstead', 'quadrant'].includes(c.id))) {
      byId('clear-filters').click();
      change('collection', collection.id);
      const count = collection.propertyCount.toLocaleString('en-US');
      await until(() => byId('map-status').textContent.startsWith(`${count} of ${count}`));
      document.querySelector('.property-item button').click();
      await until(() => byId('detail-body').querySelector(`[data-collection=${collection.id}]`));
      assert.ok(byId('detail-body').textContent.includes('Matched company names:'));
      assert.ok(byId('detail-body').textContent.includes('View King County property details'));
      byId('close-detail').click();
    }
    change('search', 'no-such-address-ever', 'input');
    await until(() => byId('map-status').textContent.startsWith('No matching homes'));
    assert.equal(canvas.querySelectorAll('.leaflet-marker-icon').length, 0);
    assert.equal(byId('empty-state').hidden, false);
    assert.equal(byId('fit-map').disabled, true);
    byId('toggle-map').click();
    assert.equal(byId('map-content').hidden, true);
    assert.equal(canvas.querySelectorAll('img.leaflet-tile').length, 0, 'hidden map removes tile layer');
    byId('reset-empty').click();
    assert.equal(document.querySelectorAll('.property-item').length, 50);
    assert.equal(requested.every(path => path.startsWith('data/')), true, 'search makes no geocoding requests');
  } finally {
    dom.window.close();
    for (const [key, descriptor] of saved) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor);
      else delete globalThis[key];
    }
  }
});
