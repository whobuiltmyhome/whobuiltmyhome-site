"""Public-release gates; runnable without private source files or dependencies."""

import hashlib
import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("public_data", ROOT / "scripts/build-public-data.py")
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)
MEMBERSHIP_SHA256 = "3fe83e888574e6cc577ac74612e17d0718d9f556d946838a2a3210b703a6bd52"
HELD_CALIBRATION_PINS = {
    "0924069036", "3885807660", "6669070290", "7523700800",
    "7525530540", "8568010060", "9290850720",
}


class PublicReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / "data/manifest.json").read_text())
        cls.index_bytes = (ROOT / cls.manifest["indexUrl"]).read_bytes()
        cls.detail_bytes = (ROOT / cls.manifest["detailsUrl"]).read_bytes()
        cls.rows = json.loads(cls.index_bytes)
        cls.details = json.loads(cls.detail_bytes)

    def test_complete_release_membership_excludes_held_candidates(self):
        pins = [row["pin"] for row in self.rows]
        self.assertEqual(len(pins), 2975)
        self.assertEqual(len(set(pins)), 2975)
        self.assertEqual(self.manifest["verifiedPropertyCount"], 2975)
        self.assertEqual(pins, sorted(pins))
        # Hash of all sorted verified PINs prevents swapping held candidates into
        # a still-2,975-row release, including the 362 unreleased recovery cases.
        digest = hashlib.sha256(("\n".join(pins) + "\n").encode()).hexdigest()
        self.assertEqual(digest, MEMBERSHIP_SHA256)
        self.assertFalse(set(pins) & HELD_CALIBRATION_PINS)
        self.assertEqual(set(pins), set(self.details))

    def test_public_allowlist_identifier_and_evidence_semantics(self):
        for row in self.rows:
            self.assertEqual(set(row), exporter.INDEX_KEYS)
            self.assertIsInstance(row["pin"], str)
            self.assertRegex(row["pin"], r"^[0-9]{10}$")
            self.assertEqual(row["id"], "king-wa:" + row["pin"])
            self.assertEqual(row["status"], "associated")
            self.assertEqual(row["collectionIds"], ["buchan"])
            self.assertTrue(row["yearBuilt"] is None or type(row["yearBuilt"]) is int)
            self.assertTrue(set(row["reviewFlags"]) <= set(exporter.FLAG_DESCRIPTIONS))
            detail = self.details[row["pin"]]
            self.assertEqual(set(detail), exporter.DETAIL_KEYS)
            self.assertEqual(detail["addressStatus"], "verified")
            self.assertEqual(detail["builderStatus"], "unconfirmed")
            self.assertEqual(detail["countyUrl"], exporter.COUNTY_URL + row["pin"])
            self.assertEqual(detail["mapUrl"], exporter.MAP_URL + row["pin"])
            self.assertTrue(all(isinstance(r, str) and re.fullmatch(r"[0-9]{12,14}", r)
                                for r in detail["recordings"]))

    def test_manifest_assets_are_content_addressed_and_root_relative(self):
        for label, payload in (("index", self.index_bytes), ("details", self.detail_bytes)):
            digest = hashlib.sha256(payload).hexdigest()
            self.assertEqual(digest, self.manifest[label + "Sha256"])
            self.assertEqual(self.manifest[label + "Url"], f"data/{label}.{digest[:16]}.json")
        self.assertEqual(self.index_bytes, exporter.json_bytes(self.rows))
        self.assertEqual(self.detail_bytes, exporter.json_bytes(self.details))

    def test_planned_collections_have_no_invented_properties(self):
        available = [c for c in self.manifest["collections"] if c["status"] == "available"]
        planned = [c for c in self.manifest["collections"] if c["status"] == "planned"]
        self.assertEqual([c["id"] for c in available], ["buchan"])
        self.assertEqual(available[0]["propertyCount"], 2975)
        self.assertEqual([c["id"] for c in planned], list(exporter.CATALOG_NAMES))
        self.assertTrue(all(c["propertyCount"] == 0 for c in planned))

    def test_caution_counts_match_source_audit(self):
        count = lambda flag: sum(flag in row["reviewFlags"] for row in self.rows)
        self.assertEqual(count("land-only-evidence"), 52)
        self.assertEqual(count("chronology-review"), 18)
        self.assertEqual(count("minor-chronology-gap"), 162)
        priority = sum(bool(set(row["reviewFlags"]) & {"land-only-evidence", "chronology-review"})
                       for row in self.rows)
        self.assertEqual(priority, 57)
        self.assertEqual(priority, self.manifest["priorityReviewPropertyCount"])
        self.assertFalse(self.manifest["geometryAvailable"])


class ProjectionPolicyTests(unittest.TestCase):
    def setUp(self):
        self.source = {
            "pin": "0012345678", "street": "1 EXAMPLE ST", "city": "EXAMPLE", "zip": "98000",
            "year_built": "2000", "first_verified_company_recording": "2000-01-02",
            "support_recording": "20000102000001", "verified_recordings": ["20000102000001"],
            "notes": [], "route": "Assessor recording number",
            "company_sellers": ["PRIVATE_SELLER_SENTINEL"], "owner": "PRIVATE_OWNER_SENTINEL",
        }
        self.sale = {"PIN": "0012345678", "PropertyClass": "7", "PropertyType": "2",
                     "SellerName": "PRIVATE_SELLER_SENTINEL", "BuyerName": "PRIVATE_BUYER_SENTINEL"}
        self.evidence = {"sales": {"20000102000001": [self.sale]}}

    def test_land_flag_uses_property_class_and_never_guesses_builder(self):
        row, details = exporter.project_property(self.source, self.evidence)
        self.assertIn("land-only-evidence", row["reviewFlags"])
        self.assertEqual(details["builderStatus"], "unconfirmed")
        self.evidence["sales"]["20000102000001"].append(dict(self.sale, PropertyClass="8"))
        row, _ = exporter.project_property(self.source, self.evidence)
        self.assertNotIn("land-only-evidence", row["reviewFlags"])

    def test_sale_join_cannot_borrow_another_parcels_classification(self):
        self.sale["PIN"] = "0099999999"
        row, _ = exporter.project_property(self.source, self.evidence)
        self.assertNotIn("land-only-evidence", row["reviewFlags"])

    def test_chronology_rules_do_not_infer_rebuilding(self):
        for gap in (-1, 0, 1, 2, 3, 37):
            with self.subTest(gap=gap):
                self.source["year_built"] = str(2000 + gap)
                row, detail = exporter.project_property(self.source, self.evidence)
                self.assertEqual("chronology-review" in row["reviewFlags"], gap >= 3)
                self.assertEqual("minor-chronology-gap" in row["reviewFlags"], gap in (1, 2))
                self.assertEqual(detail["builderStatus"], "unconfirmed")
        self.source["year_built"] = ""
        row, _ = exporter.project_property(self.source, self.evidence)
        self.assertIsNone(row["yearBuilt"])

    def test_raw_parties_are_excluded_and_unreviewed_notes_fail_closed(self):
        row, detail = exporter.project_property(self.source, self.evidence)
        self.assertNotIn(b"PRIVATE_", exporter.json_bytes([row, detail]))
        self.source["notes"] = ["PRIVATE_NOTE_SENTINEL"]
        with self.assertRaisesRegex(ValueError, "public wording review"):
            exporter.project_property(self.source, self.evidence)

    def test_numeric_pin_and_changed_frozen_source_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "ten-digit string"):
            exporter.verify_pin(12345678)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "final_verification.json"
            path.write_text('{"properties": []}')
            with self.assertRaisesRegex(ValueError, "Unrecognized frozen source"):
                exporter.read_pinned(path, exporter.VERIFICATION_SHA256)


if __name__ == "__main__":
    unittest.main()
