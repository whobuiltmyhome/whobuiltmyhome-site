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


def normalized(value):
    return re.sub(r'\s+', ' ', re.sub(r'[.,]', '', value.upper())).strip()


def source_entity_id(seller, document_day, recorded_day, entities):
    """Independently reproduce the reviewed seller-to-entity policy."""
    exact = next((e for e in entities.values()
                  if seller in e['aliases'] and
                  all(e['from'] <= day <= e['through'] for day in (document_day, recorded_day))), None)
    if exact:
        return exact['id']
    in_window = all('1976-01-01' <= day <= '2026-09-04'
                    for day in (document_day, recorded_day))
    if not in_window:
        return None
    if (any(k in seller for k in ('MURRAY FRANKLYN', 'MURRAY FRANKLIN')) and
            any(k in seller for k in ('HOMES', 'DEVELOPMENT', 'LAND ACQUISITIONS', 'WEST', 'INC'))):
        return 'historical-murray-franklyn-company'
    if (any(k in seller for k in ('CAMWEST', 'CAM WEST')) and
            any(k in seller for k in ('DEVELOPMENT', 'HOMES', 'LLC', 'INC', 'CAMWEST'))):
        return 'camwest-named-company'
    if any(k in seller for k in ('CONNER HOMES', 'CONNER DEVELOPMENT', 'CONNER-JARVIS')):
        return 'conner-homes-named-company'
    if any(k in seller for k in ('TOLL BROTHERS', 'TOLL BROS')):
        return 'toll-brothers-named-company'
    if any(k in seller for k in ('MAINVUE', 'MAIN VUE')):
        return 'mainvue-named-company'
    if 'LENNAR NORTHWEST' in seller:
        return 'lennar-northwest-named-company'
    if ('BURNSTEAD' not in seller or
            not any(k in seller for k in ('CONST', 'CONSTR', 'HOMES'))):
        return None
    has_rick = any(k in seller for k in ('RICK', 'RICH', 'ROCK', 'RUCK'))
    has_steve = any(k in seller for k in ('STEVE', 'STEVEN', 'STEVER', 'STEVEM'))
    if 'HOMES' in seller and not any(k in seller for k in ('CONST', 'CONSTR')):
        return 'historical-burnstead-homes'
    if has_rick and not has_steve:
        return 'historical-rick-burnstead-construction'
    if has_steve and not has_rick:
        return 'historical-steve-burnstead-construction'
    return 'historical-burnstead-construction'


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
                try:
                    document_day = datetime.strptime(row['DocumentDate'].strip(), '%m/%d/%Y').date().isoformat()
                    recorded_day = datetime.strptime(recording[:8], '%Y%m%d').date().isoformat()
                except ValueError:
                    continue
                if (row['SaleInstrument'].strip() not in ('2', '3') or
                        row['PropertyClass'].strip() not in ('7', '8')):
                    continue
                entity_id = source_entity_id(normalized(row['SellerName']), document_day,
                                             recorded_day, entities)
                if not entity_id:
                    continue
                collection = entities[entity_id]['collectionId']
                key = p, recording, collection
                if key in needed and entity_id in needed[key]:
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
    recovered = 0
    for p in new_pins:
        row = index[p]
        matches = [f for f in features[p] if normalize(f['attributes']['ADDR_FULL']) == normalize(row['address'])
                   and f['attributes']['ZIP5'] == row['zip']]
        if 'gis-primary-address-recovery' in row['reviewFlags']:
            recovered += 1
            matches = [f for f in matches
                       if f['attributes'].get('PRIMARY_ADDR') in (1, True, '1', 'Y', 'YES', 'TRUE')]
            identities = {(normalize(f['attributes']['ADDR_FULL']), f['attributes']['ZIP5'],
                           normalize(f['attributes']['POSTALCTYNAME']),
                           round(f['centroid']['y'], 6), round(f['centroid']['x'], 6))
                          for f in matches}
            assert len(identities) == 1, 'Recovered address is not one unique primary GIS feature'
        points = {(round(f['centroid']['y'], 6), round(f['centroid']['x'], 6)) for f in matches}
        assert points == {tuple(geometry['locations'][p])}, 'Uncorroborated public coordinate'
        assert {normalize(f['attributes']['POSTALCTYNAME']) for f in matches} == {normalize(row['city'])}
    audit = read(manifest['expansionAuditUrl'])
    assert recovered == sum(c['gisPrimaryAddressRecoveredPins'] for c in audit['collections'].values())
    print(json.dumps({'newPropertiesChecked': len(new_pins), 'companyRecordingParcelReferencesChecked': len(needed),
                      'countyLocationsChecked': len(new_pins), 'gisPrimaryAddressesChecked': recovered,
                      'mismatches': 0}))


if __name__ == '__main__':
    main()
