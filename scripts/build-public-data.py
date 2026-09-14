#!/usr/bin/env python3
"""Project the frozen 2,975-address release into explicitly public static files.

This is an exporter, not a builder-attribution or candidate-approval pipeline.
Requires only Python's standard library. Raw evidence must stay outside the site.
"""

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

EXPECTED_COUNT = 2975
VERIFICATION_SHA256 = "1f06d5b3a931e4b0cb70eba281027595676b6893e552025063f595c7ef38b45a"
ASSESSOR_SHA256 = "c51d53e80ae134e368030bd4b879c23a8df46ad56ab96774682fc07aad722941"
SCHEMA_VERSION = 1
RULE_VERSION = "buchan-public-projection-1"
COUNTY_URL = "https://blue.kingcounty.com/Assessor/eRealProperty/Detail.aspx?ParcelNbr="
MAP_URL = "https://gismaps.kingcounty.gov/parcelviewer2/?pin="
INDEX_KEYS = frozenset(("id", "pin", "address", "city", "zip", "yearBuilt", "collectionIds", "status", "reviewFlags"))
DETAIL_KEYS = frozenset(("countyUrl", "mapUrl", "firstCompanyRecording", "recordings", "notes", "addressStatus", "builderStatus"))
CATALOG_NAMES = {
    "john-f-buchan": "John F. Buchan / John Buchan Homes",
    "william-e-buchan": "William E. Buchan / William Buchan Homes",
    "burnstead": "Burnstead",
    "murray-franklyn": "Murray Franklyn",
    "camwest": "CamWest",
    "quadrant": "Quadrant Homes",
    "conner": "Conner Homes",
    "toll-brothers": "Toll Brothers",
    "mainvue": "MainVue Homes",
    "lennar": "Lennar",
}
EVIDENCE_LABELS = {
    "associated": "Company association; builder unconfirmed",
    "land-only-evidence": "Land-only classification in supporting sales",
    "chronology-review": "Construction chronology needs review",
    "minor-chronology-gap": "One or two-year date difference",
    "recording-crosswalk": "County recording crosswalk used",
    "legal-corroboration-missing": "Legal description not independently corroborated",
    "multi-parcel-recording": "Recording covers multiple parcels",
}
FLAG_DESCRIPTIONS = {
    "land-only-evidence": "Supporting Assessor sales include residential land-only classifications and no residential improved-property classification. This does not establish who built the current structure.",
    "chronology-review": "The county construction year is at least three years after the earliest verified company recording. Structure identity and construction history need review; rebuilding is not established.",
    "minor-chronology-gap": "The county construction year is one or two years after the earliest verified company recording. This date difference alone does not establish rebuilding or a different builder.",
    "recording-crosswalk": "The Assessor recording-to-parcel crosswalk differs from the recorder index PIN. The verified address uses the Assessor crosswalk.",
    "legal-corroboration-missing": "The complete plat, lot, and block combination was not independently corroborated. The verified association uses the Assessor recording-to-parcel crosswalk.",
    "multi-parcel-recording": "The Assessor links a supporting recording to more than one parcel. Each public record remains a distinct verified PIN.",
}
SOURCE_NOTE_FLAGS = {
    "Assessor recording-number crosswalk differs from indexed PIN": "recording-crosswalk",
    "Full legal tuple not independently corroborated; recording-number crosswalk used": "legal-corroboration-missing",
    "Assessor associates this recording with multiple parcels": "multi-parcel-recording",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def json_bytes(value, pretty=False):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       indent=2 if pretty else None,
                       separators=None if pretty else (",", ":")) + "\n").encode("utf-8")


def sha256(content):
    return hashlib.sha256(content).hexdigest()


def read_pinned(path, expected_hash):
    content = path.read_bytes()
    require(sha256(content) == expected_hash,
            f"Unrecognized frozen source: {path.name}. Review and version a new release before exporting it.")
    return json.loads(content)


def verify_pin(pin):
    require(isinstance(pin, str) and re.fullmatch(r"[0-9]{10}", pin),
            "PIN must be a ten-digit string; never coerce numeric identifiers.")


def project_property(source, evidence):
    pin = source["pin"]
    verify_pin(pin)
    for field in ("street", "city", "zip"):
        require(isinstance(source[field], str) and source[field].strip(), f"Missing public {field}.")
    require(re.fullmatch(r"[0-9]{5}", source["zip"]), "Expected a verified five-digit ZIP.")
    raw_year = source["year_built"]
    require(raw_year in ("", "0") or (isinstance(raw_year, str) and re.fullmatch(r"[0-9]{4}", raw_year)),
            "Unexpected county construction year.")
    year = int(raw_year) if raw_year not in ("", "0") else None
    first_recording = source["first_verified_company_recording"]
    datetime.strptime(first_recording, "%Y-%m-%d")
    recordings = sorted(set(source["verified_recordings"]))
    require(recordings and all(isinstance(r, str) and re.fullmatch(r"[0-9]{12,14}", r) for r in recordings),
            "Unexpected verified recording identifier.")
    require(source["support_recording"] in recordings, "Support recording is outside the verified set.")

    # Join only the verified recording AND PIN. Never import parties or unreviewed deeds.
    sales = [sale for recording in recordings for sale in evidence["sales"].get(recording, [])
             if sale["PIN"] == pin]
    # PropertyClass lookup 4|7 and 4|8 is the basis of the frozen publication audit.
    # PropertyType describes a different dimension and must not replace this rule.
    has_land = any(sale["PropertyClass"] == "7" for sale in sales)
    has_improved = any(sale["PropertyClass"] == "8" for sale in sales)
    flags = []
    if has_land and not has_improved:
        flags.append("land-only-evidence")
    gap = year - int(first_recording[:4]) if year is not None else None
    if gap is not None and gap >= 3:
        flags.append("chronology-review")
    elif gap in (1, 2):
        flags.append("minor-chronology-gap")
    for note in source["notes"]:
        require(note in SOURCE_NOTE_FLAGS, "An unfamiliar source note requires public wording review.")
        flags.append(SOURCE_NOTE_FLAGS[note])
    flags = sorted(set(flags))
    notes = [FLAG_DESCRIPTIONS[flag] for flag in flags]
    if source["route"] == "Unique full legal tuple":
        notes.append("The recording was linked to this parcel through a unique complete plat, lot, and block combination. No matching Assessor sale row was available for this supporting route.")
    else:
        require(source["route"] == "Assessor recording number", "Unknown address-verification route.")
    if source.get("other_recordings_requiring_review"):
        notes.append("Additional recording links still require review and are excluded from the verified references shown here.")

    index_row = {
        "id": "king-wa:" + pin, "pin": pin,
        "address": source["street"], "city": source["city"], "zip": source["zip"],
        "yearBuilt": year, "collectionIds": ["buchan"], "status": "associated",
        "reviewFlags": flags,
    }
    detail_row = {
        "countyUrl": COUNTY_URL + pin, "mapUrl": MAP_URL + pin,
        "firstCompanyRecording": first_recording, "recordings": recordings,
        "notes": notes, "addressStatus": "verified", "builderStatus": "unconfirmed",
    }
    require(set(index_row) == INDEX_KEYS and set(detail_row) == DETAIL_KEYS, "Public allowlist changed.")
    return index_row, detail_row


def project_release(verification, evidence, catalog, generated_at):
    require(verification["summary"]["verified_total"] == EXPECTED_COUNT, "Unexpected source release count.")
    require(evidence["assessor_extract_date"] == "2026-09-04", "Unexpected Assessor extract date.")
    require(evidence["lookups"]["4|7"] == "Res-Land only" and
            evidence["lookups"]["4|8"] == "Res-Improved property", "PropertyClass meaning changed.")
    require(re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", generated_at),
            "Use an explicit UTC generation timestamp, YYYY-MM-DDTHH:MM:SSZ.")
    datetime.strptime(generated_at, "%Y-%m-%dT%H:%M:%SZ")
    rows, details = [], {}
    held = {row["pin"] for kind in ("original_review", "recovered_review") for row in verification[kind]}
    for source in sorted(verification["properties"], key=lambda row: row["pin"]):
        require(source["pin"] not in details, "Duplicate PIN in source release.")
        require(source["pin"] not in held, "Held candidate cannot be published.")
        row, detail = project_property(source, evidence)
        rows.append(row)
        details[row["pin"]] = detail
    require(len(rows) == EXPECTED_COUNT, "Only the complete 2,975-property release is supported.")
    flags = Counter(flag for row in rows for flag in row["reviewFlags"])
    priority_count = sum(bool({"land-only-evidence", "chronology-review"} & set(row["reviewFlags"])) for row in rows)
    require(flags["land-only-evidence"] == 52 and flags["chronology-review"] == 18 and
            flags["minor-chronology-gap"] == 162 and priority_count == 57,
            "Source chronology/land classification no longer reconciles to the reviewed audit.")

    collections = [{
        "id": "buchan", "name": "Buchan company associations", "status": "available",
        "propertyCount": len(rows),
        "description": "Verified addresses with historical Buchan company sale or deed associations. Current-structure builders are unconfirmed; the John F. Buchan / William E. Buchan split remains unreviewed.",
    }]
    require(catalog["status"] == "proposal_only", "Expected a proposed collection catalog.")
    require([c["id"] for c in catalog["collections"]] == list(CATALOG_NAMES), "Proposed launch collections changed.")
    for collection in catalog["collections"]:
        require(collection["state"] == "planned" and not collection["approved_legal_entity_ids"] and
                not collection["approved_grantor_aliases"], "This exporter does not approve entity mappings.")
        require(collection["display_name"] == CATALOG_NAMES[collection["id"]], "Unexpected collection label.")
        require(collection["history_source"].startswith("https://"), "History source must use HTTPS.")
        collections.append({
            "id": collection["id"], "name": CATALOG_NAMES[collection["id"]], "status": "planned",
            "propertyCount": 0, "description": "Planned research collection; no reviewed properties published under this brand yet.",
            "historySource": collection["history_source"],
        })
    index_content, detail_content = json_bytes(rows), json_bytes(details)
    index_hash, detail_hash = sha256(index_content), sha256(detail_content)
    manifest = {
        "version": SCHEMA_VERSION, "releaseId": "2026-09-14-buchan-associations-v1",
        "ruleVersion": RULE_VERSION, "verifiedPropertyCount": len(rows), "generatedAt": generated_at,
        "sourceAsOf": evidence["assessor_extract_date"], "sourceRetrievedOn": "2026-09-13",
        "postalSourceAsOf": sorted({row["postal_source_date"] for row in verification["properties"]}),
        "indexUrl": f"data/index.{index_hash[:16]}.json", "indexSha256": index_hash,
        "detailsUrl": f"data/details.{detail_hash[:16]}.json", "detailsSha256": detail_hash,
        "collections": collections, "evidenceLabels": EVIDENCE_LABELS,
        "reviewFlagDescriptions": FLAG_DESCRIPTIONS,
        "evidenceScope": "Verified current addresses and historical company associations. Builder attribution for the current structures has not been confirmed.",
        "coverage": "A curated Buchan-associated release in King County, Washington. Missing results do not establish that a builder was uninvolved. The planned ten collections are not yet a countywide inventory.",
        "researchWindow": [1976, 2026],
        "researchWindowDescription": "Recording-history research window, not continuous or complete historical coverage. County construction years are retained separately and can precede 1976.",
        "geometryAvailable": False,
        "geometryDescription": "This release has no reviewed home-level coordinates. County parcel maps remain available through property links.",
        "reviewCounts": dict(sorted(flags.items())), "priorityReviewPropertyCount": priority_count,
        "heldRecoveryCandidateCount": 362,
        "heldRecoveryDescription": "GIS-ZIP recovery candidates from the prior assessment remain outside this release pending validation.",
        "sourceSnapshots": {
            "finalVerificationSha256": VERIFICATION_SHA256,
            "independentAssessorEvidenceSha256": ASSESSOR_SHA256,
        },
        "sources": [{
            "name": source["local_file"].replace("_", " ").removesuffix(".zip"),
            "url": source["url"], "asOf": source["assessor_extract_date"],
            "retrievedOn": source["retrieved_on"], "sha256": source["sha256"],
        } for source in sorted(verification["source_metadata"], key=lambda item: item["local_file"])],
    }
    return manifest, index_content, detail_content


def atomic_write(path, content):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(content)
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verification", required=True, type=Path)
    parser.add_argument("--assessor-evidence", required=True, type=Path)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--generated-at", required=True, help="Explicit UTC timestamp makes releases reproducible.")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[1] / "data")
    args = parser.parse_args()
    verification = read_pinned(args.verification, VERIFICATION_SHA256)
    evidence = read_pinned(args.assessor_evidence, ASSESSOR_SHA256)
    catalog = json.loads(args.catalog.read_text())
    manifest, index, details = project_release(verification, evidence, catalog, args.generated_at)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    # Write immutable payloads first and swap the referencing manifest last.
    # Retain prior content-hashed payloads for rollback and in-flight readers.
    atomic_write(args.output_dir / Path(manifest["indexUrl"]).name, index)
    atomic_write(args.output_dir / Path(manifest["detailsUrl"]).name, details)
    atomic_write(args.output_dir / "manifest.json", json_bytes(manifest, pretty=True))
    print(json.dumps({"verifiedPropertyCount": len(verification["properties"]),
                      "indexBytes": len(index), "detailsBytes": len(details),
                      "manifest": str(args.output_dir / "manifest.json")}, indent=2))


if __name__ == "__main__":
    main()
