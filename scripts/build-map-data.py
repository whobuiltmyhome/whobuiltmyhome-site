#!/usr/bin/env python3
"""Join public records to county parcel centroids, using serial cached queries.

Only exact PIN + normalized street + ZIP matches with one distinct centroid
are mapped. No geocoding, owner fields, city-center fallbacks, or new records.
Cache source responses outside the public repository. Reusing the cache gives
byte-identical geometry. County centroids are approximate parcel locations.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'https://services.arcgis.com/Ej0PsM5Aw677QF1W/arcgis/rest/services/PARCEL_ADDRESS_PUB_AREA_3069/FeatureServer/0'
FIELDS = 'OBJECTID,PIN,ADDR_FULL,ZIP5,POSTALCTYNAME,PRIMARY_ADDR'
RULE = 'exact-pin-street-zip-unique-parcel-centroid-v1'


def packed(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode()


def normalize(value):
    return re.sub(r'\s+', ' ', re.sub(r'[.,#]', ' ', str(value or '').upper())).strip()


def select_location(property, features):
    matching = [f for f in features if f['attributes']['PIN'] == property['pin']
                and normalize(f['attributes'].get('ADDR_FULL')) == normalize(property['address'])
                and f['attributes'].get('ZIP5') == property['zip']]
    if not matching:
        return None, 'address-mismatch' if features else 'no-county-match'
    points = set()
    for feature in matching:
        center = feature.get('centroid') or {}
        lat, lon = center.get('y'), center.get('x')
        if not all(type(v) in (int, float) and math.isfinite(v) for v in (lat, lon)):
            return None, 'missing-coordinate'
        if not (47.0 <= lat <= 47.9 and -122.6 <= lon <= -121.0):
            return None, 'coordinate-out-of-range'
        points.add((round(lat, 6), round(lon, 6)))
    if len(points) != 1:
        return None, 'ambiguous-geometry'
    return list(points.pop()), None


def fetch_batch(pins, cache):
    params = dict(where='PIN IN (' + ','.join("'" + pin + "'" for pin in pins) + ')',
                  outFields=FIELDS, returnGeometry='false', returnCentroid='true', outSR=4326,
                  f='json', resultRecordCount=1000, orderByFields='OBJECTID')
    key = hashlib.sha256(packed(params)).hexdigest()
    path = cache / (key + '.json')
    if path.exists():
        result = json.loads(path.read_text())
    else:
        features, offset = [], 0
        while True:
            params['resultOffset'] = offset
            request = urllib.request.Request(SOURCE + '/query',
                data=urllib.parse.urlencode(params).encode(),
                headers={'User-Agent': 'WhoBuiltMyHome/1.0 (+https://whobuiltmyhome.com/)'})
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = json.load(response)
            if payload.get('error') or not isinstance(payload.get('features'), list):
                raise ValueError('County query failed; refusing to publish incomplete responses')
            if payload.get('spatialReference', {}).get('wkid') != 4326:
                raise ValueError('County response must use WGS84')
            part = payload['features']
            features.extend(part)
            if not payload.get('exceededTransferLimit'):
                break
            if not part:
                raise ValueError('County pagination made no progress')
            offset += len(part)
        result = {'source': SOURCE, 'requestedPins': pins, 'features': features,
                  'retrievedAt': datetime.now(timezone.utc).isoformat()}
        path.write_bytes(packed(result))
    if result['source'] != SOURCE or result['requestedPins'] != pins:
        raise ValueError('Mismatched source cache')
    if any(f['attributes']['PIN'] not in pins for f in result['features']):
        raise ValueError('County returned an unrequested parcel')
    return result, hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache-dir', required=True, type=Path)
    args = parser.parse_args()
    if args.cache_dir.resolve().is_relative_to(ROOT):
        raise ValueError('Source cache must be outside the public repository')
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = ROOT / 'data/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    raw_index = (ROOT / manifest['indexUrl']).read_bytes()
    if hashlib.sha256(raw_index).hexdigest() != manifest['indexSha256']:
        raise ValueError('Index hash mismatch')
    properties = json.loads(raw_index)
    pins = sorted(p['pin'] for p in properties)
    if len(pins) != len(set(pins)) or any(not re.fullmatch(r'\d{10}', p) for p in pins):
        raise ValueError('Invalid published membership')
    grouped, batches = defaultdict(list), []
    for start in range(0, len(pins), 200):
        result, digest = fetch_batch(pins[start:start + 200], args.cache_dir)
        for feature in result['features']:
            grouped[feature['attributes']['PIN']].append(feature)
        batches.append({'sha256': digest, 'retrievedAt': result['retrievedAt'],
                        'requested': len(result['requestedPins']), 'returned': len(result['features'])})
        print(json.dumps({'batch': len(batches), 'requested': batches[-1]['requested'],
                          'returned': len(result['features'])}), flush=True)
    locations, excluded = {}, {}
    for property in properties:
        location, reason = select_location(property, grouped[property['pin']])
        if location is not None:
            locations[property['pin']] = location
        else:
            excluded[property['pin']] = reason
    geometry = {'version': 1, 'indexSha256': manifest['indexSha256'], 'coordinateOrder': 'latitude,longitude',
                'locationType': 'parcel-centroid', 'source': SOURCE, 'ruleVersion': RULE,
                'locations': locations, 'excluded': excluded, 'sourceBatches': batches}
    content = packed(geometry)
    digest = hashlib.sha256(content).hexdigest()
    filename = f'geometry.{digest[:16]}.json'
    (ROOT / 'data' / filename).write_bytes(content)
    manifest.update(geometryAvailable=bool(locations), geometryUrl='data/' + filename,
                    geometrySha256=digest, mappedPropertyCount=len(locations),
                    unmappedPropertyCount=len(excluded), geometrySource=SOURCE,
                    geometryRetrievedAt=max(b['retrievedAt'] for b in batches),
                    geometryDescription='Approximate county parcel centers matched by parcel number, street address, and ZIP. These are not surveyed building locations.',
                    releaseId='2026-09-14-buchan-associations-map-v1')
    temporary = manifest_path.with_suffix('.tmp')
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(manifest_path)
    print(json.dumps({'mapped': len(locations), 'unmapped': len(excluded),
                      'reasons': dict(Counter(excluded.values())), 'geometryBytes': len(content)}), flush=True)


if __name__ == '__main__':
    main()
