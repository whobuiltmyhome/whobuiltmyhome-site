import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { gunzipSync } from 'node:zlib';
import { filterProperties, paginateProperties, readUrlState } from '../app.js';
import { validateGeometry, matchMapProperties } from '../property-map.js';

const root = new URL('../', import.meta.url);
const read = path => {
  const data = readFileSync(new URL(path, root));
  return JSON.parse(path.endsWith('.gz') ? gunzipSync(data) : data);
};
const manifest = read('data/manifest.json');
const properties = read(manifest.indexUrl);
const geometry = read(manifest.geometryUrl);

test('map uses all filtered IDs across pages, including empty and combined searches', () => {
  const locations = validateGeometry(geometry, manifest, properties);
  for (const query of ['', '?city=RENTON&from=2020&to=2021&collection=mainvue', '?city=SAMMAMISH&collection=murray-franklyn', '?q=not-a-real-address']) {
    const filtered = filterProperties(properties, readUrlState(query));
    const result = matchMapProperties(filtered, locations);
    assert.deepEqual(result.mapped.map(p => p.pin), filtered.map(p => p.pin));
    assert.equal(result.missing, 0);
    if (query.includes('RENTON')) {
      assert.equal(result.mapped.length, 86);
      assert.equal(paginateProperties(filtered, 1).items.length, 50);
    }
  }
});

test('missing coordinates stay in list; invalid, overlapping or mismatched geometry is rejected', () => {
  const data = structuredClone(geometry);
  const pin = properties[0].pin;
  delete data.locations[pin];
  data.excluded[pin] = 'no-county-match';
  const partial = { ...manifest, mappedPropertyCount: properties.length - 1, unmappedPropertyCount: 1 };
  const locations = validateGeometry(data, partial, properties);
  const { mapped, missing } = matchMapProperties(properties, locations);
  assert.equal(mapped.length, properties.length - 1);
  assert.equal(missing, 1);
  assert.equal(properties.length, manifest.verifiedPropertyCount);
  for (const edit of [d => { d.locations[pin] = [0, 0]; }, d => { d.indexSha256 = 'wrong'; }, d => { d.excluded[pin] = 'conflict'; }, d => { d.locations['0000000000'] = [47.6, -122.1]; }]) {
    const invalid = structuredClone(geometry);
    edit(invalid);
    assert.throws(() => validateGeometry(invalid, manifest, properties));
  }
});
