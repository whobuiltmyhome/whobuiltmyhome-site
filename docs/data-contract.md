# Public data contract, version 1

The site publishes **2,975 distinct verified address/company associations** from the frozen September 13, 2026 Buchan verification release. Every current-structure builder is **unconfirmed**. A historical company transaction is not a construction attribution.

One neutral `buchan` collection is available. The John F. Buchan / William E. Buchan split is unreviewed. Ten proposed brand collections are marked `planned`; `propertyCount: 0` means no properties are published under that collection, not that the builder has no homes. Do not relabel neutral records based on a keyword or brand acquisition.

## Assets and loading

Fetch `data/manifest.json` first. `indexUrl` and `detailsUrl` are **relative to the site root**, not to the manifest directory. The index is complete; fetch the detail file only when a property is opened. Hashes cover the exact UTF-8 file bytes, including the trailing newline. Immutable filenames contain the first 16 hex characters of the SHA-256 digest. The full digest is in the manifest.

| File | Public fields |
| --- | --- |
| `manifest.json` | `version`, `releaseId`, `ruleVersion`, `verifiedPropertyCount`, `generatedAt`, `sourceAsOf`, `sourceRetrievedOn`, `postalSourceAsOf`, `indexUrl`, `indexSha256`, `detailsUrl`, `detailsSha256`, `collections`, evidence labels, review counts, coverage limitations and source provenance |
| `index.<hash>.json` | Array of `{id, pin, address, city, zip, yearBuilt, collectionIds, status, reviewFlags}` |
| `details.<hash>.json` | Object keyed by PIN: `{countyUrl, mapUrl, firstCompanyRecording, recordings, notes, addressStatus, builderStatus}` |

`pin` is always a ten-digit string, including leading zeroes; `id` is `king-wa:` plus PIN. `address` is the street address; city and ZIP are separate. `yearBuilt` is the county construction year as a number, or `null` when unknown. A county year can precede the 1976–2026 recording-history research window; keep it unchanged. `collectionIds` is an array to permit future independently reviewed overlapping associations without inflating the distinct-property count.

The index `status` is `associated`. Detail `addressStatus` is `verified`, and `builderStatus` is `unconfirmed`. `firstCompanyRecording` is an ISO calendar date of the earliest verified company recording, not the construction date or sale document date. `recordings` contains recording-identifier strings only. Display them as references. Details link to the county property record and parcel map; no unreviewed recording links are included.

There are no reviewed home-level coordinates in this release. `geometryAvailable` is false. Do not infer a property's coordinates from a city center or a neighborhood marker. Property-list operation does not depend on maps.

## Evidence and chronology rules

| Flag | Source-backed meaning | Properties |
| --- | --- | ---: |
| `land-only-evidence` | A verified recording/PIN sale has `PropertyClass=7` (Res-Land only), and none has `PropertyClass=8` (Res-Improved property) | 52 |
| `chronology-review` | County construction year is at least three years after the first company recording year | 18 |
| `minor-chronology-gap` | County construction year is one or two years after the first company recording year | 162 |
| `recording-crosswalk` | Assessor recording crosswalk differs from recorder-index PIN | 105 |
| `legal-corroboration-missing` | Complete legal tuple was not independently corroborated; Assessor recording crosswalk used | 401 |
| `multi-parcel-recording` | Assessor associates the supporting recording with multiple parcels | 15 |

The first two sets overlap: **57 distinct properties** need priority attribution review. A one-year gap alone is not rebuilding evidence. Neither a longer gap nor a land-only classification establishes rebuilding. The flags preserve uncertainty; they do not change the address verification outcome or claim a builder.

Land classification specifically uses the Assessor `PropertyClass` lookup family `4`, not `PropertyType` lookup family `1`. Those dimensions sometimes differ. Sales join on both the verified recording and PIN, so a multi-parcel recording cannot donate another parcel's classification. The 913 unique-legal-tuple address associations lack matching Assessor sales for that supporting route; absence of a land flag is not proof of improved-property construction.

Public notes come only from fixed reviewed templates. Raw seller, buyer, co-seller, owner, grantor, grantee, legal descriptions, cookie headers, arbitrary source notes, and local source paths are never projected. The exporter builds every object from an explicit field allowlist.

## Sources and release boundaries

The county extracts are dated **September 4, 2026**, retrieved September 13. Postal verification uses its separately recorded source dates. `generatedAt` records this projection build, not a new county refresh. Official data downloads: [King County Assessor](https://info.kingcounty.gov/assessor/DataDownload/default.aspx). Specific source ZIP URLs, extract dates, retrieval dates, and SHA-256 hashes are in the manifest. The source snapshot hashes bind this exporter to the reviewed verification and independent-assessor evidence files.

Only `final_verification.json.properties` is eligible for export. Original and recovered held candidates are rejected. The separate 362 GIS-ZIP recovery candidates remain unreleased. The full verified membership has a frozen SHA-256 fingerprint in the tests; replacing one property with an unreleased candidate fails even if the total remains 2,975. Candidate discovery counts, raw parties, and unreviewed proposed builder inventories are not public result rows.

## Reproduce and verify

Keep private evidence outside the public repository. Use Python 3.9 or later; no packages, network calls, or live county queries are required. `--verification` and `--assessor-evidence` must match the hashes pinned in the script. A new approved release requires a reviewed rule/snapshot update, not silently replacing these inputs.

```bash
python scripts/build-public-data.py \
  --verification /path/to/verification_work/final_verification.json \
  --assessor-evidence /path/to/verification_work/independent_assessor_evidence.json \
  --catalog /path/to/proposed_collection_catalog.json \
  --generated-at 2026-09-14T18:50:14Z

python -m unittest discover -s tests -p 'data*_test.py'
```

Reuse the same explicit generation timestamp to reproduce the manifest byte for byte. The same inputs always produce the same sorted index, detail bytes, filenames, and counts. The exporter checks count reconciliation, unique string PINs, held exclusions, known lookup meanings, proposed collection status, and source-grounded review totals before writing anything. Tests also cover privacy allowlisting, leading-zero identifiers, chronological edge cases, and cross-parcel classification isolation.

Payloads are written before the manifest, whose local replacement is atomic. Publish the manifest and referenced assets in one deployment snapshot; changing the manifest alone is insufficient. Retain prior hashed payloads for rollback and in-flight readers. This script does not deploy the site or delete earlier releases.
