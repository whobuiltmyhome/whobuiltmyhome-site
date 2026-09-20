"""Parcel matching and complete map-release reconciliation."""
import hashlib
import gzip
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('map_data', ROOT / 'scripts/build-map-data.py')
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


class GeometryTests(unittest.TestCase):
    def test_release_locations_partition_exact_published_membership(self):
        manifest = json.loads((ROOT / 'data/manifest.json').read_text())
        properties = json.loads(gzip.decompress((ROOT / manifest['indexUrl']).read_bytes()))
        raw = gzip.decompress((ROOT / manifest['geometryUrl']).read_bytes())
        geometry = json.loads(raw)
        digest = hashlib.sha256(raw).hexdigest()
        self.assertEqual(manifest['geometrySha256'], digest)
        self.assertEqual(manifest['geometryUrl'], f'data/geometry.{digest[:16]}.json.gz')
        self.assertEqual(geometry['indexSha256'], manifest['indexSha256'])
        self.assertEqual(geometry['source'], exporter.SOURCE)
        self.assertEqual(geometry['ruleVersion'], exporter.RULE)
        self.assertEqual(set(geometry['locations']) | set(geometry['excluded']), {p['pin'] for p in properties})
        self.assertFalse(set(geometry['locations']) & set(geometry['excluded']))
        self.assertEqual(len(geometry['locations']), manifest['mappedPropertyCount'])
        self.assertEqual(len(geometry['excluded']), manifest['unmappedPropertyCount'])
        self.assertEqual(len(geometry['locations']), manifest['verifiedPropertyCount'])
        self.assertGreaterEqual(sum(b['requested'] for b in geometry['sourceBatches']), len(properties))
        for point in geometry['locations'].values():
            self.assertEqual(len(point), 2)
            self.assertTrue(47 <= point[0] <= 47.9 and -122.6 <= point[1] <= -121)

    def test_match_requires_parcel_street_zip_and_unambiguous_valid_coordinates(self):
        property = {'pin': '0012345678', 'address': '1 EXAMPLE ST', 'zip': '98004'}
        feature = {'attributes': {'PIN': property['pin'], 'ADDR_FULL': '1 Example St.', 'ZIP5': '98004'},
                   'centroid': {'x': -122.1, 'y': 47.6}}
        self.assertEqual(exporter.select_location(property, [feature]), ([47.6, -122.1], None))
        for field, value in [('PIN', '0099999999'), ('ADDR_FULL', '2 EXAMPLE ST'), ('ZIP5', '98005')]:
            changed = json.loads(json.dumps(feature))
            changed['attributes'][field] = value
            self.assertIsNone(exporter.select_location(property, [changed])[0])
        conflicting = dict(feature, centroid={'x': -122.2, 'y': 47.6})
        self.assertEqual(exporter.select_location(property, [feature, conflicting])[1], 'ambiguous-geometry')
        for center in ({}, {'x': 0, 'y': 0}, {'x': 47.6, 'y': -122.1}, {'x': float('nan'), 'y': 47.6}):
            self.assertIsNone(exporter.select_location(property, [dict(feature, centroid=center)])[0])
        self.assertEqual(exporter.select_location(property, [])[1], 'no-county-match')

    def test_primary_address_recovery_requires_one_complete_primary_feature(self):
        pin = '0012345678'
        feature = {'attributes': {'PIN': pin, 'ADDR_FULL': '1 Example St.', 'ZIP5': '98004',
                                  'POSTALCTYNAME': 'Bellevue', 'PRIMARY_ADDR': 1},
                   'centroid': {'x': -122.1, 'y': 47.6}}
        expected = {'address': '1 EXAMPLE ST', 'zip': '98004', 'city': 'BELLEVUE',
                    'location': [47.6, -122.1]}
        self.assertEqual(exporter.select_primary_address(pin, [feature]), (expected, None))
        duplicate = json.loads(json.dumps(feature))
        self.assertEqual(exporter.select_primary_address(pin, [feature, duplicate]), (expected, None))
        nonprimary = json.loads(json.dumps(feature))
        nonprimary['attributes']['PRIMARY_ADDR'] = 0
        self.assertEqual(exporter.select_primary_address(pin, [nonprimary])[1], 'missing-primary-address')
        conflicting = json.loads(json.dumps(feature))
        conflicting['attributes']['ADDR_FULL'] = '2 Example St.'
        self.assertEqual(exporter.select_primary_address(pin, [feature, conflicting])[1],
                         'ambiguous-primary-address')


if __name__ == '__main__':
    unittest.main()
