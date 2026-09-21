import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { gunzipSync } from 'node:zlib';
import { filterProperties, readUrlState, buildUrlSearch, paginateProperties, safeCountyUrl } from '../app.js';

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
  const count = Math.ceil(properties.length / 50);
  const pages = Array.from({length:count}, (_,i)=>paginateProperties(properties,i+1).items);
  assert.equal(pages.at(-1).length, properties.length % 50 || 50);
  assert.equal(new Set(pages.flat().map(p=>p.pin)).size, properties.length);
  assert.equal(paginateProperties(properties,999).page,count);
  assert.equal(paginateProperties([],999).items.length,0);
});

test('outbound evidence links remain HTTPS county sources', () => {
  assert.equal(safeCountyUrl('javascript:alert(1)'), null);
  assert.equal(safeCountyUrl('https://kingcounty.gov.example.com/a'), null);
  assert.equal(safeCountyUrl('http://blue.kingcounty.com/a'), null);
  assert.equal(safeCountyUrl('https://blue.kingcounty.com.evil.example/a'), null);
  assert.equal(safeCountyUrl('https://blue.kingcounty.com/Assessor/eRealProperty/Detail.aspx?ParcelNbr=0292000050'), 'https://blue.kingcounty.com/Assessor/eRealProperty/Detail.aspx?ParcelNbr=0292000050');
});
