import { ANALYTICS_CONFIG } from './analytics-config.js';

const CANONICAL_ORIGIN = 'https://whobuiltmyhome.com';
const pageTitles = new Map([
  ['/', 'Who Built My Home? | King County Home Builders'],
  ['/guides/find-home-builder-king-county/', 'How to Find Your Home Builder in King County | Who Built My Home?'],
  ['/builders/burnstead/', 'Burnstead Homes in King County | Who Built My Home?'],
  ['/builders/quadrant/', 'Quadrant Homes in King County | Who Built My Home?'],
]);
const campaignSources = new Set([
  'agent_outreach', 'reddit', 'facebook', 'nextdoor', 'newsletter',
  'living_snoqualmie', 'hoa', 'redmond_ridge',
]);
const campaignMedia = new Set(['email', 'social', 'referral']);
const campaignNames = new Set(['launch_2026_10']);
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
  } else if (name === 'share') {
    // Count a completed copy action, never the copied property or destination.
    params = { method: 'copy_link', content_type: 'property_evidence' };
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

function locationUrl(location) {
  try {
    return new URL(location?.href || `${CANONICAL_ORIGIN}${location?.pathname || '/'}${location?.search || ''}`);
  } catch {
    return new URL(`${CANONICAL_ORIGIN}/`);
  }
}

// Never use document.title or an arbitrary pathname as measurement input.
export function pageContext(location) {
  const pathname = locationUrl(location).pathname;
  const path = pathname === '/index.html' ? '/' : pathname.replace(/\/index\.html$/, '/');
  const pagePath = pageTitles.has(path) ? path : '/';
  return {
    page_location: `${CANONICAL_ORIGIN}${pagePath}`,
    page_path: pagePath,
    page_title: pageTitles.get(pagePath),
  };
}

export function campaignAttribution(location) {
  const params = locationUrl(location).searchParams;
  const values = ['utm_source', 'utm_medium', 'utm_campaign'].map(key => params.getAll(key));
  const hasCampaign = [...params.keys()].some(key => key.startsWith('utm_'));
  if (!hasCampaign) return {};

  const [source, medium, campaign] = values.map(value => value[0]);
  const valid = values.every(value => value.length === 1) &&
    campaignSources.has(source) && campaignMedia.has(medium) && campaignNames.has(campaign);
  // Explicit constants override unsupported native UTM values. No partial
  // campaign or duplicate parameters can silently label a visitor.
  const result = {
    campaign_source: valid ? source : 'unattributed',
    campaign_medium: valid ? medium : 'none',
    campaign_name: valid ? campaign : 'unattributed',
  };
  for (const [queryKey, campaignKey] of [
    ['utm_id', 'campaign_id'], ['utm_term', 'campaign_term'], ['utm_content', 'campaign_content'],
  ]) {
    if (params.has(queryKey)) result[campaignKey] = 'not_collected';
  }
  return result;
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
    ...pageContext(win.location),
    page_referrer: referrerOrigin(win.document.referrer),
    // Capture once before the explorer rewrites its URL. Retain only the
    // allowlisted strings, not the original query, PIN, or URL.
    ...campaignAttribution(win.location),
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
export const trackShare = () => track('share');

initializeAnalytics();
