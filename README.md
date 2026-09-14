# Who Built My Home

A free static King County property explorer. The initial release contains 2,975
verified address/company-sale associations in a combined Buchan collection.
These are historical company connections, not confirmed builders of the current
homes. John and William Buchan remain combined until entity attribution is reviewed.
The proposed ten brand collections are shown as awaiting evidence.

## Run locally

Requires Python 3 and Node 20 or later. No package installation, hosted database,
API service, or build step is needed to serve the site.

```sh
python3 -m http.server 8765
```

Open http://localhost:8765. Use HTTP instead of opening index.html directly,
because the browser fetches the local data files.

```sh
npm test
python3 -m unittest discover -s tests -p 'data*.py'
```

## Data

The browser reads `data/manifest.json` and its immutable index, then fetches
property evidence only when needed. The complete index participates in search.
No raw grantor, grantee, private owner, or buyer fields are included.

See [the data contract](docs/data-contract.md) for the deterministic export,
provenance, review labels, and input paths. Keep raw source evidence outside this
public repository. Do not replace a reviewed release with a keyword candidate scan.

The page offers official county parcel-map links. Home-level map geometry has
not been joined into this release; the prior city-center circles have been removed.

## Measurement and publishing

The existing GA4 stream ID is retained. Measurement is disabled in previews and
also disabled in production until the account settings described in
[analytics.md](docs/analytics.md) are verified. This avoids collecting residential
addresses through automatic URL/search events.

See the repository's pull request and deployment history for publication status,
and [release.md](docs/release.md) for publishing and rollback.
