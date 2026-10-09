import test from 'node:test';
import assert from 'node:assert/strict';
import { eventPayload, configureAnalyticsCatalog, productionAllowed, initializeAnalytics, pageContext, campaignAttribution } from '../analytics.js';

const enabledConfig = {measurementId:'G-TEST',enhancedMeasurementReviewed:true,productionHosts:['whobuiltmyhome.com']};
let importCount = 0;
function freshAnalytics() {
  // A separate module represents a fresh document load; production has no reset hook.
  return import(`../analytics.js?privacy-test=${++importCount}`);
}

function browser(href = 'https://whobuiltmyhome.com/') {
  const scripts = [];
  const win = {
    location: new URL(href),
    navigator: {}, localStorage: {getItem: () => null},
    document: {
      title: '123 Private St',
      referrer: 'https://example.com/search?q=private&pin=0123456789',
      createElement: () => ({}), head: {append: script => scripts.push(script)},
    },
  };
  return {win, scripts, commands: () => (win.dataLayer || []).map(args => Array.from(args))};
}

test('only coarse allowlisted search metadata can enter an event', () => {
  configureAnalyticsCatalog({ cities: ['BELLEVUE'], collections: [{id: 'mainvue'}] });
  const result = eventPayload('search_performed', {
    queryType: 'address', queryLength: 32, resultCount: 0,
    city: 'Bellevue', collection: 'mainvue', yearFrom: 1976, yearTo: 2026,
    query: '123 Private St', query_sample: '123 Private St', address: '123 Private St',
    pin: '0123456789', page_location: 'https://whobuiltmyhome.com/?q=123+Private+St',
  });
  assert.equal(result.result_count, 0);
  assert.equal(result.has_results, false);
  assert.equal(result.city, 'bellevue');
  assert.equal(result.collection, 'mainvue');
  assert.ok(!/Private|0123456789|page_location|query_sample/.test(JSON.stringify(result)));
  const hostile = eventPayload('search_performed', { city: '123 Private St', collection: 'person@example.com', queryType: '123 Private St', resultCount: Infinity });
  assert.equal(hostile.city, 'all');
  assert.equal(hostile.collection, 'all');
  assert.equal(hostile.query_type, 'text');
  assert.ok(!('result_count' in hostile));
});

test('property and source clicks never contain property identifiers', () => {
  assert.deepEqual(eventPayload('property_open', {pin:'0123456789',address:'Private'}), {evidence_status:'company_association'});
  assert.deepEqual(eventPayload('source_click', {source:'county_record',url:'https://example.com/?pin=0123456789'}), {source:'county_record'});
  assert.equal(eventPayload('arbitrary', {query:'Private'}), null);
  assert.deepEqual(eventPayload('share', {pin:'0123456789',address:'Private',url:'https://example.com/?pin=0123456789',method:'person@example.com'}), {method:'copy_link',content_type:'property_evidence'});
});

test('preview and unreviewed production settings do not load analytics', () => {
  const enabled = {enhancedMeasurementReviewed:true, productionHosts:['whobuiltmyhome.com']};
  assert.equal(productionAllowed({protocol:'http:',hostname:'localhost'}, enabled), false);
  assert.equal(productionAllowed({protocol:'https:',hostname:'preview.example.com'}, enabled), false);
  assert.equal(productionAllowed({protocol:'https:',hostname:'whobuiltmyhome.com'}), false);
  assert.equal(productionAllowed({protocol:'https:',hostname:'whobuiltmyhome.com'}, enabled), true);
  assert.equal(initializeAnalytics(null), false);
});

test('page identity uses exact released routes, never raw paths or document titles', () => {
  assert.equal(pageContext(new URL('https://whobuiltmyhome.com/index.html?q=Private')).page_path, '/');
  for (const path of ['/guides/find-home-builder-king-county/', '/builders/burnstead/', '/builders/quadrant/']) {
    const result = pageContext(new URL(`https://whobuiltmyhome.com${path}?q=Private&pin=0123456789#person@example.com`));
    assert.equal(result.page_path, path);
    assert.equal(result.page_location, `https://whobuiltmyhome.com${path}`);
    assert.equal(pageContext(new URL(`https://whobuiltmyhome.com${path}index.html`)).page_path, path);
    assert.ok(!/Private|0123456789|person@example.com/.test(JSON.stringify(result)));
  }
  for (const path of ['/builders/person@example.com/', '/builders/burnstead/0123456789/', '/123%20Private%20St']) {
    assert.equal(pageContext(new URL(`https://whobuiltmyhome.com${path}`)).page_path, '/');
  }
});

test('only complete exact launch campaign tags can label traffic', () => {
  const known = campaignAttribution(new URL('https://whobuiltmyhome.com/?utm_source=agent_outreach&utm_medium=email&utm_campaign=launch_2026_10&q=123+Private+St&pin=0123456789'));
  assert.deepEqual(known, {campaign_source:'agent_outreach',campaign_medium:'email',campaign_name:'launch_2026_10'});
  for (const source of ['reddit','facebook','nextdoor','newsletter','living_snoqualmie','hoa','redmond_ridge']) {
    assert.equal(campaignAttribution(new URL(`https://whobuiltmyhome.com/?utm_source=${source}&utm_medium=referral&utm_campaign=launch_2026_10`)).campaign_source, source);
  }
  assert.deepEqual(campaignAttribution(new URL('https://whobuiltmyhome.com/?q=Private&pin=0123456789')), {});
  for (const search of [
    '?utm_source=person@example.com&utm_medium=email&utm_campaign=launch_2026_10',
    '?utm_source=reddit&utm_medium=123+Private+St&utm_campaign=launch_2026_10',
    '?utm_source=reddit&utm_medium=social&utm_campaign=0123456789',
    '?utm_source=reddit&utm_medium=social',
    '?utm_source=reddit&utm_source=person@example.com&utm_medium=social&utm_campaign=launch_2026_10',
    '?utm_source=Reddit&utm_medium=social&utm_campaign=launch_2026_10',
  ]) {
    assert.deepEqual(campaignAttribution(new URL(`https://whobuiltmyhome.com/${search}`)), {campaign_source:'unattributed',campaign_medium:'none',campaign_name:'unattributed'});
  }
  const extra = campaignAttribution(new URL('https://whobuiltmyhome.com/?utm_source=reddit&utm_medium=social&utm_campaign=launch_2026_10&utm_id=0123456789&utm_term=123+Private+St&utm_content=person@example.com'));
  assert.equal(extra.campaign_id, 'not_collected');
  assert.equal(extra.campaign_term, 'not_collected');
  assert.equal(extra.campaign_content, 'not_collected');
  assert.ok(!/Private|0123456789|person@example.com/.test(JSON.stringify(extra)));
});

test('enabled transport uses a safe page identity and a coarse referrer', async () => {
  const analytics = await freshAnalytics();
  const {win, scripts, commands} = browser('https://whobuiltmyhome.com/?q=123+Private+St&pin=0123456789');
  assert.equal(analytics.initializeAnalytics(win, enabledConfig), true);
  const sent = commands();
  assert.equal(scripts.length, 1);
  assert.equal(scripts[0].referrerPolicy, 'origin');
  assert.equal(sent.find(a=>a[0]==='config')[2].send_page_view, false);
  assert.equal(sent.find(a=>a[0]==='set')[1].page_referrer, 'https://example.com/');
  assert.equal(sent.find(a=>a[0]==='set')[1].page_path, '/');
  assert.equal(sent.filter(a=>a[0]==='event' && a[1]==='page_view').length, 1);
  assert.ok(!/Private|0123456789|q=private/.test(JSON.stringify(sent)));
});

test('launch attribution survives explorer URL rewrites and share omits the copied home', async () => {
  const analytics = await freshAnalytics();
  const {win, commands} = browser('https://whobuiltmyhome.com/?utm_source=reddit&utm_medium=social&utm_campaign=launch_2026_10&q=123+Private+St&pin=0123456789');
  assert.equal(analytics.initializeAnalytics(win, enabledConfig), true);
  win.location = new URL('https://whobuiltmyhome.com/?q=987+Secret+Way&pin=9876543210');
  analytics.trackPropertyOpen();
  analytics.trackShare({url:win.location.href,pin:'9876543210',address:'987 Secret Way'});
  const sent = commands();
  assert.equal(sent.find(a=>a[0]==='config')[2].campaign_source, 'reddit');
  const share = sent.find(a=>a[0]==='event' && a[1]==='share')[2];
  assert.equal(share.campaign_source, 'reddit');
  assert.equal(share.campaign_medium, 'social');
  assert.equal(share.campaign_name, 'launch_2026_10');
  assert.equal(share.method, 'copy_link');
  assert.ok(!/Private|Secret|0123456789|9876543210|q=/.test(JSON.stringify(sent)));
  assert.equal(analytics.initializeAnalytics(win, enabledConfig), false);
});

test('static guide transport reports the guide instead of the homepage', async () => {
  const analytics = await freshAnalytics();
  const {win, commands} = browser('https://whobuiltmyhome.com/guides/find-home-builder-king-county/?q=123+Private+St&utm_source=newsletter&utm_medium=email&utm_campaign=launch_2026_10');
  assert.equal(analytics.initializeAnalytics(win, enabledConfig), true);
  const view = commands().find(a=>a[0]==='event' && a[1]==='page_view')[2];
  assert.equal(view.page_path, '/guides/find-home-builder-king-county/');
  assert.match(view.page_title, /^How to Find Your Home Builder/);
  assert.equal(view.campaign_source, 'newsletter');
  assert.ok(!/Private|q=/.test(JSON.stringify(commands())));
});

test('all privacy preferences and blocked domains prevent any tag load', async () => {
  for (const configure of [
    win => { win.localStorage.getItem = () => '1'; },
    win => { win.navigator.globalPrivacyControl = true; },
    win => { win.navigator.doNotTrack = '1'; },
    win => { win['ga-disable-G-TEST'] = true; },
    win => { win.localStorage.getItem = () => { throw new Error('Storage denied'); }; },
    win => { win.location = new URL('https://preview.example.com/'); },
    win => { win.location = new URL('http://whobuiltmyhome.com/'); },
  ]) {
    const analytics = await freshAnalytics();
    const {win, scripts, commands} = browser();
    configure(win);
    assert.equal(analytics.initializeAnalytics(win, enabledConfig), false);
    assert.equal(scripts.length, 0);
    assert.equal(commands().length, 0);
  }
});

test('a preference changed after initialization suppresses later manual events', async () => {
  const analytics = await freshAnalytics();
  const {win, commands} = browser();
  assert.equal(analytics.initializeAnalytics(win, enabledConfig), true);
  const before = commands().length;
  win.navigator.globalPrivacyControl = true;
  analytics.trackShare();
  analytics.trackPropertyOpen();
  assert.equal(commands().length, before);
});
