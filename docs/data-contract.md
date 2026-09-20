# Public data contract, version 2

The site publishes distinct King County addresses with historical company connections. **The builder of every current structure remains unconfirmed.** All nine available collections are partial; counts in `data/manifest.json` are published address counts, not estimates of all homes built by a brand.

The original 2,975 Buchan addresses and their collection-specific evidence are preserved exactly. John F. Buchan and William E. Buchan remain unresolved. The [version 1 contract](buchan-data-contract-v1.md) describes that frozen cohort. Evidence from another collection never approves a held Buchan association, even when the parcel has an independently eligible connection to another company.

## Loading and fields

Read `data/manifest.json` first. Its index, details and geometry URLs are relative to the site root. Immutable filenames contain the first 16 characters of the SHA-256 of their exact UTF-8 bytes, including the trailing newline; the full hashes are in the manifest. Search uses the complete index; details and geometry load on demand. Retain older hashed files for cached readers and rollback.

| Asset | Contract |
| --- | --- |
| Index | Array of `{id, pin, address, city, zip, yearBuilt, collectionIds, status, reviewFlags}` |
| Details | Object by PIN: `{countyUrl, mapUrl, firstCompanyRecording, recordings, notes, addressStatus, builderStatus, connections}` |
| Connection | `{collectionId, entityIds, firstCompanyRecording, recordings, notes, reviewFlags}` |
| Geometry | `[latitude, longitude]` parcel centers by PIN, explicit exclusions, exact index hash, matching rule and source-batch hashes |
| Entity policy | Exact reviewed corporate aliases, date windows, company sources and excluded scope |
| Expansion audit | Candidate PIN totals, published totals and mutually exclusive terminal hold reasons for each new collection |

PINs remain ten-digit strings. The index status is `associated`; details use `addressStatus: verified` and `builderStatus: unconfirmed`. Each PIN appears once. Collection counts may overlap and must not be summed to infer unique homes. `firstCompanyRecording` comes from a supporting recording date, never a construction claim. Flat detail fields aggregate the connections for older readers; the current UI renders evidence separately for each connection. Index review flags are the union of all connections, and the review filter explicitly applies to any connection.

The manifest exposes only reviewed corporate display names and their company-source URLs. Raw seller, buyer, co-seller, owner, grantor, grantee, legal text, prices, private notes and local source paths are excluded. Public notes come from fixed templates.

## Expansion publication rules

`data/entity-policy.json` defines the exact aliases and narrowly reviewed brand/business-name patterns. Normalize case, whitespace, commas and periods, then apply only the documented terms below. No fuzzy matching, surname matching, inferred affiliate identity or acquisition-based brand assignment is allowed.

- Burnstead: three named current LLCs plus historical county seller names containing `BURNSTEAD` and an explicit construction or homes business term, with supporting document and recording dates from 1976 through September 4, 2026. The [company's builder documents](https://www.burnstead.com/builder-documents-1) support the current LLCs; historical names are grouped for discovery without asserting legal succession.
- Murray Franklyn: county seller names containing `MURRAY FRANKLYN` or the `MURRAY FRANKLIN` spelling variant plus an explicit homes, development, land-acquisition, west, or incorporated business term, with supporting dates through September 4, 2026.
- CamWest: explicit `CAMWEST` or `CAM WEST` business seller names.
- Conner: explicit `CONNER HOMES`, `CONNER DEVELOPMENT`, or `CONNER-JARVIS` seller names; generic surname matches are excluded.
- Toll Brothers: explicit `TOLL BROTHERS` or `TOLL BROS` seller names.
- MainVue: explicit `MAINVUE` or `MAIN VUE` seller names.
- Lennar: explicit `LENNAR NORTHWEST` seller names; Lennart and other surname lookalikes are excluded.
- Quadrant: five reviewed corporate-name forms with both dates no later than December 31, 2020. The [company's history](https://www.tripointehomes.com/blog/celebrating-55-years-of-homebuilding-in-the-pacific-northwest) identifies The Quadrant Corporation. Later Tri Pointe entries, misspellings and combined sellers await separate review.
- Require valid county document dates and 12–14 digit recording identifiers with valid date prefixes. Only warranty/statutory warranty instruments (`SaleInstrument` 2/3) and residential land/improved classes (`PropertyClass` 7/8) qualify; lookup meanings are checked against the pinned county dictionary.
- Require a current parcel, exactly one residential building with one living unit, and county construction year 1976–2026. This narrower cohort applies only to the new collections.
- Normally require a nonempty Residential Building street and five-digit ZIP, the exact PIN/street/ZIP in county GIS, one postal city and one valid WGS84 parcel centroid. For MainVue and Murray Franklyn only, a missing or mismatched Residential Building address may be replaced by exactly one complete county-designated primary GIS address for the same PIN; zero, conflicting or invalid primary addresses remain held. Existing released address/year conflicts hold the new association.
- Every new connection carries `assessor-sale-association`: the county Assessor sale directly links the company and PIN; the deed image and original builder remain unreviewed.
- A connection using the narrowly scoped county primary-address fallback also carries `gis-primary-address-recovery`; its street, ZIP, postal city and centroid come from that GIS feature.
- Apply land-only, one/two-year or larger chronology-gap flags per connection. Multi-parcel flags count every Assessor PIN on a supporting recording, including other-company and held parcels. Another parcel cannot contribute its classification.

Candidate totals are keyword discovery universes, not verified inventory. Each candidate PIN is either published for that collection or held under one terminal reason. A missing result says nothing definitive about a company's involvement. The two Buchan attributions remain planned research, with no running background jobs implied.

## Reproduction

The Assessor sales, residential-building, parcel and lookup ZIPs are pinned to the September 4, 2026 snapshot hashes in the manifest. GIS response hashes and actual retrieval timestamps are recorded separately. Source caches must stay outside the public repository. Preserve the original base files and `tests/fixtures/buchan-manifest.json`.

```sh
python scripts/build-expanded-data.py \
  --assessor-dir /path/to/assessor_exports \
  --sales /path/to/Real_Property_Sales.zip \
  --cache-dir /path/outside/repository/expanded-source-cache \
  --generated-at 2026-09-20T13:30:00Z
npm test
python -m unittest discover -s tests -p 'data*.py'
```

Reuse the actual recorded generation timestamp and cached source responses for deterministic output. The exporter writes all payloads before replacing the manifest. Publish them together in one tested deployment. The original `build-public-data.py` intentionally produces only the frozen Buchan release; it is not the expansion entrypoint. The map-only exporter preserves current membership and evidence.
