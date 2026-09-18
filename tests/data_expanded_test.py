"""Expansion gates: preserve the frozen cohort and reject unsupported associations."""
from collections import Counter
import hashlib
import gzip
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

    def test_entire_buchan_cohort_and_its_evidence_are_preserved(self):
        base = builder.BASE
        original = read(base['detailsUrl'])
        actual = {p for p, r in self.index.items() if 'buchan' in r['collectionIds']}
        self.assertEqual(actual, set(original))
        for row in read(base['indexUrl']):
            p = row['pin']
            for field in ('id', 'pin', 'address', 'city', 'zip', 'yearBuilt', 'status'):
                self.assertEqual(self.index[p][field], row[field])
            c, = [c for c in self.details[p]['connections'] if c['collectionId'] == 'buchan']
            self.assertEqual(c['reviewFlags'], row['reviewFlags'])
            for field in ('firstCompanyRecording', 'recordings', 'notes'):
                self.assertEqual(c[field], original[p][field])

    def test_exact_aliases_and_dates_reject_false_matches(self):
        self.assertEqual(builder.entity_for('The Quadrant Corp.', '2018-01-01', '2018-01-02')['id'], 'quadrant-corporation')
        for name in ('QUADRANT REAL ESTATE LLC', 'QUADRANT CORPORAITON',
                     'TRI POINTE HOMES WASHINGTON INC +QUADRANT CORP',
                     'STEVEN BURNSTEAD CONSTRUCTION LLC', 'BURNSTEAD CONSTRUCTION CO',
                     'PRIVATE PERSON + RICK BURNSTEAD CONSTRUCTION LLC'):
            self.assertIsNone(builder.entity_for(name, '2018-01-01', '2018-01-02'))
        self.assertIsNone(builder.entity_for('QUADRANT CORPORATION', '2021-01-01', '2021-01-02'))
        self.assertIsNone(builder.entity_for('RICK BURNSTEAD CONSTRUCTION LLC', '2009-01-01', '2009-01-02'))
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
                           ('SellerName', 'BURNSTEAD CONSTRUCTION CO')]:
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
                if c['collectionId'] != 'buchan':
                    self.assertTrue(c['entityIds'])
                    self.assertIn('assessor-sale-association', c['reviewFlags'])
                    self.assertTrue(all(entities[e]['collectionId'] == c['collectionId'] for e in c['entityIds']))
                    self.assertTrue(1976 <= row['yearBuilt'] <= 2026)
            self.assertEqual(set(row['reviewFlags']), flags)
            self.assertEqual(set(detail['recordings']), {r for c in detail['connections'] for r in c['recordings']})
        flags = Counter(f for r in self.index.values() for f in r['reviewFlags'])
        self.assertEqual(flags, self.manifest['reviewCounts'])
        for c in self.manifest['collections']:
            count = sum(c['id'] in r['collectionIds'] for r in self.index.values())
            self.assertEqual(count, c['propertyCount'])
            self.assertEqual(c['status'], 'available' if count else 'planned')
        audit = read(self.manifest['expansionAuditUrl'])
        self.assertEqual(audit['entityPolicySha256'], hashlib.sha256((ROOT / 'data/entity-policy.json').read_bytes()).hexdigest())
        for c, a in audit['collections'].items():
            self.assertEqual(a['keywordCandidatePins'], a['publishedPins'] + a['heldPins'])
            self.assertEqual(a['heldPins'], sum(a['heldReasons'].values()))
            self.assertEqual(a['publishedPins'], sum(c in r['collectionIds'] for r in self.index.values()))


if __name__ == '__main__':
    unittest.main()
