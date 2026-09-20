#!/usr/bin/env python3
"""Reproducible, conservative King County builder-company release.

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
COUNTY = 'https://blue.kingcounty.com/Assessor/eRealProperty/Detail.aspx?ParcelNbr='
MAP = 'https://gismaps.kingcounty.gov/parcelviewer2/?pin='
SOURCE_CATALOG = [
    {'asOf': '2026-09-04', 'name': 'Lookup', 'retrievedOn': '2026-09-13',
     'sha256': '27b5d492021bfdbd6b245f4890e068af1dda6a165bcaea3860616a11c468489e',
     'url': 'https://aqua.kingcounty.gov/extranet/assessor/Lookup.zip'},
    {'asOf': '2026-09-04', 'name': 'Parcel', 'retrievedOn': '2026-09-13',
     'sha256': 'e60e188614671eeeda303e30dac2a2608c7fc7930cb1d4e768f4bc0626e60316',
     'url': 'https://aqua.kingcounty.gov/extranet/assessor/Parcel.zip'},
    {'asOf': '2026-09-04', 'name': 'Real Property Sales', 'retrievedOn': '2026-09-13',
     'sha256': 'efd110440e9bde37186ca3751bb81a9e3253e8389c9486e02b1d8ec53d0c7c88',
     'url': 'https://aqua.kingcounty.gov/extranet/assessor/Real%20Property%20Sales.zip'},
    {'asOf': '2026-09-04', 'name': 'Residential Building', 'retrievedOn': '2026-09-13',
     'sha256': '2ee8fca58b6b436c27188fedcca1132230b085ec24312f34cd2a6d4067f5291d',
     'url': 'https://aqua.kingcounty.gov/extranet/assessor/Residential%20Building.zip'},
]
COLLECTION_CATALOG = {
    'burnstead': ('Burnstead', 'https://www.burnstead.com/builder-documents-1'),
    'murray-franklyn': ('Murray Franklyn', 'https://www.murrayfranklyn.com/ourdifference'),
    'camwest': ('CamWest', 'https://www.annualreports.com/HostedData/AnnualReportArchive/t/NYSE_TOL_2012.pdf'),
    'quadrant': ('Quadrant Homes', 'https://www.tripointehomes.com/blog/celebrating-55-years-of-homebuilding-in-the-pacific-northwest'),
    'conner': ('Conner Homes', 'https://www.connerhomes.com/about/'),
    'toll-brothers': ('Toll Brothers', 'https://www.annualreports.com/HostedData/AnnualReportArchive/t/NYSE_TOL_2012.pdf'),
    'mainvue': ('MainVue Homes', 'https://www.mainvuehomes.com/wa/about-mainvue'),
    'lennar': ('Lennar', 'https://www.lennar.com/new-homes/washington/seattle'),
}
REVIEW_FLAG_DESCRIPTIONS = {
    'assessor-sale-association': 'The Assessor directly associates this PIN with a sale by a reviewed company name. The deed image and original builder have not been independently confirmed.',
    'gis-primary-address-recovery': 'The released street, ZIP, postal city and parcel center use the county-designated primary GIS address because the Residential Building address was missing or did not match.',
    'chronology-review': 'The county construction year is at least three years after the earliest matching company recording. Structure identity and construction history need review; rebuilding is not established.',
    'land-only-evidence': 'Supporting Assessor sales include residential land-only classifications and no residential improved-property classification. This does not establish who built the current structure.',
    'minor-chronology-gap': 'The county construction year is one or two years after the earliest matching company recording. This date difference alone does not establish rebuilding or a different builder.',
    'multi-parcel-recording': 'The Assessor links a supporting recording to more than one parcel. Each home remains a distinct PIN.',
}
EVIDENCE_LABELS = {
    'associated': 'Builder-company match; builder unconfirmed',
    'assessor-sale-association': 'County sale-record match',
    'gis-primary-address-recovery': 'County primary-address match',
    'chronology-review': 'Construction chronology needs review',
    'land-only-evidence': 'Land-only classification in supporting sales',
    'minor-chronology-gap': 'One or two-year date difference',
    'multi-parcel-recording': 'Recording covers multiple parcels',
}
COLLECTION_KEYWORDS = {
    'burnstead': ('BURNSTEAD',),
    'camwest': ('CAMWEST', 'CAM WEST'),
    'conner': ('CONNER HOMES', 'CONNER DEVELOPMENT', 'CONNER-JARVIS'),
    'lennar': ('LENNAR NORTHWEST',),
    'mainvue': ('MAINVUE', 'MAIN VUE'),
    'murray-franklyn': ('MURRAY FRANKLYN', 'MURRAY FRANKLIN'),
    'quadrant': ('QUADRANT',),
    'toll-brothers': ('TOLL BROTHERS', 'TOLL BROS'),
}
GIS_PRIMARY_ADDRESS_RECOVERY = frozenset(('mainvue', 'murray-franklyn'))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def names(value):
    return re.sub(r'\s+', ' ', re.sub(r'[.,]', '', value.upper())).strip()


def collection_matches(collection, seller):
    return any(keyword in seller for keyword in COLLECTION_KEYWORDS[collection])


def entity_for(seller, document_date, recording_date):
    normalized = names(seller)
    historical = {entity['id']: entity for entity in POLICY['entities']}
    for entity in POLICY['entities']:
        if normalized in entity['aliases'] and all(entity['from'] <= day <= entity['through']
                                                     for day in (document_date, recording_date)):
            return entity
    if (any(keyword in normalized for keyword in COLLECTION_KEYWORDS['murray-franklyn']) and
            any(term in normalized for term in ('HOMES', 'DEVELOPMENT', 'LAND ACQUISITIONS', 'WEST', 'INC')) and
            all('1976-01-01' <= day <= '2026-09-04' for day in (document_date, recording_date))):
        return historical['historical-murray-franklyn-company']
    if (collection_matches('camwest', normalized) and
            any(term in normalized for term in ('DEVELOPMENT', 'HOMES', 'LLC', 'INC', 'CAMWEST')) and
            all('1976-01-01' <= day <= '2026-09-04' for day in (document_date, recording_date))):
        return historical['camwest-named-company']
    if (collection_matches('conner', normalized) and
            all('1976-01-01' <= day <= '2026-09-04' for day in (document_date, recording_date))):
        return historical['conner-homes-named-company']
    if (collection_matches('toll-brothers', normalized) and
            all('1976-01-01' <= day <= '2026-09-04' for day in (document_date, recording_date))):
        return historical['toll-brothers-named-company']
    if (collection_matches('mainvue', normalized) and
            all('1976-01-01' <= day <= '2026-09-04' for day in (document_date, recording_date))):
        return historical['mainvue-named-company']
    if (collection_matches('lennar', normalized) and
            all('1976-01-01' <= day <= '2026-09-04' for day in (document_date, recording_date))):
        return historical['lennar-northwest-named-company']
    if ('BURNSTEAD' not in normalized or
            not any(term in normalized for term in ('CONST', 'CONSTR', 'HOMES')) or
            not all('1976-01-01' <= day <= '2026-09-04' for day in (document_date, recording_date))):
        return None
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
    expected = next(s['sha256'] for s in SOURCE_CATALOG if s['name'] == source_name)
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
    universe = {c: set() for c in COLLECTION_KEYWORDS}
    sales = defaultdict(list)
    for row in rows(sales_path):
        p = pin(row)
        if not p:
            continue
        seller = names(row['SellerName'])
        for collection in universe:
            if collection_matches(collection, seller):
                try:
                    day = datetime.strptime(row['DocumentDate'], '%m/%d/%Y').date().isoformat()
                except ValueError:
                    continue
                if '1976-01-01' <= day <= '2026-12-31':
                    universe[collection].add(p)
        if any(collection_matches(c, seller) for c in universe):
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
    reasons, candidates, recovery_candidates = {}, {}, {}
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
            collections = {s['collectionId'] for s in sales[p]}
            if collections & GIS_PRIMARY_ADDRESS_RECOVERY:
                recovery_candidates[p] = {'id': 'king-wa:' + p, 'pin': p,
                                          'yearBuilt': int(b['YrBuilt']), 'status': 'associated'}
            else:
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
    recovery_pins = sorted(recovery_candidates)
    for start in range(0, len(recovery_pins), 200):
        result, sha = geo.fetch_batch(recovery_pins[start:start + 200], args.cache_dir)
        for feature in result['features']:
            grouped[feature['attributes']['PIN']].append(feature)
        batches.append({'sha256': sha, 'retrievedAt': result['retrievedAt'],
                        'requested': len(result['requestedPins']), 'returned': len(result['features'])})
        print(json.dumps({'countyRecoveryBatch': start // 200 + 1,
                          'of': (len(recovery_pins) + 199) // 200}), flush=True)
    candidates.update(recovery_candidates)
    # Count every Assessor PIN on supporting recordings, including held/non-keyword parcels.
    recording_pins = {s['recording']: set() for ss in sales.values() for s in ss}
    for row in rows(sales_path):
        if row['RecordingNbr'] in recording_pins and (p := pin(row)):
            recording_pins[row['RecordingNbr']].add(p)
    index, details = {}, {}
    geometry = {'version': 1, 'source': geo.SOURCE, 'coordinateOrder': 'latitude,longitude',
                'locationType': 'parcel-centroid', 'ruleVersion': geo.RULE,
                'locations': {}, 'excluded': {}, 'sourceBatches': []}
    released = {c: set() for c in universe}
    recovered = {c: set() for c in universe}
    flags_text = dict(REVIEW_FLAG_DESCRIPTIONS)
    for p, row in sorted(candidates.items()):
        features = grouped[p]
        target_collections = ({s['collectionId'] for s in sales[p]} &
                              GIS_PRIMARY_ADDRESS_RECOVERY)
        recovered_address = p in recovery_candidates
        if recovered_address:
            primary, reason = geo.select_primary_address(p, features)
            if reason:
                reasons[p] = reason
                continue
            row.update({k: primary[k] for k in ('address', 'zip', 'city')})
            location = primary['location']
        else:
            location, reason = geo.select_location(row, features)
            cities = {geo.normalize(f['attributes'].get('POSTALCTYNAME')) for f in features
                      if geo.normalize(f['attributes'].get('ADDR_FULL')) == row['address']
                      and f['attributes'].get('ZIP5') == row['zip']}
            if reason or len(cities) != 1 or not next(iter(cities), ''):
                if reason == 'address-mismatch' and target_collections:
                    primary, recovery_reason = geo.select_primary_address(p, features)
                    if primary:
                        row.update({k: primary[k] for k in ('address', 'zip', 'city')})
                        location = primary['location']
                        recovered_address = True
                    else:
                        reasons[p] = recovery_reason
                        continue
                else:
                    reasons[p] = reason or 'ambiguous-or-missing-postal-city'
                    continue
            else:
                row['city'] = cities.pop()
        if p not in index:
            index[p] = {**row, 'collectionIds': [], 'reviewFlags': []}
            details[p] = {'countyUrl': COUNTY + p, 'mapUrl': MAP + p, 'addressStatus': 'verified',
                          'builderStatus': 'unconfirmed', 'connections': []}
        # Every active builder row uses geometry reviewed in this build.
        geometry['locations'][p] = location
        for collection in universe:
            ss = [s for s in sales[p] if s['collectionId'] == collection]
            if not ss:
                continue
            first = min(s['recordedOn'] for s in ss)
            flags = ['assessor-sale-association']
            if recovered_address:
                flags.append('gis-primary-address-recovery')
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
            if recovered_address:
                recovered[collection].add(p)
    for detail in details.values():
        cs = detail['connections']
        detail.update(firstCompanyRecording=min(c['firstCompanyRecording'] for c in cs),
                      recordings=sorted({r for c in cs for r in c['recordings']}),
                      notes=sorted({n for c in cs for n in c['notes']}))
    audit = {'ruleVersion': 'reviewed-company-associations-v6', 'reviewedOn': '2026-09-20',
             'entityPolicySha256': digest((ROOT / 'data/entity-policy.json').read_bytes()), 'collections': {}}
    for collection, all_pins in universe.items():
        held = Counter(
            reasons.get(p, 'eligible-sale-not-released')
            if any(s['collectionId'] == collection for s in sales.get(p, ()))
            else 'no-eligible-reviewed-company-sale'
            for p in all_pins - released[collection]
        )
        assert 'eligible-sale-not-released' not in held
        audit['collections'][collection] = {'keywordCandidatePins': len(all_pins), 'publishedPins': len(released[collection]),
                                             'gisPrimaryAddressRecoveredPins': len(recovered[collection]),
                                             'heldPins': sum(held.values()), 'heldReasons': dict(sorted(held.items())),
                                             'scope': POLICY['limits'][collection]}
        assert len(all_pins) == len(released[collection]) + sum(held.values())
    manifest = {
        'version': 2,
        'entities': [{k: e[k] for k in ('id', 'name', 'collectionId', 'sourceUrl')}
                     for e in POLICY['entities']],
        'collections': [
            {'id': collection, 'name': COLLECTION_CATALOG[collection][0],
             'historySource': COLLECTION_CATALOG[collection][1], 'status': 'available',
             'propertyCount': len(released[collection]),
             'description': POLICY['limits'][collection]}
            for collection in COLLECTION_CATALOG
        ],
        'coverage': 'A partial view of homes linked to eight builders across King County. Coverage varies by builder, and a match does not confirm who built the current structure.',
        'evidenceScope': 'King County homes linked to reviewed builder-company names in county sale records. A match does not confirm who built the current structure.',
        'geometryAvailable': True,
        'geometryDescription': 'Approximate county parcel centers matched by parcel number, street address, and ZIP. These are not surveyed building locations.',
        'researchWindow': [1976, 2026],
        'researchWindowDescription': 'County sale records reviewed from 1976 through September 4, 2026. The 2026 period is incomplete.',
        'sourceAsOf': '2026-09-04',
        'sourceRetrievedOn': '2026-09-13',
        'sources': SOURCE_CATALOG,
    }
    public_rows = [index[p] for p in sorted(index)]
    for label, value in [('index', public_rows), ('details', details)]:
        raw = geo.packed(value)
        sha = digest(raw)
        url = f'data/{label}.{sha[:16]}.json.gz'
        (ROOT / url).write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
        manifest[label + 'Url'], manifest[label + 'Sha256'] = url, sha
    geometry.update(indexSha256=manifest['indexSha256'], sourceBatches=batches)
    raw = geo.packed(geometry)
    sha = digest(raw)
    manifest.update(geometryUrl=f'data/geometry.{sha[:16]}.json.gz', geometrySha256=sha,
                    mappedPropertyCount=len(geometry['locations']), unmappedPropertyCount=0,
                    postalSourceAsOf=sorted({b['retrievedAt'][:10] for b in batches}),
                    geometryRetrievedAt=max(b['retrievedAt'] for b in batches), generatedAt=args.generated_at,
                    releaseId='2026-09-20-king-county-builder-view-v6', ruleVersion=audit['ruleVersion'],
                    verifiedPropertyCount=len(index), expansionAuditUrl='data/expansion-audit.json',
                    reviewCounts=dict(Counter(f for r in public_rows for f in r['reviewFlags'])),
                    priorityReviewPropertyCount=sum(bool(set(r['reviewFlags']) & {'land-only-evidence', 'chronology-review'}) for r in public_rows))
    used_flags = set(manifest['reviewCounts'])
    manifest['reviewFlagDescriptions'] = {key: value for key, value in flags_text.items()
                                          if key in used_flags}
    manifest['evidenceLabels'] = {key: value for key, value in EVIDENCE_LABELS.items()
                                  if key == 'associated' or key in used_flags}
    (ROOT / manifest['geometryUrl']).write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
    (ROOT / 'data/expansion-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    temporary = ROOT / 'data/manifest.tmp'
    temporary.write_text(json.dumps(manifest, indent=2) + '\n')
    temporary.replace(ROOT / 'data/manifest.json')
    print(json.dumps({'total': len(index), **audit}), flush=True)


if __name__ == '__main__':
    main()
