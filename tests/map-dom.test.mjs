// DOM integration, using the real vendored map libraries without requesting tiles.
// This verifies behavior; it is not a visual browser or mobile rendering test.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { gunzipSync } from 'node:zlib';
import { JSDOM } from 'jsdom';

test('search, map, all builder dialogs and sharing remain usable after copy cleanup', async () => {
  const root = new URL('../', import.meta.url);
  const manifest = JSON.parse(readFileSync(new URL('data/manifest.json', root), 'utf8'));
  const total = manifest.verifiedPropertyCount.toLocaleString('en-US');
  const dom = new JSDOM(readFileSync(new URL('index.html', root), 'utf8'), {
    url: 'http://localhost:8765/?from=1900&review=flagged&pin=0000000000', runScripts: 'outside-only', pretendToBeVisual: true,
  });
  const { window } = dom;
  const { document } = window;
  const saved = new Map(['window', 'document', 'navigator', 'fetch'].map(k => [k, Object.getOwnPropertyDescriptor(globalThis, k)]));
  let failGeometry = true;
  let failManifest = true;
  let failDetails = true;
  let failClipboard = false;
  let copiedLink = '';
  const requested = [];
  const fetchLocal = async input => {
    const path = new URL(String(input)).pathname.slice(1);
    requested.push(path);
    if (path === 'data/manifest.json' && failManifest) return { ok: false };
    if (path.includes('geometry.') && failGeometry) return { ok: false };
    if (path.includes('details.') && failDetails) return { ok: false };
    const bytes = readFileSync(new URL(path, root));
    const content = JSON.parse(path.endsWith('.gz') ? gunzipSync(bytes) : bytes);
    return { ok: true, json: async () => structuredClone(content) };
  };
  Object.defineProperties(globalThis, {
    window: { value: window, configurable: true }, document: { value: document, configurable: true },
    navigator: { value: window.navigator, configurable: true }, fetch: { value: fetchLocal, configurable: true },
  });
  window.matchMedia = () => ({ matches: true });
  Object.defineProperty(window.navigator, 'clipboard', { value: {
    writeText: async value => {
      if (failClipboard) throw new Error('Clipboard unavailable');
      copiedLink = value;
    },
  } });
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
    await until(() => byId('load-state').querySelector('button'));
    assert.equal(byId('search-button').disabled, true);
    failManifest = false;
    byId('load-state').querySelector('button').click();
    await until(() => !byId('toggle-map').disabled);
    await until(() => byId('property-dialog').open);
    assert.equal(byId('copy-property-link').disabled, true, 'unknown shared home cannot be copied');
    assert.equal(byId('detail-body').querySelector('.detail-source-links'), null);
    byId('close-detail').click();
    assert.equal(document.querySelectorAll('.property-item').length, 20);
    assert.equal(requested.some(path => path.includes('geometry.')), false, 'geometry stays lazy');
    byId('toggle-map').click();
    await until(() => !byId('retry-map').hidden);
    assert.equal(document.querySelectorAll('.property-item').length, 20, 'map failure preserves list');
    failGeometry = false;
    byId('retry-map').click();
    await until(() => byId('map-status').textContent.startsWith(`${total} of ${total}`));
    assert.ok(canvas.querySelector('.property-map-cluster'), 'real library creates clusters');
    assert.ok(canvas.querySelector('img.leaflet-tile').referrerPolicy === 'origin');
    assert.ok(canvas.querySelector('.leaflet-control-attribution').textContent.includes('OpenStreetMap'));
    assert.equal(byId('collection').querySelector('option[value=burnstead]').disabled, false);
    assert.equal(byId('collection').querySelector('option[value=quadrant]').disabled, false);
    assert.equal(byId('review'), null, 'data-note review is not a primary search filter');
    const properties = JSON.parse(gunzipSync(readFileSync(new URL(manifest.indexUrl, root))));
    const years = [...new Set(properties.map(p => p.yearBuilt).filter(Number.isInteger))].sort((a, b) => b - a);
    assert.equal(byId('year-options').options.length, years.length);
    assert.equal(byId('year-options').options[0].value, '2026');
    assert.equal(byId('year-options').options[years.length - 1].value, '1965');
    assert.equal(window.location.search, '?from=1900', 'valid typed year boundaries survive even when no home was built in that year');
    assert.equal(document.querySelector('details.source-note').open, false, 'county source details start collapsed');
    const beforeZoom = canvas.querySelector('.leaflet-marker-pane').innerHTML;
    canvas.querySelector('.property-map-cluster').dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
    await until(() => canvas.querySelector('.leaflet-marker-pane').innerHTML !== beforeZoom);
    change('collection', 'mainvue'); change('city', 'RENTON'); change('year-from', '2020'); change('year-to', '2021');
    await until(() => byId('map-status').textContent.startsWith('86 of 86'));
    const markersBeforePage = canvas.querySelector('.leaflet-marker-pane').innerHTML;
    byId('next-page').click();
    assert.equal(document.querySelectorAll('.property-item').length, 20);
    await new Promise(resolve => setTimeout(resolve, 250));
    assert.equal(byId('map-status').textContent.startsWith('86 of 86'), true);
    assert.equal(canvas.querySelector('.leaflet-marker-pane').innerHTML, markersBeforePage);
    byId('clear-filters').click();
    change('search', '0292000050', 'input');
    await until(() => byId('map-status').textContent.startsWith('1 of 1'));
    canvas.querySelector('.property-map-pin').dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
    await until(() => byId('detail-body').querySelector('.detail-error'));
    assert.equal(document.querySelectorAll('.property-item').length, 1, 'details failure preserves results');
    failDetails = false;
    byId('detail-body').querySelector('button').click();
    await until(() => byId('detail-body').querySelector('.recording-list'));
    assert.equal(byId('detail-title').textContent, '1071 102nd Pl SE');
    const countyLinks = [...byId('detail-body').querySelectorAll('.detail-source-links a')];
    assert.equal(countyLinks.length, 1);
    assert.match(countyLinks[0].textContent, /King County/);
    assert.equal(countyLinks[0].href, 'https://blue.kingcounty.com/Assessor/eRealProperty/Detail.aspx?ParcelNbr=0292000050');
    assert.equal(byId('property-dialog').open, true);
    byId('close-detail').click();
    for (const collection of manifest.collections) {
      byId('clear-filters').click();
      change('collection', collection.id);
      const count = collection.propertyCount.toLocaleString('en-US');
      await until(() => byId('map-status').textContent.startsWith(`${count} of ${count}`));
      document.querySelector('.property-item button').click();
      await until(() => byId('detail-body').querySelector(`[data-collection=${collection.id}]`));
      assert.equal(byId('detail-body').querySelector(`[data-collection=${collection.id}] h3`).textContent, collection.name);
      assert.ok(byId('detail-body').querySelector('.recording-list li'), 'county record numbers remain available');
      assert.doesNotMatch(byId('detail-body').textContent, /Company match group|reviewed company labels|No additional data notes listed|independently verified construction|investigate the association|Builder not confirmed|Original builder unconfirmed/);
      const countyLink = byId('detail-body').querySelector('.detail-source-links a');
      const pin = new URL(window.location.href).searchParams.get('pin');
      assert.equal(new URL(countyLink.href).searchParams.get('ParcelNbr'), pin);
      const reportLink = [...byId('detail-body').querySelectorAll('a')].find(a => a.href.startsWith('mailto:'));
      assert.equal(new URL(reportLink.href).pathname, 'hello@whobuiltmyhome.com');
      assert.ok(new URL(reportLink.href).searchParams.get('body').includes(pin));
      byId('copy-property-link').click();
      await until(() => copiedLink && new URL(copiedLink).searchParams.get('pin') === pin);
      assert.deepEqual([...new URL(copiedLink).searchParams.keys()], ['pin'], 'copied links exclude search/filter state');
      assert.equal(new URL(copiedLink).hash, '');
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
    assert.equal(document.querySelectorAll('.property-item').length, 20);
    assert.equal(byId('show-list').getAttribute('aria-pressed'), 'true');
    change('search', '25 92nd Avenue NE, Bellevue, WA 98004', 'input');
    assert.equal(document.querySelectorAll('.property-item').length, 1);
    assert.ok(byId('address-options').options[0].value.includes('Bellevue, WA'));
    change('collection', 'burnstead');
    assert.ok(byId('search-recovery').textContent.includes('1 match'));
    byId('search-recovery').querySelector('button').click();
    assert.equal(document.querySelectorAll('.property-item').length, 1);
    change('search', '25 92nd Ave NE Belleuve', 'input');
    assert.ok(byId('search-recovery').querySelector('button'));
    byId('search-recovery').querySelector('button').click();
    await until(() => byId('detail-body').querySelector('.detail-evidence'));
    assert.equal(byId('detail-title').textContent, '25 92nd Ave NE');
    assert.equal(byId('detail-body').querySelector('.detail-evidence').open, false);
    assert.ok(byId('detail-body').textContent.includes('Builder match'));
    assert.ok(byId('detail-body').textContent.includes('Source: King County records.'));
    assert.doesNotMatch(byId('detail-body').textContent, /builder.*unconfirmed|builder not confirmed/i);
    failClipboard = true;
    byId('copy-property-link').click();
    await until(() => byId('copy-status').textContent.includes('address bar'));
    failClipboard = false;
    byId('close-detail').click();
    byId('reset-empty').click();
    change('year-from', 'abcd');
    assert.equal(byId('filter-error').hidden, false);
    assert.ok(byId('filter-error').textContent.includes('four-digit'));
    document.querySelector('[data-year-from="2000"]').click();
    assert.equal(byId('year-from').value, '2000');
    assert.equal(byId('year-to').value, '2009');
    assert.equal(byId('filter-error').hidden, true);
    for (const button of document.querySelectorAll('[data-year-from]')) {
      button.click();
      assert.equal(byId('year-from').value, button.dataset.yearFrom);
      assert.equal(byId('year-to').value, button.dataset.yearTo || '');
      assert.equal(byId('filter-error').hidden, true);
    }
    change('year-from', '2020');
    change('year-to', '2000');
    assert.equal(byId('filter-error').hidden, false, 'reversed year range is rejected');
    assert.equal(byId('empty-state').hidden, true, 'invalid filter is not presented as missing data');
    byId('clear-filters').click();
    for (const value of ['city', 'year-asc', 'year-desc', 'address']) {
      change('sort', value);
      assert.equal(document.querySelectorAll('.property-item').length, 20);
      assert.equal(new URL(window.location.href).searchParams.get('sort'), value === 'address' ? null : value);
    }
    const shared = properties.find(property => property.collectionIds.length > 1);
    assert.ok(shared, 'fixture includes a home linked to multiple builders');
    change('search', shared.pin, 'input');
    document.querySelector('.property-item button').click();
    await until(() => byId('detail-body').querySelectorAll('[data-collection]').length === shared.collectionIds.length);
    for (const id of shared.collectionIds) assert.ok(byId('detail-body').querySelector(`[data-collection=${id}] .recording-list li`));
    assert.equal(byId('detail-body').querySelector('.detail-evidence').open, false, 'record details start collapsed for all homes');
    byId('detail-body').querySelector('.detail-evidence summary').click();
    assert.equal(byId('detail-body').querySelector('.detail-evidence').open, true, 'record disclosure can be opened');
    byId('close-detail').click();
    for (const details of document.querySelectorAll('.source-note, #project, #privacy')) {
      details.querySelector('summary').click();
      assert.equal(details.open, true);
      details.querySelector('summary').click();
      assert.equal(details.open, false);
    }
    assert.equal(requested.every(path => path.startsWith('data/')), true, 'search makes no geocoding requests');
  } finally {
    dom.window.close();
    for (const [key, descriptor] of saved) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor);
      else delete globalThis[key];
    }
  }
});
