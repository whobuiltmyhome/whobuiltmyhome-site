#!/usr/bin/env python3
"""Reproducible, conservative company-connection expansion of the frozen release.

Inputs and GIS response caches stay outside this public repository. Corporate
names are selected by the reviewed exact allowlist; no raw parties are exported.
The keyword universe is accounted for by PIN, with one terminal hold reason.
"""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('map_data', ROOT / 'scripts/build-map-data.py')
geo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geo)
POLICY = json.loads((ROOT / 'data/entity-policy.json').read_text())
BASE = json.loads((ROOT / 'tests/fixtures/buchan-manifest.json').read_text())
COUNTY = 'https://blue.kingcounty.com/Assessor/eRealProperty/Detail.aspx?ParcelNbr='
MAP = 'https://gismaps.kingcounty.gov/parcelviewer2/?pin='


def digest(data):
    return hashlib.sha256(data).hexdigest()


def names(value):
    return re.sub(r'\s+', ' ', re.sub(r'[.,]', '', value.upper())).strip()


def entity_for(seller, document_date, recording_date):
    normalized = names(seller)
    for entity in POLICY['entities']:
        if normalized in entity['aliases'] and all(entity['from'] <= day <= entity['through']
                                                     for day in (document_date, recording_date)):
            return entity
    if ('BURNSTEAD' not in normalized or
            not any(term in normalized for term in ('CONST', 'CONSTR', 'HOMES')) or
            not all('1976-01-01' <= day <= '2026-09-04' for day in (document_date, recording_date))):
        return None
    historical = {entity['id']: entity for entity in POLICY['entities']}
    has_rick = any(term in normalized for term in ('RICK', 'RICH', 'ROCK', 'RUCK'))
    has_steve = any(term in normalized for term in ('STEVE', 'STEVEN', 'STEVER', 'STEVEM'))
    if 'HOMES' in normalized and not any(term in normalized for term in ('CONST', 'CONSTR')):
        entity_id = 'historical-burnstead-homes'
    elif has_rick and not has_steve:
        entity_id = 'historical-rick-burnstead-construction'
    elif has_steve and not has_rick:
        entity_id = 'historical-steve-burnstead-construction'
    else:
        entity_id = 'historical-burnstead-construction'
    return historical[entity_id]
    return None


def rows(path):
    with zipfile.ZipFile(path) as archive:
        filename, = [n for n in archive.namelist() if n.lower().endswith('.csv')]
        with io.TextIOWrapper(archive.open(filename), encoding='latin1', newline='') as stream:
            for row in csv.DictReader(stream):
                yield {k: v.strip() for k, v in row.items()}


def pin(row):
    if not re.fullmatch(r'\d{1,6}', row['Major']) or not re.fullmatch(r'\d{1,4}', row['Minor']):
        return None
    return row['Major'].zfill(6) + row['Minor'].zfill(4)


def sale_evidence(row):
    try:
        day = datetime.strptime(row['DocumentDate'], '%m/%d/%Y').date().isoformat()
        recording = row['RecordingNbr']
        if not re.fullmatch(r'\d{12,14}', recording):
            return None
        recorded = datetime.strptime(recording[:8], '%Y%m%d').date().isoformat()
    except ValueError:
        return None
    entity = entity_for(row['SellerName'], day, recorded)
    if not entity or row['SaleInstrument'] not in ('2', '3') or row['PropertyClass'] not in ('7', '8'):
        return None
    # No buyer, price, private seller string, or raw deed content passes this boundary.
    return {'entityId': entity['id'], 'collectionId': entity['collectionId'],
            'recording': recording, 'recordedOn': recorded,
            'documentDate': day, 'propertyClass': row['PropertyClass']}


def building_address(building):
    zip_code = building['ZipCode'][:5]
    street = re.sub(r'\s+\d{5}(?:-\d{4})?\s*$', '', building['Address']).strip()
    return geo.normalize(street), zip_code


def source_file(path, source_name):
    expected = next(s['sha256'] for s in BASE['sources'] if s['name'] == source_name)
    if digest(path.read_bytes()) != expected:
        raise ValueError('Unreviewed source snapshot: ' + source_name)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assessor-dir', required=True, type=Path)
    parser.add_argument('--sales', required=True, type=Path)
    parser.add_argument('--cache-dir', required=True, type=Path)
    parser.add_argument('--generated-at', default=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
    args = parser.parse_args()
    datetime.strptime(args.generated_at, '%Y-%m-%dT%H:%M:%SZ')
    if args.cache_dir.resolve().is_relative_to(ROOT):
        raise ValueError('Raw source caches must stay outside the public repository')
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    sales_path = source_file(args.sales, 'Real Property Sales')
    buildings_path = source_file(args.assessor_dir / 'Residential_Building.zip', 'Residential Building')
    parcels_path = source_file(args.assessor_dir / 'Parcel.zip', 'Parcel')
    lookup_path = source_file(args.assessor_dir / 'Lookup.zip', 'Lookup')
    lookups = {(r['LUType'], r['LUItem']): r['LUDescription'] for r in rows(lookup_path)}
    assert lookups['4', '7'] == 'Res-Land only' and lookups['4', '8'] == 'Res-Improved property'
    assert lookups['6', '2'] == 'Warranty Deed' and 'Warranty' in lookups['6', '3']
    universe = {c: set() for c in ('burnstead', 'quadrant')}
    sales = defaultdict(list)
    for row in rows(sales_path):
        p = pin(row)
        if not p:
            continue
        seller = names(row['SellerName'])
        for collection in universe:
            if collection.upper() in seller:
                try:
                    day = datetime.strptime(row['DocumentDate'], '%m/%d/%Y').date().isoformat()
                except ValueError:
                    continue
                if '1976-01-01' <= day <= '2026-12-31':
                    universe[collection].add(p)
        if any(c.upper() in seller for c in universe):
            sale = sale_evidence(row)
            if sale:
                sales[p].append(sale)
    print(json.dumps({'keywordCandidates': {c: len(p) for c, p in universe.items()},
                      'eligibleSalesPins': len(sales)}), flush=True)
    buildings = defaultdict(list)
    for row in rows(buildings_path):
        p = pin(row)
        if p in sales:
            buildings[p].append(row)
    current = {p for row in rows(parcels_path) if (p := pin(row)) in sales}
    reasons, candidates = {}, {}
    for p in sales:
        bs = buildings[p]
        if p not in current or len(bs) != 1 or bs[0]['NbrLivingUnits'] != '1':
            reasons[p] = 'not-current-single-building-single-unit'
            continue
        b = bs[0]
        if not b['YrBuilt'].isdigit() or not 1976 <= int(b['YrBuilt']) <= 2026:
            reasons[p] = 'construction-year-outside-cohort'
            continue
        address, zipcode = building_address(b)
        if not address or not re.fullmatch(r'\d{5}', zipcode):
            reasons[p] = 'missing-assessor-address-or-zip'
            continue
        candidates[p] = {'id': 'king-wa:' + p, 'pin': p, 'address': address, 'zip': zipcode,
                         'yearBuilt': int(b['YrBuilt']), 'status': 'associated'}
    grouped, batches = defaultdict(list), []
    pins = sorted(candidates)
    for start in range(0, len(pins), 200):
        result, sha = geo.fetch_batch(pins[start:start + 200], args.cache_dir)
        for feature in result['features']:
            grouped[feature['attributes']['PIN']].append(feature)
        batches.append({'sha256': sha, 'retrievedAt': result['retrievedAt'],
                        'requested': len(result['requestedPins']), 'returned': len(result['features'])})
        print(json.dumps({'countyBatch': len(batches), 'of': (len(pins) + 199) // 200}), flush=True)
    # Count every Assessor PIN on supporting recordings, including held/non-keyword parcels.
    recording_pins = {s['recording']: set() for ss in sales.values() for s in ss}
    for row in rows(sales_path):
        if row['RecordingNbr'] in recording_pins and (p := pin(row)):
            recording_pins[row['RecordingNbr']].add(p)
    base_rows = json.loads((ROOT / BASE['indexUrl']).read_bytes())
    details = json.loads((ROOT / BASE['detailsUrl']).read_bytes())
    index = {r['pin']: r for r in base_rows}
    geometry = json.loads((ROOT / BASE['geometryUrl']).read_bytes())
    # Keep the original collection's complete evidence, independent of other sellers.
    for p, detail in details.items():
        detail['connections'] = [{'collectionId': 'buchan', 'entityIds': [],
                                 **{k: detail[k] for k in ('firstCompanyRecording', 'recordings', 'notes')},
                                 'reviewFlags': list(index[p]['reviewFlags'])}]
    released = {c: set() for c in universe}
    flags_text = BASE['reviewFlagDescriptions']
    flags_text['assessor-sale-association'] = 'The Assessor directly associates this PIN with a sale by a reviewed company name. The deed image and original builder have not been independently confirmed.'
    for p, row in sorted(candidates.items()):
        features = grouped[p]
        location, reason = geo.select_location(row, features)
        cities = {geo.normalize(f['attributes'].get('POSTALCTYNAME')) for f in features
                  if geo.normalize(f['attributes'].get('ADDR_FULL')) == row['address']
                  and f['attributes'].get('ZIP5') == row['zip']}
        if reason or len(cities) != 1 or not next(iter(cities), ''):
            reasons[p] = reason or 'ambiguous-or-missing-postal-city'
            continue
        row['city'] = cities.pop()
        if p in index and any((geo.normalize(index[p][k]) != geo.normalize(row[k]))
                              for k in ('address', 'zip', 'city', 'yearBuilt')):
            reasons[p] = 'conflict-with-existing-release'
            continue
        if p not in index:
            index[p] = {**row, 'collectionIds': [], 'reviewFlags': []}
            details[p] = {'countyUrl': COUNTY + p, 'mapUrl': MAP + p, 'addressStatus': 'verified',
                          'builderStatus': 'unconfirmed', 'connections': []}
            geometry['locations'][p] = location
        for collection in universe:
            ss = [s for s in sales[p] if s['collectionId'] == collection]
            if not ss:
                continue
            first = min(s['recordedOn'] for s in ss)
            flags = ['assessor-sale-association']
            if all(s['propertyClass'] == '7' for s in ss):
                flags.append('land-only-evidence')
            gap = row['yearBuilt'] - int(first[:4])
            if gap >= 3:
                flags.append('chronology-review')
            elif gap in (1, 2):
                flags.append('minor-chronology-gap')
            if any(len(recording_pins[s['recording']]) > 1 for s in ss):
                flags.append('multi-parcel-recording')
            connection = {'collectionId': collection, 'entityIds': sorted({s['entityId'] for s in ss}),
                          'firstCompanyRecording': first, 'recordings': sorted({s['recording'] for s in ss}),
                          'reviewFlags': sorted(flags), 'notes': [flags_text[f] for f in sorted(flags)]}
            details[p]['connections'].append(connection)
            index[p]['collectionIds'].append(collection)
            index[p]['reviewFlags'] = sorted(set(index[p]['reviewFlags']) | set(flags))
            released[collection].add(p)
    for detail in details.values():
        cs = detail['connections']
        detail.update(firstCompanyRecording=min(c['firstCompanyRecording'] for c in cs),
                      recordings=sorted({r for c in cs for r in c['recordings']}),
                      notes=sorted({n for c in cs for n in c['notes']}))
    audit = {'ruleVersion': 'reviewed-company-associations-v2', 'reviewedOn': '2026-09-18',
             'entityPolicySha256': digest((ROOT / 'data/entity-policy.json').read_bytes()), 'collections': {}}
    for collection, all_pins in universe.items():
        held = Counter(reasons.get(p, 'no-eligible-reviewed-company-sale') for p in all_pins - released[collection])
        audit['collections'][collection] = {'keywordCandidatePins': len(all_pins), 'publishedPins': len(released[collection]),
                                             'heldPins': sum(held.values()), 'heldReasons': dict(sorted(held.items())),
                                             'scope': POLICY['limits'][collection]}
        assert len(all_pins) == len(released[collection]) + sum(held.values())
    manifest = dict(BASE)
    manifest['version'] = 2
    manifest['entities'] = [{k: e[k] for k in ('id', 'name', 'collectionId', 'sourceUrl')} for e in POLICY['entities']]
    manifest['collections'] = [dict(c) for c in BASE['collections']]
    for c in manifest['collections']:
        if c['id'] in released:
            c.update(status='available', propertyCount=len(released[c['id']]), description=POLICY['limits'][c['id']])
    public_rows = [index[p] for p in sorted(index)]
    for label, value in [('index', public_rows), ('details', details)]:
        raw = geo.packed(value)
        sha = digest(raw)
        url = f'data/{label}.{sha[:16]}.json.gz'
        (ROOT / url).write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
        manifest[label + 'Url'], manifest[label + 'Sha256'] = url, sha
    geometry.update(indexSha256=manifest['indexSha256'], sourceBatches=geometry['sourceBatches'] + batches)
    raw = geo.packed(geometry)
    sha = digest(raw)
    manifest.update(geometryUrl=f'data/geometry.{sha[:16]}.json.gz', geometrySha256=sha,
                    mappedPropertyCount=len(geometry['locations']), unmappedPropertyCount=0,
                    postalSourceAsOf=sorted(set(BASE['postalSourceAsOf']) | {b['retrievedAt'][:10] for b in batches}),
                    geometryRetrievedAt=max(b['retrievedAt'] for b in batches), generatedAt=args.generated_at,
                    releaseId='2026-09-18-expanded-burnstead-associations-v2', ruleVersion=audit['ruleVersion'],
                    verifiedPropertyCount=len(index), expansionAuditUrl='data/expansion-audit.json',
                    coverage='Partial King County collections for Buchan, Burnstead and Quadrant company associations. A missing result does not establish that a company was uninvolved. Other brands await evidence review.',
                    reviewFlagDescriptions=flags_text, reviewCounts=dict(Counter(f for r in public_rows for f in r['reviewFlags'])),
                    priorityReviewPropertyCount=sum(bool(set(r['reviewFlags']) & {'land-only-evidence', 'chronology-review'}) for r in public_rows))
    manifest['evidenceLabels'] = {**BASE['evidenceLabels'], 'assessor-sale-association': 'Assessor sale association; deed image unreviewed'}
    (ROOT / manifest['geometryUrl']).write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
    (ROOT / 'data/expansion-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    temporary = ROOT / 'data/manifest.tmp'
    temporary.write_text(json.dumps(manifest, indent=2) + '\n')
    temporary.replace(ROOT / 'data/manifest.json')
    print(json.dumps({'total': len(index), **audit}), flush=True)


if __name__ == '__main__':
    main()
