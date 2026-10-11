#!/usr/bin/env python3
"""Merge the hash-verified frozen Buchan release into a builder release.

Preserve the original reviewed evidence and neutral company grouping. This is
a restoration, not a new county refresh or a John/William attribution review.
The same merge is applied by build-expanded-data.py on every future rebuild.
"""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / 'tests/fixtures/buchan'


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def frozen_release():
    manifest = read(SEED / 'manifest.json')
    values = {}
    for label in ('index', 'details', 'geometry'):
        raw = gzip.decompress((SEED / manifest[label + 'Url']).read_bytes())
        if hashlib.sha256(raw).hexdigest() != manifest[label + 'Sha256']:
            raise ValueError('Frozen Buchan input hash mismatch: ' + label)
        values[label] = json.loads(raw)
    return manifest, values


def merge_buchan(index, details, geometry, manifest, audit):
    base, frozen = frozen_release()
    for original in frozen['index']:
        p = original['pin']
        if p in index:
            for key in ('id', 'address', 'city', 'zip', 'yearBuilt', 'status'):
                if index[p][key] != original[key]:
                    raise ValueError('Buchan restoration conflicts with current property: ' + p)
        else:
            index[p] = deepcopy(original)
            index[p]['collectionIds'] = []
            index[p]['reviewFlags'] = []
            details[p] = deepcopy(frozen['details'][p])
            details[p]['connections'] = []
        detail = frozen['details'][p]
        connection = {
            'collectionId': 'buchan', 'entityIds': [],
            **{key: deepcopy(detail[key]) for key in ('firstCompanyRecording', 'recordings', 'notes')},
            'reviewFlags': list(original['reviewFlags']),
        }
        # Idempotent restoration keeps other independently reviewed connections.
        details[p]['connections'] = [c for c in details[p]['connections'] if c['collectionId'] != 'buchan'] + [connection]
        index[p]['collectionIds'] = sorted(set(index[p]['collectionIds']) | {'buchan'})
        index[p]['reviewFlags'] = sorted({f for c in details[p]['connections'] for f in c['reviewFlags']})
        geometry['locations'].setdefault(p, deepcopy(frozen['geometry']['locations'][p]))
    for detail in details.values():
        connections = detail['connections']
        detail.update(firstCompanyRecording=min(c['firstCompanyRecording'] for c in connections),
                      recordings=sorted({r for c in connections for r in c['recordings']}),
                      notes=sorted({n for c in connections for n in c['notes']}))
    collection = deepcopy(base['collections'][0])
    collection['name'] = 'Buchan'
    manifest['collections'] = [collection] + [c for c in manifest['collections'] if c['id'] != 'buchan']
    manifest['coverage'] = 'A partial view of homes linked to nine builder collections across King County. Coverage varies by builder, and a match does not confirm who built the current structure.'
    manifest['evidenceScope'] = 'King County home addresses with reviewed historical builder-company sale or deed associations. A match does not confirm who built the current structure.'
    manifest['reviewFlagDescriptions'] = {**base['reviewFlagDescriptions'], **manifest.get('reviewFlagDescriptions', {})}
    manifest['evidenceLabels'] = {**base['evidenceLabels'], **manifest.get('evidenceLabels', {})}
    manifest['sources'] = list({s['name']: s for s in base['sources'] + manifest['sources']}.values())
    manifest['frozenCollectionSources'] = {'buchan': {
        'releaseId': base['releaseId'], 'ruleVersion': base['ruleVersion'],
        'sourceSnapshots': base['sourceSnapshots'], 'restoredFromCommit': base['restoredFromCommit'],
        **{label + 'Sha256': base[label + 'Sha256'] for label in ('index', 'details', 'geometry')},
        'propertyCount': len(frozen['index']), 'heldRecoveryCandidateCount': base['heldRecoveryCandidateCount'],
        'heldRecoveryDescription': base['heldRecoveryDescription'],
    }}
    # Preserve the original GIS batch provenance as well as the expansion's.
    for batch in frozen['geometry']['sourceBatches']:
        if batch not in geometry['sourceBatches']:
            geometry['sourceBatches'].append(deepcopy(batch))
    audit['frozenCollectionRestorations'] = deepcopy(manifest['frozenCollectionSources'])
    audit['ruleVersion'] = 'reviewed-company-associations-v7-buchan-restored'
    audit['reviewedOn'] = '2026-10-11'
    return base


def write_release(index, details, geometry, manifest, audit):
    rows = [index[p] for p in sorted(index)]
    for label, value in (('index', rows), ('details', details)):
        raw = (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()
        sha = hashlib.sha256(raw).hexdigest()
        manifest[label + 'Url'] = f'data/{label}.{sha[:16]}.json.gz'
        manifest[label + 'Sha256'] = sha
        (ROOT / manifest[label + 'Url']).write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
    geometry['indexSha256'] = manifest['indexSha256']
    raw = (json.dumps(geometry, sort_keys=True, separators=(',', ':')) + '\n').encode()
    sha = hashlib.sha256(raw).hexdigest()
    manifest.update(geometryUrl=f'data/geometry.{sha[:16]}.json.gz', geometrySha256=sha,
                    verifiedPropertyCount=len(index), mappedPropertyCount=len(geometry['locations']),
                    unmappedPropertyCount=len(geometry['excluded']),
                    releaseId='2026-10-11-king-county-builders-buchan-restored-v7',
                    generatedAt=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    ruleVersion=audit['ruleVersion'],
                    reviewCounts=dict(Counter(f for row in rows for f in row['reviewFlags'])),
                    priorityReviewPropertyCount=sum(bool(set(row['reviewFlags']) & {'land-only-evidence', 'chronology-review'}) for row in rows))
    manifest['postalSourceAsOf'] = sorted(set(manifest['postalSourceAsOf']) | {b['retrievedAt'][:10] for b in geometry['sourceBatches']})
    manifest['geometryRetrievedAt'] = max(b['retrievedAt'] for b in geometry['sourceBatches'])
    (ROOT / manifest['geometryUrl']).write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
    (ROOT / 'data/expansion-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    (ROOT / 'data/manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


def main():
    manifest = read(ROOT / 'data/manifest.json')
    index = {row['pin']: row for row in read(ROOT / manifest['indexUrl'])}
    details = read(ROOT / manifest['detailsUrl'])
    geometry = read(ROOT / manifest['geometryUrl'])
    audit = read(ROOT / manifest['expansionAuditUrl'])
    merge_buchan(index, details, geometry, manifest, audit)
    write_release(index, details, geometry, manifest, audit)
    print(json.dumps({'total': len(index), 'buchan': 2975, 'builders': len(manifest['collections'])}))


if __name__ == '__main__':
    main()
