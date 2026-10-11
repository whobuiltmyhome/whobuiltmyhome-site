"""Builder-view publication gates and unsupported-association checks."""
from collections import Counter
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('expanded', ROOT / 'scripts/build-expanded-data.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def read(path):
    data = (ROOT / path).read_bytes()
    return json.loads(gzip.decompress(data) if str(path).endswith('.gz') else data)


def release_bytes(path):
    data = (ROOT / path).read_bytes()
    return gzip.decompress(data) if str(path).endswith('.gz') else data


class ExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = read('data/manifest.json')
        cls.index = {r['pin']: r for r in read(cls.manifest['indexUrl'])}
        cls.details = read(cls.manifest['detailsUrl'])

    def test_release_contains_all_nine_active_builders_including_buchan(self):
        expected = {'buchan', 'burnstead', 'murray-franklyn', 'camwest', 'quadrant', 'conner',
                    'toll-brothers', 'mainvue', 'lennar'}
        self.assertEqual({c['id'] for c in self.manifest['collections']}, expected)
        self.assertEqual({c for row in self.index.values() for c in row['collectionIds']}, expected)
        self.assertTrue(all(row['collectionIds'] for row in self.index.values()))
        self.assertTrue(all(detail['connections'] for detail in self.details.values()))

    def test_reviewed_aliases_and_historical_business_names_reject_false_matches(self):
        self.assertEqual(builder.entity_for('The Quadrant Corp.', '2018-01-01', '2018-01-02')['id'], 'quadrant-corporation')
        self.assertEqual(builder.entity_for('BURNSTEAD CONSTRUCTION CO', '2005-01-01', '2005-01-02')['id'], 'historical-burnstead-construction')
        self.assertEqual(builder.entity_for('STEVEN BURNSTEAD CONSTRUCTION CO', '2005-01-01', '2005-01-02')['id'], 'historical-steve-burnstead-construction')
        self.assertEqual(builder.entity_for('RICK BURNSTEAD CONSTRUCTION CO', '2005-01-01', '2005-01-02')['id'], 'historical-rick-burnstead-construction')
        self.assertEqual(builder.entity_for('BURNSTEAD HOMES INC', '1992-01-01', '1992-01-02')['id'], 'historical-burnstead-homes')
        self.assertEqual(builder.entity_for('MURRAY FRANKLYN HOMES LLC', '2024-01-01', '2024-01-02')['id'], 'murray-franklyn-homes-llc')
        self.assertEqual(builder.entity_for('MURRAY FRANKLIN WEST INC', '1988-01-01', '1988-01-02')['id'], 'historical-murray-franklyn-company')
        self.assertEqual(builder.entity_for('CAMWEST DEVELOPMENT INC', '2005-01-01', '2005-01-02')['id'], 'camwest-named-company')
        self.assertEqual(builder.entity_for('CONNER HOMES COMPANY', '2005-01-01', '2005-01-02')['id'], 'conner-homes-named-company')
        self.assertEqual(builder.entity_for('TOLL BROS INC', '2022-01-01', '2022-01-02')['id'], 'toll-brothers-named-company')
        self.assertEqual(builder.entity_for('MAINVUE WA LLC', '2022-01-01', '2022-01-02')['id'], 'mainvue-named-company')
        self.assertEqual(builder.entity_for('LENNAR NORTHWEST INC', '2018-01-01', '2018-01-02')['id'], 'lennar-northwest-named-company')
        for name in ('QUADRANT REAL ESTATE LLC', 'QUADRANT CORPORAITON',
                     'TRI POINTE HOMES WASHINGTON INC +QUADRANT CORP',
                     'BURNSTEAD FREDERICK H', 'BURNSTEAD INVESTMENTS LLC',
                     'MURRAY FRANKLYN FAMILY TRUST', 'CONNER FAMILY TRUST',
                     'HENDRICKSON LENNARD', 'MAIN STREET VUE LLC'):
            self.assertIsNone(builder.entity_for(name, '2018-01-01', '2018-01-02'))
        self.assertIsNone(builder.entity_for('QUADRANT CORPORATION', '2021-01-01', '2021-01-02'))
        self.assertEqual(builder.entity_for('RICK BURNSTEAD CONSTRUCTION LLC', '2009-01-01', '2009-01-02')['id'], 'historical-rick-burnstead-construction')
        self.assertIsNone(builder.entity_for('QUADRANT CORPORATION', '2020-12-30', '2021-01-02'))

    def test_sale_gate_rejects_invalid_recordings_and_unreviewed_instruments(self):
        row = {'DocumentDate': '01/02/2018', 'RecordingNbr': '20180103000001',
               'SellerName': 'RICK BURNSTEAD CONSTRUCTION LLC', 'SaleInstrument': '3',
               'PropertyClass': '8', 'BuyerName': 'PRIVATE_BUYER_SENTINEL'}
        projected = builder.sale_evidence(row)
        self.assertEqual(projected['entityId'], 'rick-burnstead-construction-llc')
        self.assertNotIn('PRIVATE_', json.dumps(projected))
        for key, value in [('RecordingNbr', ''), ('RecordingNbr', '201813990001'),
                           ('SaleInstrument', '15'), ('PropertyClass', '3'),
                           ('SellerName', 'BURNSTEAD FREDERICK H')]:
            self.assertIsNone(builder.sale_evidence(dict(row, **{key: value})))

    def test_public_schema_membership_counts_and_hashes_reconcile(self):
        self.assertEqual(self.manifest['version'], 2)
        self.assertEqual(len(self.index), self.manifest['verifiedPropertyCount'])
        self.assertEqual(set(self.index), set(self.details))
        for label in ('index', 'details', 'geometry'):
            data = release_bytes(self.manifest[label + 'Url'])
            sha = hashlib.sha256(data).hexdigest()
            self.assertEqual(sha, self.manifest[label + 'Sha256'])
            self.assertEqual(self.manifest[label + 'Url'], f'data/{label}.{sha[:16]}.json.gz')
        entities = {e['id']: e for e in self.manifest['entities']}
        for p, row in self.index.items():
            self.assertEqual(set(row), {'id', 'pin', 'address', 'city', 'zip', 'yearBuilt', 'collectionIds', 'status', 'reviewFlags'})
            self.assertRegex(p, r'^\d{10}$')
            self.assertEqual(row['status'], 'associated')
            detail = self.details[p]
            self.assertEqual(set(detail), {'countyUrl', 'mapUrl', 'firstCompanyRecording', 'recordings', 'notes', 'addressStatus', 'builderStatus', 'connections'})
            self.assertEqual(detail['addressStatus'], 'verified')
            self.assertEqual(detail['builderStatus'], 'unconfirmed')
            self.assertEqual(set(row['collectionIds']), {c['collectionId'] for c in detail['connections']})
            self.assertEqual(len(row['collectionIds']), len(set(row['collectionIds'])))
            flags = set()
            for c in detail['connections']:
                self.assertEqual(set(c), {'collectionId', 'entityIds', 'firstCompanyRecording', 'recordings', 'notes', 'reviewFlags'})
                flags.update(c['reviewFlags'])
                self.assertTrue(c['recordings'])
                for recording in c['recordings']:
                    self.assertRegex(recording, r'^\d{12,14}$')
                if c['collectionId'] == 'buchan':
                    # The frozen recorder/crosswalk route does not establish
                    # the John/William split or expansion-style exact entity IDs.
                    self.assertEqual(c['entityIds'], [])
                else:
                    self.assertTrue(c['entityIds'])
                    self.assertIn('assessor-sale-association', c['reviewFlags'])
                self.assertTrue(all(entities[e]['collectionId'] == c['collectionId'] for e in c['entityIds']))
                self.assertTrue((1965 if c['collectionId'] == 'buchan' else 1976) <= row['yearBuilt'] <= 2026)
            self.assertEqual(set(row['reviewFlags']), flags)
            self.assertEqual(set(detail['recordings']), {r for c in detail['connections'] for r in c['recordings']})
        flags = Counter(f for r in self.index.values() for f in r['reviewFlags'])
        self.assertEqual(flags, self.manifest['reviewCounts'])
        for c in self.manifest['collections']:
            count = sum(c['id'] in r['collectionIds'] for r in self.index.values())
            self.assertEqual(count, c['propertyCount'])
            self.assertEqual(c['status'], 'available')
        audit = read(self.manifest['expansionAuditUrl'])
        self.assertEqual(audit['entityPolicySha256'], hashlib.sha256((ROOT / 'data/entity-policy.json').read_bytes()).hexdigest())
        for c, a in audit['collections'].items():
            self.assertEqual(a['keywordCandidatePins'], a['publishedPins'] + a['heldPins'])
            self.assertEqual(a['heldPins'], sum(a['heldReasons'].values()))
            self.assertEqual(a['publishedPins'], sum(c in r['collectionIds'] for r in self.index.values()))
            self.assertLessEqual(a['gisPrimaryAddressRecoveredPins'], a['publishedPins'])
        self.assertEqual(audit['collections']['mainvue']['publishedPins'], 981)
        self.assertEqual(audit['collections']['mainvue']['gisPrimaryAddressRecoveredPins'], 723)
        self.assertEqual(audit['collections']['murray-franklyn']['publishedPins'], 204)
        self.assertEqual(audit['collections']['murray-franklyn']['gisPrimaryAddressRecoveredPins'], 108)
        self.assertEqual(self.manifest['verifiedPropertyCount'], 16025)
        self.assertEqual(len(self.manifest['collections']), 9)
        self.assertEqual(set(self.manifest['reviewCounts']),
                         {'assessor-sale-association', 'minor-chronology-gap',
                          'multi-parcel-recording', 'land-only-evidence',
                          'chronology-review', 'gis-primary-address-recovery',
                          'legal-corroboration-missing', 'recording-crosswalk'})
        self.assertEqual(self.manifest['reviewCounts']['assessor-sale-association'], 13056)
        self.assertEqual(self.manifest['reviewCounts']['minor-chronology-gap'], 2341)
        self.assertEqual(self.manifest['reviewCounts']['multi-parcel-recording'], 1915)
        self.assertEqual(self.manifest['reviewCounts']['land-only-evidence'], 1766)
        self.assertEqual(self.manifest['reviewCounts']['chronology-review'], 214)
        self.assertEqual(self.manifest['reviewCounts']['gis-primary-address-recovery'], 831)
        self.assertEqual(self.manifest['reviewCounts']['legal-corroboration-missing'], 401)
        self.assertEqual(self.manifest['reviewCounts']['recording-crosswalk'], 105)
        self.assertEqual(self.manifest['priorityReviewPropertyCount'], 1814)
        self.assertEqual({source['name'] for source in self.manifest['sources']},
                         {'Legal', 'Lookup', 'Parcel', 'Real Property Sales', 'Residential Building'})
        self.assertEqual(audit['collections']['mainvue']['heldReasons'],
                         {'no-eligible-reviewed-company-sale': 66,
                          'not-current-single-building-single-unit': 3})
        self.assertEqual(audit['collections']['murray-franklyn']['heldReasons'],
                         {'missing-primary-address': 1,
                          'no-eligible-reviewed-company-sale': 4,
                          'not-current-single-building-single-unit': 2})

    def test_frozen_buchan_membership_evidence_and_map_locations_are_retained(self):
        spec = importlib.util.spec_from_file_location('restore', ROOT / 'scripts/restore-buchan.py')
        restore = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(restore)
        original_manifest, frozen = restore.frozen_release()
        original_pins = {row['pin'] for row in frozen['index']}
        restored_pins = {p for p, row in self.index.items() if 'buchan' in row['collectionIds']}
        self.assertEqual(restored_pins, original_pins)
        self.assertEqual(len(restored_pins), 2975)
        geometry = read(self.manifest['geometryUrl'])
        overlap = 0
        for original in frozen['index']:
            p = original['pin']
            row = self.index[p]
            for key in ('id', 'address', 'city', 'zip', 'yearBuilt', 'status'):
                self.assertEqual(row[key], original[key])
            connection, = [c for c in self.details[p]['connections'] if c['collectionId'] == 'buchan']
            for key in ('firstCompanyRecording', 'recordings', 'notes'):
                self.assertEqual(connection[key], frozen['details'][p][key])
            self.assertEqual(connection['reviewFlags'], original['reviewFlags'])
            self.assertEqual(geometry['locations'][p], frozen['geometry']['locations'][p])
            overlap += len(row['collectionIds']) > 1
        self.assertEqual(overlap, 6)
        source = self.manifest['frozenCollectionSources']['buchan']
        self.assertEqual(source['releaseId'], original_manifest['releaseId'])
        self.assertEqual(source['heldRecoveryCandidateCount'], 362)
        self.assertNotIn('john-f-buchan', {c['id'] for c in self.manifest['collections']})
        self.assertNotIn('william-e-buchan', {c['id'] for c in self.manifest['collections']})


if __name__ == '__main__':
    unittest.main()
