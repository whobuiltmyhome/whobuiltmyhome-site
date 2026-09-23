import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { gunzipSync } from 'node:zlib';
import { PAGE_SIZE, filterProperties, readUrlState, buildUrlSearch, paginateProperties, safeCountyUrl, suggestProperties } from '../app.js';

const manifest = JSON.parse(await readFile(new URL('../data/manifest.json', import.meta.url)));
const indexBytes = await readFile(new URL('../' + manifest.indexUrl, import.meta.url));
const properties = JSON.parse(manifest.indexUrl.endsWith('.gz') ? gunzipSync(indexBytes) : indexBytes);
const state = changes => ({...readUrlState(), ...changes});

test('global search covers all released records and composes city/year/collection filters', () => {
  assert.equal(filterProperties(properties, state()).length, manifest.verifiedPropertyCount);
  const result = filterProperties(properties, state({city:'RENTON',from:'2020',to:'2021',collection:'mainvue'}));
  assert.equal(result.length, 86);
  assert.ok(result.every(p=>p.city==='RENTON' && p.yearBuilt>=2020 && p.yearBuilt<=2021));
  assert.equal(filterProperties(properties, state({q:'1071 102nd pl se, Bellevue 98004'}))[0].pin, '0292000050');
  assert.equal(filterProperties(properties, state({q:'no such address anywhere'})).length, 0);
  for (const collection of manifest.collections) assert.equal(filterProperties(properties, state({collection:collection.id})).length, collection.propertyCount);
});

test('shared filter and property state survives round-trip without numeric PIN conversion', () => {
  const original = state({q:'1071 102ND PL SE',city:'BELLEVUE',collection:'murray-franklyn',from:'2019',to:'2021',sort:'year-desc',page:3,pin:'0292000050'});
  assert.deepEqual(readUrlState(buildUrlSearch(original)), original);
  const invalid = readUrlState('?from=oops&to=99999&page=-9&pin=123&sort=hack&review=flagged');
  assert.equal(invalid.page, 1);
  assert.equal(invalid.pin, '');
  assert.equal(invalid.from, '');
  assert.equal(invalid.to, '');
  assert.equal(invalid.sort, 'address');
  assert.equal('review' in invalid, false);
});

test('pagination exposes every property exactly once and clamps stale pages', () => {
  const count = Math.ceil(properties.length / PAGE_SIZE);
  const pages = Array.from({length:count}, (_,i)=>paginateProperties(properties,i+1).items);
  assert.equal(pages.at(-1).length, properties.length % PAGE_SIZE || PAGE_SIZE);
  assert.equal(new Set(pages.flat().map(p=>p.pin)).size, properties.length);
  assert.equal(paginateProperties(properties,999).page,count);
  assert.equal(paginateProperties([],999).items.length,0);
});

test('copied full addresses, street names, state names, and ZIP+4 resolve to the same parcel', () => {
  for (const q of ['25 92nd Ave NE', '25 92nd Ave NE, Bellevue, WA 98004', '25 92nd Avenue Northeast, Bellevue, Washington 98004-1234', '25 92nd Avenue North East Bellevue']) {
    assert.deepEqual(filterProperties(properties, state({q})).map(p => p.pin), ['1872900047'], q);
  }
  assert.equal(filterProperties(properties, state({q:'1872900047'}))[0].pin, '1872900047');
  assert.equal(filterProperties(properties, state({q:'25 92nd Avenue NE Seattle'})).length, 0, 'a contradictory city is not discarded');
  const samples = [{...properties[0], address:'25 92ND AVE NE'}, {...properties[0], pin:'9999999999', address:'125 92ND AVE NE'}];
  assert.equal(filterProperties(samples, state({q:'25 92nd'})).length, 1, 'house number must be a complete token');
});

test('near matches are suggestions only, keeping the entered house number', () => {
  const q = '25 92nd Ave NE Belleuve';
  assert.equal(filterProperties(properties, state({q})).length, 0);
  assert.equal(suggestProperties(properties, q)[0].pin, '1872900047');
  assert.ok(suggestProperties(properties, q).every(p => p.address.startsWith('25 ')));
  assert.equal(suggestProperties(properties, 'no such address anywhere').length, 0);
});

test('outbound evidence links remain HTTPS county sources', () => {
  assert.equal(safeCountyUrl('javascript:alert(1)'), null);
  assert.equal(safeCountyUrl('https://kingcounty.gov.example.com/a'), null);
  assert.equal(safeCountyUrl('http://blue.kingcounty.com/a'), null);
  assert.equal(safeCountyUrl('https://blue.kingcounty.com.evil.example/a'), null);
  assert.equal(safeCountyUrl('https://blue.kingcounty.com/Assessor/eRealProperty/Detail.aspx?ParcelNbr=0292000050'), 'https://blue.kingcounty.com/Assessor/eRealProperty/Detail.aspx?ParcelNbr=0292000050');
});
