#!/usr/bin/env python3
"""Check every new public reference and location against pinned source records.

This separate check reads the finished artifacts. It never exports raw parties.
"""
import argparse
from collections import defaultdict
import csv
from datetime import datetime
import hashlib
import gzip
import io
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sales', required=True, type=Path)
    parser.add_argument('--cache-dir', required=True, type=Path)
    args = parser.parse_args()
    read = lambda path: json.loads(gzip.decompress((ROOT / path).read_bytes()) if str(path).endswith('.gz') else (ROOT / path).read_bytes())
    manifest = read('data/manifest.json')
    index = {p['pin']: p for p in read(manifest['indexUrl'])}
    details = read(manifest['detailsUrl'])
    geometry = read(manifest['geometryUrl'])
    entities = {e['id']: e for e in read('data/entity-policy.json')['entities']}
    expected = next(s['sha256'] for s in manifest['sources'] if s['name'] == 'Real Property Sales')
    assert hashlib.sha256(args.sales.read_bytes()).hexdigest() == expected
    needed, matched = {}, set()
    new_pins = set()
    for p, detail in details.items():
        for c in detail['connections']:
            if c['collectionId'] == 'buchan':
                continue
            new_pins.add(p)
            for recording in c['recordings']:
                needed[p, recording, c['collectionId']] = c['entityIds']
    recordings = {r for _, r, _ in needed}
    with zipfile.ZipFile(args.sales) as archive:
        with io.TextIOWrapper(archive.open(archive.namelist()[0]), encoding='latin1', newline='') as stream:
            for row in csv.DictReader(stream):
                recording = row['RecordingNbr'].strip()
                if recording not in recordings:
                    continue
                p = row['Major'].strip().zfill(6) + row['Minor'].strip().zfill(4)
                seller = re.sub(r'\s+', ' ', row['SellerName'].upper().replace('.', '').replace(',', '')).strip()
                for c in ('burnstead', 'quadrant'):
                    key = p, recording, c
                    if key not in needed:
                        continue
                    for e in (entities[e] for e in needed[key]):
                        if seller not in e['aliases']:
                            continue
                        document_day = datetime.strptime(row['DocumentDate'].strip(), '%m/%d/%Y').date().isoformat()
                        recorded_day = datetime.strptime(recording[:8], '%Y%m%d').date().isoformat()
                        if all(e['from'] <= d <= e['through'] for d in (document_day, recorded_day)) and row['SaleInstrument'].strip() in ('2', '3') and row['PropertyClass'].strip() in ('7', '8'):
                            matched.add(key)
    assert set(needed) == matched, 'Public transaction lacks matching qualified source evidence'
    hashes = {b['sha256'] for b in geometry['sourceBatches']}
    features = defaultdict(list)
    for path in args.cache_dir.glob('*.json'):
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() not in hashes:
            continue
        for feature in json.loads(raw)['features']:
            features[feature['attributes']['PIN']].append(feature)
    normalize = lambda value: re.sub(r'\s+', ' ', re.sub(r'[.,#]', ' ', str(value or '').upper())).strip()
    for p in new_pins:
        row = index[p]
        matches = [f for f in features[p] if normalize(f['attributes']['ADDR_FULL']) == normalize(row['address'])
                   and f['attributes']['ZIP5'] == row['zip']]
        points = {(round(f['centroid']['y'], 6), round(f['centroid']['x'], 6)) for f in matches}
        assert points == {tuple(geometry['locations'][p])}, 'Uncorroborated public coordinate'
        assert {normalize(f['attributes']['POSTALCTYNAME']) for f in matches} == {normalize(row['city'])}
    print(json.dumps({'newPropertiesChecked': len(new_pins), 'companyRecordingParcelReferencesChecked': len(needed),
                      'countyLocationsChecked': len(new_pins), 'mismatches': 0}))


if __name__ == '__main__':
    main()
