# Clustered parcel map

The optional **Show map** panel uses locally vendored Leaflet 1.9.4 and
Leaflet.markercluster 1.5.3. Its geometry, CSS and JavaScript load when opened.
The list always works independently, including when map data fails to load.

## Geometry and coverage

The current builder view contains 13,056 parcel centers. Counts come from the
manifest; every included PIN has a matching centroid, with zero exclusions.
Each address matches its ten-digit PIN, normalized street and five-digit ZIP in
the official [King County parcel service](https://services.arcgis.com/Ej0PsM5Aw677QF1W/arcgis/rest/services/PARCEL_ADDRESS_PUB_AREA_3069/FeatureServer/0).
The query returns polygon centroids in WGS84 (`returnCentroid=true`,
`returnGeometry=false`, `outSR=4326`). These are approximate parcel centers;
they do not establish the location or builder of the current structure.

Serial batches request candidate PINs and allowlisted address fields; only
qualifying matches become published locations. No owner, buyer, grantor or tax-mailing fields are requested. Each
response is cached outside this repository. Raw response hashes, retrieval
timestamps, the exact search-index hash and matching-rule version are retained
in the immutable geometry file. Street normalization only handles case,
punctuation and whitespace. Different coordinates for the same matched
address, missing geometry and out-of-region coordinates are excluded.

```sh
python3 scripts/build-map-data.py --cache-dir /path/outside/repo/map-source-cache
```

Reuse the same source cache for byte-identical output; an uncached run queries
the current county data and requires reviewing any changed matches. The expansion exporter already includes geometry. Run the map-only exporter
to refresh geometry for the current published membership. It preserves the index and evidence bytes,
writes geometry first, and updates the manifest last. It does not deploy.

## Interaction

- Search, city, builder, and year filters feed the same complete
  filtered property array to the map and list.
- The map includes matching records across all pages. Pagination and sorting
  preserve the map position. A changed matching set fits its bounds.
- Clusters expand on click; individual markers open the existing evidence
  dialog. Keyboard activation is supported by Leaflet's markers and controls.
- **Fit results** restores the filtered extent. Panning does not filter the list.
- Missing locations are explicitly counted, with those records retained in
  the list. Zero matches clears the markers and disables Fit results.
- Hiding the map removes its tile layer; filter changes while hidden stay local.
- Geometry failures show a retry. Tile failures show a notice and keep markers
  and list available. Scroll-wheel zoom is off to preserve ordinary page scrolling.

## Background map and privacy

`map-config.js` contains the tile URL, attribution and maximum zoom. The initial
provider is the standard OpenStreetMap raster service, under its
[tile usage policy](https://operations.osmfoundation.org/policies/tiles/).
This public service has no SLA. No paid account, API key or hosting change was
created. Switch providers if usage or availability requires it.

Only an opened map requests tiles for its viewport. There is no offline tile
download, background geocoding, prefetch job, proxy or cache-bypass header.
Normal browser caching applies. Visible attribution and a map-issue link remain.
Tile images use `referrerPolicy: 'origin'`, so the provider receives the site's
origin, not search text, parcel identifiers or query parameters. The document's
no-referrer policy remains for other resources. Like any external tile service,
the provider receives ordinary network information and the requested map area.
Map browsing and filtering do not call the county API. A home's explicit county
link opens its official eReal Property details table.
GA4 stays disabled pending the existing account-settings review.

## Verification

`npm test` exercises the real app and vendored map libraries inside jsdom,
without network tile requests. It checks lazy loading, recovery from failed
geometry, clusters, combined filters, pagination, marker-to-evidence navigation,
empty results and hiding the map. Python tests check the full membership,
coordinate order/range, content hashes, exact matching and exclusion rules.
These DOM tests do not replace visual browser/mobile checks.

Vendored package archives from the npm registry:

| Package | Version | Archive SHA-256 |
| --- | --- | --- |
| Leaflet | 1.9.4 | `84c65a256e50657896f54c33bd857b6849ebe94c817803be818bf32a3dde0b77` |
| Leaflet.markercluster | 1.5.3 | `fc6b0b1d00b6c708ae54e43ee4a11ac345e41660e19f0a570190bb35babb1a1c` |

Their BSD-2-Clause and MIT license files are included beside the assets.
