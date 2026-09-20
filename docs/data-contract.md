# Public data contract, version 2

The site publishes 13,056 distinct King County homes linked to eight builders
through county sale records. Every builder view is partial. A match can reflect
a home sale, land sale, or parcel transfer and does not certify who built the
current structure.

## Loading and fields

Read `data/manifest.json` first. Its index, details, and geometry URLs are
relative to the site root. Immutable filenames contain the first 16 characters
of each asset's SHA-256; the full hashes are in the manifest.

| Asset | Contract |
| --- | --- |
| Index | Array of `{id, pin, address, city, zip, yearBuilt, collectionIds, status, reviewFlags}` |
| Details | Object by PIN: `{countyUrl, mapUrl, firstCompanyRecording, recordings, notes, addressStatus, builderStatus, connections}` |
| Connection | `{collectionId, entityIds, firstCompanyRecording, recordings, notes, reviewFlags}` |
| Geometry | `[latitude, longitude]` parcel centers by PIN, exact index hash, matching rule, and source-batch hashes |
| Entity policy | Reviewed company aliases, date windows, source links, and excluded scope |
| Expansion audit | Candidate, included, and held PIN totals for each builder |

PINs are ten-digit strings. Each PIN appears once, but it can match more than
one builder. Builder counts therefore must not be added to infer the distinct
home total. `firstCompanyRecording` is the first supporting county recording,
not a construction date. Flat detail fields aggregate all connections for older
readers; the current interface presents each builder separately.

`countyUrl` points to the King County eReal Property details table. `mapUrl`
remains in the version-2 payload for compatibility but is not shown by the
current interface.

The manifest exposes only reviewed company display names and company-source
links. Raw seller, buyer, co-seller, owner, grantor, grantee, legal text, prices,
private notes, and local source paths are excluded. Public notes come from fixed
templates.

## Inclusion rules

`data/entity-policy.json` defines the allowed company names and date windows.
Matching normalizes case, whitespace, commas, and periods, then applies only the
documented terms. There is no fuzzy surname or successor-brand matching.

- Include valid county document dates and 12–14 digit recording identifiers.
- Include warranty or statutory-warranty instruments and residential land or
  improved-property classes only.
- Require a current parcel, exactly one residential building with one living
  unit, and a county year built from 1976 through 2026.
- Normally require one exact PIN, street, ZIP, postal city, and WGS84 parcel
  centroid match in King County GIS.
- MainVue and Murray Franklyn may use one complete county-designated primary GIS
  address when the Residential Building address is missing or stale. Conflicting
  or incomplete primary addresses remain excluded.
- Every builder match carries `assessor-sale-association`. Date, land-only, and
  multi-parcel conditions are stored as separate data notes.

Candidate totals are discovery universes, not estimates of all homes built by a
company. Every candidate is either included or assigned one terminal hold reason
in `data/expansion-audit.json`.

## Reproduction

The sales, residential-building, parcel, and lookup files are pinned to the
September 4, 2026 source hashes in the manifest. GIS response hashes and actual
retrieval timestamps are recorded separately. Keep all source exports and GIS
caches outside the public repository.

```sh
python scripts/build-expanded-data.py \
  --assessor-dir /path/to/assessor_exports \
  --sales /path/to/Real_Property_Sales.zip \
  --cache-dir /path/outside/repository/gis-cache \
  --generated-at 2026-09-20T21:56:03Z
npm test
python -m unittest discover -s tests -p 'data*.py'
```

Reuse the recorded timestamp and cached GIS responses for byte-identical output.
The exporter writes immutable payloads before replacing the manifest. Publish
the new assets and manifest together.
