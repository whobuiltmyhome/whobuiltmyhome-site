import { ANALYTICS_CONFIG } from './analytics-config.js';

const CANONICAL_URL = 'https://whobuiltmyhome.com/';
const PAGE_TITLE = 'Who Built My Home? | King County';
const queryTypes = new Set(['empty', 'zip', 'address_or_text', 'city', 'text', 'address', 'postal', 'mixed']);
const filters = new Set(['city', 'collection', 'yearFrom', 'yearTo', 'from', 'to', 'sort', 'reset']);
let cities = new Set();
let collections = new Set();

export function configureAnalyticsCatalog(catalog = {}) {
  cities = new Set((catalog.cities || []).map(value => String(value).toLowerCase()));
  collections = new Set((catalog.collections || []).map(value => typeof value === 'string' ? value : value.id));
}

function integer(value, min, max) {
  if (value === '' || value === null || value === undefined) return undefined;
  const number = Number(value);
  return Number.isFinite(number) ? Math.max(min, Math.min(max, Math.trunc(number))) : undefined;
}

// Construct every payload explicitly. Never forward arbitrary caller fields.
export function eventPayload(name, input = {}) {
  let params;
  if (name === 'search_performed') {
    const count = integer(input.resultCount, 0, 10000000);
    const city = String(input.city || '').toLowerCase();
    const collection = String(input.collection || '');
    params = {
      query_type: queryTypes.has(input.queryType) ? input.queryType : 'text',
      query_length: integer(input.queryLength, 0, 200),
      result_count: count,
      has_results: count === undefined ? undefined : count > 0,
      city: cities.has(city) ? city : 'all',
      collection: collections.has(collection) ? collection : 'all',
      year_from: integer(input.yearFrom, 1800, 2100),
      year_to: integer(input.yearTo, 1800, 2100),
    };
  } else if (name === 'property_open') {
    params = { evidence_status: 'company_association' };
  } else if (name === 'source_click') {
    const sources = new Set(['county', 'county_record']);
    params = { source: sources.has(input.source) ? input.source : 'county_record' };
  } else if (name === 'filter_changed') {
    params = { filter: filters.has(input.filter) ? input.filter : 'other' };
  } else {
    return null;
  }
  return Object.fromEntries(Object.entries(params).filter(([, value]) => value !== undefined));
}

export function productionAllowed(location, config = ANALYTICS_CONFIG) {
  return Boolean(config.enhancedMeasurementReviewed && location?.protocol === 'https:' &&
    config.productionHosts.includes(location.hostname));
}

function referrerOrigin(value) {
  try {
    const url = new URL(value);
    return ['https:', 'http:'].includes(url.protocol) ? `${url.origin}/` : '';
  } catch {
    return '';
  }
}

let send = null;
export function initializeAnalytics(win = typeof window === 'undefined' ? null : window, config = ANALYTICS_CONFIG) {
  if (send || !win || !productionAllowed(win.location, config)) return false;
  try {
    if (win.localStorage.getItem('wbmh.analytics.optout') === '1' ||
        win[`ga-disable-${config.measurementId}`] === true ||
        win.navigator.globalPrivacyControl === true || win.navigator.doNotTrack === '1') return false;
  } catch {
    // If privacy preferences cannot be read, do not start reporting.
    return false;
  }
  win.dataLayer = win.dataLayer || [];
  const gtag = function () { win.dataLayer.push(arguments); };
  win.gtag = gtag;
  const common = {
    page_location: CANONICAL_URL,
    page_title: PAGE_TITLE,
    page_referrer: referrerOrigin(win.document.referrer),
  };
  gtag('js', new Date());
  gtag('set', common);
  gtag('config', config.measurementId, {
    ...common,
    send_page_view: false,
    allow_google_signals: false,
    allow_ad_personalization_signals: false,
  });
  const script = win.document.createElement('script');
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(config.measurementId)}`;
  script.referrerPolicy = 'origin';
  win.document.head.append(script);
  send = (name, params) => {
    // Recheck opt-out on each event without retaining query text or history.
    try {
      if (win.localStorage.getItem('wbmh.analytics.optout') === '1' ||
          win[`ga-disable-${config.measurementId}`] === true ||
          win.navigator.globalPrivacyControl === true || win.navigator.doNotTrack === '1') return;
      gtag('event', name, { ...params, ...common, send_to: config.measurementId });
    } catch { /* Measurement failure must never interrupt a lookup. */ }
  };
  send('page_view', {});
  return true;
}

function track(name, input) {
  const payload = eventPayload(name, input);
  if (payload && send) send(name, payload);
}

export const trackSearch = input => track('search_performed', input);
export const trackPropertyOpen = () => track('property_open');
export const trackSourceClick = input => track('source_click', input);
export const trackFilter = input => track('filter_changed', input);

initializeAnalytics();
