import test from 'node:test';
import assert from 'node:assert/strict';
import { eventPayload, configureAnalyticsCatalog, productionAllowed, initializeAnalytics } from '../analytics.js';

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
});

test('preview and unreviewed production settings do not load analytics', () => {
  const enabled = {enhancedMeasurementReviewed:true, productionHosts:['whobuiltmyhome.com']};
  assert.equal(productionAllowed({protocol:'http:',hostname:'localhost'}, enabled), false);
  assert.equal(productionAllowed({protocol:'https:',hostname:'preview.example.com'}, enabled), false);
  assert.equal(productionAllowed({protocol:'https:',hostname:'whobuiltmyhome.com'}), false);
  assert.equal(productionAllowed({protocol:'https:',hostname:'whobuiltmyhome.com'}, enabled), true);
  assert.equal(initializeAnalytics(null), false);
});

test('enabled transport uses a canonical URL and a coarse referrer', () => {
  const scripts = [];
  const win = {
    location:{protocol:'https:',hostname:'whobuiltmyhome.com',href:'https://whobuiltmyhome.com/?q=123+Private+St&pin=0123456789'},
    navigator:{}, localStorage:{getItem:()=>null},
    document:{referrer:'https://example.com/search?q=private',createElement:()=>({}),head:{append:s=>scripts.push(s)}},
  };
  const config = {measurementId:'G-TEST',enhancedMeasurementReviewed:true,productionHosts:['whobuiltmyhome.com']};
  assert.equal(initializeAnalytics(win, config), true);
  const commands = win.dataLayer.map(a => Array.from(a));
  assert.equal(scripts.length, 1);
  assert.equal(commands.find(a=>a[0]==='config')[2].send_page_view, false);
  assert.equal(commands.find(a=>a[0]==='set')[1].page_referrer, 'https://example.com/');
  assert.ok(!/Private|0123456789|q=private/.test(JSON.stringify(commands)));
});
