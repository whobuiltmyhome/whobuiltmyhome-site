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
  const result = filterProperties(properties, state({city:'BELLEVUE',from:'1980',to:'1990',collection:'buchan'}));
  assert.equal(result.length, 58);
  assert.ok(result.every(p=>p.city==='BELLEVUE' && p.yearBuilt>=1980 && p.yearBuilt<=1990));
  assert.equal(filterProperties(properties, state({q:'2432 279th, Sammamish 98075'}))[0].pin, '0098000130');
  assert.equal(filterProperties(properties, state({q:'no such address anywhere'})).length, 0);
  for (const collection of manifest.collections) assert.equal(filterProperties(properties, state({collection:collection.id})).length, collection.propertyCount);
});

test('review filters retain exact caution cohorts', () => {
  assert.equal(filterProperties(properties, state({review:'land-only-evidence'})).length, manifest.reviewCounts['land-only-evidence']);
  assert.equal(filterProperties(properties, state({review:'chronology-review'})).length, manifest.reviewCounts['chronology-review']);
  const clear = filterProperties(properties, state({review:'none'}));
  const flagged = filterProperties(properties, state({review:'flagged'}));
  assert.equal(clear.length + flagged.length, properties.length);
});

test('shared filter and property state survives round-trip without numeric PIN conversion', () => {
  const original = state({q:'2432 279TH DR SE',city:'SAMMAMISH',collection:'buchan',from:'2000',to:'2010',review:'none',sort:'year-desc',page:3,pin:'0098000130'});
  assert.deepEqual(readUrlState(buildUrlSearch(original)), original);
  const invalid = readUrlState('?from=oops&to=99999&page=-9&pin=123&sort=hack');
  assert.equal(invalid.page, 1);
  assert.equal(invalid.pin, '');
  assert.equal(invalid.from, '');
  assert.equal(invalid.to, '');
  assert.equal(invalid.sort, 'address');
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
  assert.equal(safeCountyUrl('http://blue.kingcounty.gov/a'), null);
  assert.equal(safeCountyUrl('https://blue.kingcounty.gov/Assessor/eRealProperty/Detail.aspx?ParcelNbr=0098000130'), 'https://blue.kingcounty.gov/Assessor/eRealProperty/Detail.aspx?ParcelNbr=0098000130');
});
