# Who Built My Home

A free static explorer of home builders across King County. The current view
contains 13,056 homes linked to eight builders through county property and sale
records. Coverage varies by builder, and a match does not by itself prove who
built the current home.

## Run locally

The site has no production build step or hosted database. Serve it over HTTP so
the browser can load its local data files:

```sh
python3 -m http.server 8765
```

Open http://localhost:8765. The test suite requires Node 20 or later and Python
3.9 or later:

```sh
npm ci
npm test
python3 -m unittest discover -s tests -p 'data*.py'
```

## Data

The browser reads `data/manifest.json` and the immutable search index first.
Home details and map geometry load only when needed. No raw owner, buyer,
grantor, grantee, or private seller fields are published.

The eight builder counts, source dates, content hashes, and coverage limits are
recorded in the manifest. See [the data contract](docs/data-contract.md) for the
deterministic export and validation rules. Raw source exports and GIS caches
must remain outside this public repository.

The optional map shows approximate parcel centers for every matching home.
Search and filters control the list and map together; list pagination never
limits the map. See [mapping.md](docs/mapping.md) for geometry and tile-provider
details.

## Measurement and publishing

The existing GA4 stream ID is retained, but measurement stays disabled until
the account settings in [analytics.md](docs/analytics.md) are verified. This
prevents automatic URL or search events from sending residential addresses.

GitHub pull requests and Pages deployment history are authoritative for the
published site. See [release.md](docs/release.md) for verification and rollback.
