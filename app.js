import { configureAnalyticsCatalog, trackSearch, trackPropertyOpen, trackSourceClick, trackFilter } from './analytics.js';

export const PAGE_SIZE = 50;
const MAX_QUERY_LENGTH = 160;
const SORT_VALUES = new Set(['address', 'city', 'year-asc', 'year-desc']);
const collator = new Intl.Collator('en', { numeric: true, sensitivity: 'base' });

export function normalizeSearchText(value) {
  return String(value ?? '').normalize('NFKC').toLowerCase().replace(/[.,#]/g, ' ').replace(/\s+/g, ' ').trim();
}

function parseYear(value) {
  if (!/^\d{4}$/.test(String(value ?? ''))) return '';
  const year = Number(value);
  return year >= 1600 && year <= 2100 ? String(year) : '';
}

export function readUrlState(search = '') {
  const params = new URLSearchParams(search);
  const page = Number(params.get('page'));
  return {
    q: (params.get('q') || '').slice(0, MAX_QUERY_LENGTH).trim(),
    city: (params.get('city') || '').slice(0, 80),
    collection: (params.get('collection') || '').slice(0, 80),
    from: parseYear(params.get('from')),
    to: parseYear(params.get('to')),
    review: (params.get('review') || '').slice(0, 80),
    sort: SORT_VALUES.has(params.get('sort')) ? params.get('sort') : 'address',
    page: Number.isSafeInteger(page) && page > 0 ? page : 1,
    pin: /^\d{10}$/.test(params.get('pin') || '') ? params.get('pin') : '',
  };
}

export function buildUrlSearch(state) {
  const params = new URLSearchParams();
  for (const key of ['q', 'city', 'collection', 'from', 'to', 'review']) {
    if (state[key]) params.set(key, String(state[key]));
  }
  if (SORT_VALUES.has(state.sort) && state.sort !== 'address') params.set('sort', state.sort);
  if (state.page > 1) params.set('page', String(state.page));
  if (/^\d{10}$/.test(state.pin || '')) params.set('pin', state.pin);
  const query = params.toString();
  return query ? `?${query}` : '';
}

export function filterProperties(properties, state) {
  const tokens = normalizeSearchText(state.q).split(' ').filter(Boolean);
  const from = Number(state.from) || null;
  const to = Number(state.to) || null;
  const filtered = properties.filter(property => {
    if (state.city && normalizeSearchText(property.city) !== normalizeSearchText(state.city)) return false;
    if (state.collection && !property.collectionIds.includes(state.collection)) return false;
    if (from !== null && (property.yearBuilt === null || property.yearBuilt < from)) return false;
    if (to !== null && (property.yearBuilt === null || property.yearBuilt > to)) return false;
    const flags = property.reviewFlags || [];
    if (state.review === 'flagged' && !flags.length) return false;
    if (state.review === 'none' && flags.length) return false;
    if (state.review && !['flagged', 'none'].includes(state.review) && !flags.includes(state.review)) return false;
    if (tokens.length) {
      const haystack = normalizeSearchText(`${property.address} ${property.city} ${property.zip} ${property.pin}`);
      if (!tokens.every(token => haystack.includes(token))) return false;
    }
    return true;
  });
  return filtered.sort((a, b) => {
    let comparison = 0;
    if (state.sort === 'city') comparison = collator.compare(a.city, b.city);
    if (state.sort === 'year-asc' || state.sort === 'year-desc') {
      if (a.yearBuilt === null && b.yearBuilt !== null) return 1;
      if (b.yearBuilt === null && a.yearBuilt !== null) return -1;
      comparison = (a.yearBuilt ?? 0) - (b.yearBuilt ?? 0);
      if (state.sort === 'year-desc') comparison *= -1;
    }
    return comparison || collator.compare(a.address, b.address) || collator.compare(a.city, b.city) || collator.compare(a.pin, b.pin);
  });
}

export function paginateProperties(properties, requestedPage = 1, pageSize = PAGE_SIZE) {
  const size = Number.isSafeInteger(pageSize) && pageSize > 0 ? pageSize : PAGE_SIZE;
  const pageCount = Math.max(1, Math.ceil(properties.length / size));
  const page = Math.min(pageCount, Math.max(1, Number.isSafeInteger(requestedPage) ? requestedPage : 1));
  const start = (page - 1) * size;
  return { page, pageCount, start, end: Math.min(start + size, properties.length), items: properties.slice(start, start + size) };
}

export function getQueryType(query, cities = []) {
  const text = normalizeSearchText(query);
  if (!text) return 'empty';
  if (/^\d{5}(?:-\d{4})?$/.test(text)) return 'zip';
  if (cities.some(city => normalizeSearchText(city) === text)) return 'city';
  return /\d/.test(text) ? 'address' : 'text';
}

export function safeCountyUrl(value) {
  try {
    const url = new URL(value);
    if (url.protocol !== 'https:' || !(url.hostname === 'kingcounty.gov' || url.hostname.endsWith('.kingcounty.gov'))) return null;
    return url.href;
  } catch { return null; }
}

function node(tag, className = '', text = '') {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== '') element.textContent = String(text);
  return element;
}

function formatDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}/.test(String(value || ''))) return value ? String(value) : 'Not available';
  const date = new Date(String(value).slice(0, 10) + 'T00:00:00Z');
  return Number.isNaN(date.getTime()) ? 'Not available' : new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' }).format(date);
}

async function bootstrap() {
  const byId = id => document.getElementById(id);
  const ui = Object.fromEntries(['search-form', 'search', 'search-button', 'filters', 'city', 'collection', 'year-from', 'year-to', 'review', 'sort', 'filter-error', 'clear-filters', 'result-summary', 'results-title', 'load-state', 'property-list', 'empty-state', 'reset-empty', 'pagination', 'previous-page', 'next-page', 'page-label', 'property-dialog', 'detail-body', 'close-detail', 'copy-property-link', 'copy-status'].map(id => [id, byId(id)]));
  if (!ui['search-form']) return;
  let state = readUrlState(window.location.search);
  let properties = [];
  let byPin = new Map();
  let manifest = null;
  let cities = [];
  let detailsPromise = null;
  let detailsUrl = '';
  let filtered = [];
  let searchTimer;
  let lastTrackedSearch = '';
  let detailRequest = 0;
  let isReady = false;
  let mapController = null;
  let mapLoading = null;
  let mapExpanded = false;
  const integer = value => Number(value).toLocaleString('en-US');

  async function showMap() {
    if (!isReady || !manifest.geometryAvailable) return;
    byId('map-error').hidden = true;
    byId('retry-map').hidden = true;
    byId('map-status').textContent = 'Loading parcel locations and map…';
    try {
      if (!mapController) {
        if (!mapLoading) mapLoading = import('./property-map.js').then(({ createPropertyMap }) => {
          mapController = createPropertyMap({ manifest, properties, onOpen: pin => openProperty(pin, true),
            elements: { canvas: byId('property-map'), status: byId('map-status'), error: byId('map-error'),
              retry: byId('retry-map'), fit: byId('fit-map'), tileNotice: byId('map-tile-notice') } });
        }).finally(() => { mapLoading = null; });
        await mapLoading;
      }
      mapController.setProperties(filtered);
      if (mapExpanded) await mapController.show();
    } catch {
      byId('map-status').textContent = 'Map unavailable. Search results are still available below.';
      byId('map-error').hidden = false;
      byId('retry-map').hidden = false;
    }
  }

  function syncUrl() {
    const next = `${window.location.pathname}${buildUrlSearch(state)}${window.location.hash}`;
    if (next !== `${window.location.pathname}${window.location.search}${window.location.hash}`) window.history.replaceState(null, '', next);
  }

  function syncControls() {
    for (const [control, key] of [['search', 'q'], ['city', 'city'], ['collection', 'collection'], ['year-from', 'from'], ['year-to', 'to'], ['review', 'review'], ['sort', 'sort']]) ui[control].value = state[key];
  }

  function hasFilters() { return ['q', 'city', 'collection', 'from', 'to', 'review'].some(key => state[key]); }

  function emitSearch() {
    clearTimeout(searchTimer);
    if (!isReady || (state.from && state.to && Number(state.from) > Number(state.to))) return;
    const signature = JSON.stringify([state.q, state.city, state.collection, state.from, state.to, state.review]);
    if (lastTrackedSearch === signature) return;
    lastTrackedSearch = signature;
    trackSearch({ queryType: getQueryType(state.q, cities), queryLength: state.q.length, resultCount: filtered.length, city: state.city, collection: state.collection, yearFrom: Number(state.from) || undefined, yearTo: Number(state.to) || undefined, review: state.review });
  }

  function propertyRow(property) {
    const item = node('li', 'property-item');
    const button = node('button', 'property-button');
    button.type = 'button';
    button.setAttribute('aria-label', `View record for ${property.address}, ${property.city} ${property.zip}`);
    const main = node('span', 'property-main');
    main.append(node('span', 'property-address', property.address), node('span', 'property-locality', `${property.city}, WA ${property.zip}`));
    const meta = node('span', 'property-meta');
    meta.append(node('span', 'property-year', property.yearBuilt === null ? 'Year not listed' : `County year ${property.yearBuilt}`));
    const label = property.collectionIds.map(id => id === 'buchan' ? 'Buchan connection' : manifest.collections.find(collection => collection.id === id)?.name).filter(Boolean).join(' · ');
    meta.append(node('span', '', label || 'Historical company connection'));
    if (property.reviewFlags.length) meta.append(node('span', 'property-review', `${property.reviewFlags.length} review ${property.reviewFlags.length === 1 ? 'flag' : 'flags'}`));
    main.append(meta);
    const arrow = node('span', 'property-arrow', '↗');
    arrow.setAttribute('aria-hidden', 'true');
    button.append(main, arrow);
    button.addEventListener('click', () => openProperty(property.pin, true));
    item.append(button);
    return item;
  }

  function render(updateUrl = true) {
    if (!isReady) return;
    const invalidYears = state.from && state.to && Number(state.from) > Number(state.to);
    ui['filter-error'].hidden = !invalidYears;
    ui['filter-error'].textContent = invalidYears ? 'The “from” year must be earlier than or equal to the “to” year.' : '';
    filtered = filterProperties(properties, state);
    mapController?.setProperties(filtered);
    const page = paginateProperties(filtered, state.page);
    state.page = page.page;
    ui['property-list'].replaceChildren(...page.items.map(propertyRow));
    ui['property-list'].hidden = !page.items.length;
    ui['empty-state'].hidden = Boolean(page.items.length) || Boolean(invalidYears);
    ui['load-state'].hidden = true;
    ui['pagination'].hidden = page.pageCount <= 1;
    ui['clear-filters'].hidden = !hasFilters();
    ui['results-title'].textContent = invalidYears ? 'Check the year range' : hasFilters() ? `${integer(filtered.length)} matching ${filtered.length === 1 ? 'record' : 'records'}` : 'Explore the records';
    ui['result-summary'].textContent = invalidYears ? 'Adjust the years above to see matching records.' : filtered.length ? `Showing ${integer(page.start + 1)}–${integer(page.end)} of ${integer(filtered.length)} ${hasFilters() ? 'matching records' : 'published addresses'}` : `0 matches in ${integer(properties.length)} published addresses`;
    ui['page-label'].textContent = `Page ${integer(page.page)} of ${integer(page.pageCount)}`;
    ui['previous-page'].disabled = page.page === 1;
    ui['next-page'].disabled = page.page === page.pageCount;
    if (updateUrl) syncUrl();
  }

  function changePage(offset) {
    state.page += offset;
    render();
    ui['results-title'].focus({ preventScroll: true });
    ui['results-title'].scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start' });
  }

  function resetFilters() {
    clearTimeout(searchTimer);
    state = { ...readUrlState(), pin: state.pin };
    syncControls();
    render();
    trackFilter({ filter: 'reset' });
    ui.search.focus({ preventScroll: true });
  }

  function fact(label, value) {
    const item = node('div');
    item.append(node('dt', '', label), node('dd', '', value));
    return item;
  }

  function sourceLink(label, urlValue, source) {
    const url = safeCountyUrl(urlValue);
    if (!url) return null;
    const link = node('a', 'button button-secondary', `${label} ↗`);
    link.href = url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.addEventListener('click', () => trackSourceClick({ source }));
    return link;
  }

  async function fetchDetails() {
    if (!detailsPromise) {
      detailsPromise = fetch(detailsUrl, { credentials: 'same-origin' }).then(response => {
        if (!response.ok) throw new Error('Evidence unavailable');
        return response.json();
      }).then(value => {
        if (!value || Array.isArray(value) || typeof value !== 'object') throw new Error('Invalid evidence');
        return value;
      }).catch(error => { detailsPromise = null; throw error; });
    }
    return detailsPromise;
  }

  async function openProperty(pin, track = false) {
    const request = ++detailRequest;
    state.pin = pin;
    syncUrl();
    const property = byPin.get(pin);
    ui['detail-body'].replaceChildren();
    ui['copy-status'].textContent = '';
    ui['copy-property-link'].disabled = !property;
    const title = node('h2', '', property ? property.address : 'Record not in this release');
    title.id = 'detail-title';
    ui['detail-body'].append(title);
    if (!ui['property-dialog'].open) {
      ui['property-dialog'].showModal();
      document.body.classList.add('dialog-open');
    }
    if (!property) {
      ui['detail-body'].append(node('p', 'detail-notice', 'This shared parcel number is not in the current published collection. Close this record to search the available addresses.'));
      return;
    }
    if (track) trackPropertyOpen();
    ui['detail-body'].append(node('p', 'detail-locality', `${property.city}, WA ${property.zip}`));
    const badges = node('div', 'detail-badges');
    badges.append(node('span', 'badge badge-green', 'Address verified'), node('span', 'badge badge-neutral', 'Historical connection'), node('span', 'badge badge-gold', 'Builder unconfirmed'));
    const connectionNotice = 'This parcel has a historical company connection. The evidence does not establish who built the current structure.';
    ui['detail-body'].append(badges, node('p', 'detail-notice', property.collectionIds.includes('buchan') ? `${connectionNotice} The John Buchan / William Buchan attribution remains unresolved.` : connectionNotice));
    const facts = node('dl', 'detail-facts');
    facts.append(fact('King County parcel number', property.pin), fact('County year built', property.yearBuilt ?? 'Not listed'), fact('Collection', property.collectionIds.map(id => manifest.collections.find(collection => collection.id === id)?.name || 'Historical company connection').join('; ')));
    ui['detail-body'].append(facts);
    const loading = node('p', 'detail-loading', 'Loading the evidence for this record…');
    ui['detail-body'].append(loading);
    try {
      const allDetails = await fetchDetails();
      if (request !== detailRequest || state.pin !== pin) return;
      const detail = allDetails[pin];
      if (!detail || !Array.isArray(detail.recordings) || !Array.isArray(detail.notes)) throw new Error('Evidence unavailable');
      loading.remove();
      facts.append(fact('Earliest observed company recording', formatDate(detail.firstCompanyRecording)));
      const sources = node('div', 'detail-source-links');
      const county = sourceLink('County property record', detail.countyUrl, 'county_record');
      const map = sourceLink('County parcel map', detail.mapUrl, 'parcel_map');
      if (county) sources.append(county);
      if (map) sources.append(map);
      ui['detail-body'].append(sources);
      if (property.reviewFlags.length) {
        const section = node('section', 'detail-section');
        section.append(node('h3', '', 'Evidence to review'));
        const flags = node('ul');
        for (const flag of property.reviewFlags) {
          const label = manifest.evidenceLabels?.[flag] || 'Evidence review needed';
          const explanation = manifest.reviewFlagDescriptions?.[flag];
          flags.append(node('li', '', explanation ? `${label}: ${explanation}` : label));
        }
        section.append(flags);
        ui['detail-body'].append(section);
      } else {
        const section = node('section', 'detail-section');
        section.append(node('h3', '', 'Review status'), node('p', '', 'No listed review flags. This does not confirm the original builder.'));
        ui['detail-body'].append(section);
      }
      if (detail.notes.length) {
        const section = node('section', 'detail-section');
        section.append(node('h3', '', 'Research notes'));
        const notes = node('ul');
        for (const note of detail.notes) notes.append(node('li', '', note));
        section.append(notes);
        ui['detail-body'].append(section);
      }
      const section = node('section', 'detail-section');
      section.append(node('h3', '', 'Recording references'), node('p', '', 'These identifiers link the research to recorded documents. They are evidence of transactions, not a certification of construction.'));
      if (detail.recordings.length) {
        const list = node('ul', 'recording-list');
        list.setAttribute('aria-label', 'County recording identifiers');
        for (const recording of detail.recordings) list.append(node('li', '', recording));
        section.append(list);
      } else section.append(node('p', '', 'No recording identifier is included in this release.'));
      ui['detail-body'].append(section);
    } catch {
      if (request !== detailRequest || state.pin !== pin) return;
      loading.remove();
      ui['detail-body'].append(node('p', 'detail-error', 'The evidence file could not be loaded. Your search results are still available.'));
      const retry = node('button', 'button button-secondary', 'Retry evidence');
      retry.type = 'button';
      retry.addEventListener('click', () => openProperty(pin));
      ui['detail-body'].append(retry);
    }
  }

  function reconcileState() {
    const matchingCity = cities.find(city => normalizeSearchText(city) === normalizeSearchText(state.city));
    state.city = matchingCity || '';
    if (!manifest.collections.some(collection => collection.id === state.collection && ['ready', 'released', 'available'].includes(collection.status))) state.collection = '';
    const flags = new Set(properties.flatMap(property => property.reviewFlags));
    if (state.review && !['flagged', 'none'].includes(state.review) && !flags.has(state.review)) state.review = '';
  }

  function renderCollectionCatalog() {
    const available = manifest.collections.filter(collection => ['ready', 'released', 'available'].includes(collection.status));
    const roadmap = manifest.collections.filter(collection => collection.id !== 'buchan');
    if (roadmap.length) {
      byId('collection-grid').replaceChildren(...roadmap.map((collection, index) => {
        const item = node('li');
        const isAvailable = available.some(candidate => candidate.id === collection.id);
        const pendingLabel = ['john-f-buchan', 'william-e-buchan'].includes(collection.id) ? 'Brand attribution awaiting evidence' : 'Awaiting evidence review';
        item.append(node('span', 'collection-number', String(index + 1).padStart(2, '0')), node('h3', '', collection.name), node('p', '', isAvailable ? 'Available to explore' : pendingLabel));
        return item;
      }));
    }
    if (available.length > 1) {
      byId('coverage-label').textContent = `${available.length} available historical company collections`;
      byId('available-title').textContent = `${available.length} historical company collections`;
      byId('available-description').textContent = 'Choose an available collection in the search filters. Properties can have more than one historical connection.';
    }
  }

  function showLoadError() {
    isReady = false;
    ui['load-state'].hidden = false;
    ui['load-state'].replaceChildren(node('h3', '', 'The collection could not be loaded'), node('p', '', 'Check your connection, then try again. No search results have been loaded.'));
    const retry = node('button', 'button button-secondary', 'Try again');
    retry.type = 'button';
    retry.addEventListener('click', loadCollection);
    ui['load-state'].append(retry);
    ui['result-summary'].textContent = 'Property records are temporarily unavailable.';
  }

  async function loadCollection() {
    ui['load-state'].hidden = false;
    ui['load-state'].replaceChildren(node('div', 'loader'), node('p', '', 'Loading property records…'));
    ui['result-summary'].textContent = 'Loading the published collection…';
    try {
      const response = await fetch(new URL('./data/manifest.json', document.baseURI), { credentials: 'same-origin', cache: 'no-cache' });
      if (!response.ok) throw new Error('Manifest unavailable');
      const nextManifest = await response.json();
      if (!Array.isArray(nextManifest.collections) || !Number.isInteger(nextManifest.verifiedPropertyCount)) throw new Error('Invalid manifest');
      const indexUrl = new URL(nextManifest.indexUrl, document.baseURI);
      const evidenceUrl = new URL(nextManifest.detailsUrl, document.baseURI);
      if (indexUrl.origin !== window.location.origin || evidenceUrl.origin !== window.location.origin) throw new Error('Invalid release source');
      const indexResponse = await fetch(indexUrl, { credentials: 'same-origin' });
      if (!indexResponse.ok) throw new Error('Index unavailable');
      const nextProperties = await indexResponse.json();
      if (!Array.isArray(nextProperties) || nextProperties.length !== nextManifest.verifiedPropertyCount || nextProperties.some(property => typeof property.pin !== 'string' || !/^\d{10}$/.test(property.pin) || typeof property.address !== 'string' || typeof property.city !== 'string' || typeof property.zip !== 'string' || !Array.isArray(property.collectionIds) || !Array.isArray(property.reviewFlags) || (property.yearBuilt !== null && !Number.isInteger(property.yearBuilt)))) throw new Error('Invalid property index');
      if (new Set(nextProperties.map(property => property.pin)).size !== nextProperties.length) throw new Error('Duplicate properties');
      manifest = nextManifest;
      properties = nextProperties;
      detailsUrl = evidenceUrl.href;
      byPin = new Map(properties.map(property => [property.pin, property]));
      cities = [...new Set(properties.map(property => property.city))].sort(collator.compare);
      configureAnalyticsCatalog({ cities, collections: manifest.collections });
      for (const city of cities) {
        const option = node('option', '', city);
        option.value = city;
        ui.city.append(option);
      }
      for (const collection of manifest.collections) {
        const option = node('option', '', collection.name);
        option.value = collection.id;
        option.disabled = !['ready', 'released', 'available'].includes(collection.status);
        if (option.disabled) option.textContent += ' — awaiting evidence';
        ui.collection.append(option);
      }
      const flags = [...new Set(properties.flatMap(property => property.reviewFlags))];
      for (const flag of flags) {
        const option = node('option', '', manifest.evidenceLabels?.[flag] || flag.replace(/-/g, ' '));
        option.value = flag;
        ui.review.append(option);
      }
      byId('coverage-count').textContent = integer(properties.length);
      byId('collection-count').textContent = `${integer(properties.length)} verified addresses`;
      byId('release-info').textContent = `Source snapshot: ${formatDate(manifest.sourceAsOf)} · Release ${manifest.version} · Prepared ${formatDate(manifest.generatedAt)}`;
      renderCollectionCatalog();
      reconcileState();
      syncControls();
      isReady = true;
      ui.search.disabled = false;
      ui['search-button'].disabled = false;
      ui.filters.disabled = false;
      ui.sort.disabled = false;
      byId('toggle-map').disabled = !manifest.geometryAvailable;
      render();
      if (state.pin) await openProperty(state.pin);
    } catch { showLoadError(); }
  }

  ui['search-form'].addEventListener('submit', event => {
    event.preventDefault();
    if (!isReady) return;
    state.q = ui.search.value.slice(0, MAX_QUERY_LENGTH).trim();
    state.page = 1;
    render();
    emitSearch();
  });
  byId('toggle-map').addEventListener('click', () => {
    mapExpanded = !mapExpanded;
    byId('toggle-map').setAttribute('aria-expanded', String(mapExpanded));
    byId('toggle-map').textContent = mapExpanded ? 'Hide map' : 'Show map';
    byId('map-content').hidden = !mapExpanded;
    if (mapExpanded) void showMap();
    else mapController?.hide();
  });
  byId('retry-map').addEventListener('click', () => { void showMap(); });
  byId('fit-map').addEventListener('click', () => mapController?.fit());
  ui.search.addEventListener('input', () => {
    clearTimeout(searchTimer);
    state.q = ui.search.value.slice(0, MAX_QUERY_LENGTH).trim();
    state.page = 1;
    render();
    if (state.q) searchTimer = setTimeout(emitSearch, 1100);
  });
  for (const [control, key, analyticName] of [['city', 'city', 'city'], ['collection', 'collection', 'collection'], ['year-from', 'from', 'yearFrom'], ['year-to', 'to', 'yearTo'], ['review', 'review', 'review'], ['sort', 'sort', 'sort']]) {
    ui[control].addEventListener('change', () => {
      state[key] = ['from', 'to'].includes(key) ? parseYear(ui[control].value) : ui[control].value;
      if (['from', 'to'].includes(key)) ui[control].value = state[key];
      state.page = 1;
      render();
      trackFilter({ filter: analyticName });
    });
  }
  ui['clear-filters'].addEventListener('click', resetFilters);
  ui['reset-empty'].addEventListener('click', resetFilters);
  ui['previous-page'].addEventListener('click', () => changePage(-1));
  ui['next-page'].addEventListener('click', () => changePage(1));
  ui['close-detail'].addEventListener('click', () => ui['property-dialog'].close());
  ui['property-dialog'].addEventListener('click', event => {
    if (event.target !== ui['property-dialog']) return;
    const bounds = ui['property-dialog'].getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) ui['property-dialog'].close();
  });
  ui['property-dialog'].addEventListener('close', () => {
    detailRequest += 1;
    document.body.classList.remove('dialog-open');
    state.pin = '';
    syncUrl();
  });
  ui['copy-property-link'].addEventListener('click', async () => {
    const link = new URL(window.location.href);
    link.search = buildUrlSearch({ ...readUrlState(), pin: state.pin });
    link.hash = '';
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
      await navigator.clipboard.writeText(link.href);
      ui['copy-status'].textContent = 'Record link copied.';
    } catch {
      ui['copy-status'].textContent = 'Copy the link from your browser’s address bar.';
    }
  });
  for (const link of document.querySelectorAll('[data-source]')) link.addEventListener('click', () => trackSourceClick({ source: link.dataset.source }));
  window.addEventListener('popstate', () => {
    state = readUrlState(window.location.search);
    if (!isReady) return;
    reconcileState();
    syncControls();
    render();
    if (state.pin) openProperty(state.pin);
    else if (ui['property-dialog'].open) ui['property-dialog'].close();
  });
  await loadCollection();
}

if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => { void bootstrap(); }, { once: true });
  else void bootstrap();
}
