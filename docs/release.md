# Release and rollback

Repository: https://github.com/whobuiltmyhome/whobuiltmyhome-site

The full searchable collection shipped in PR #1, commit
`5056883cafa9c7bc62f0aed16981dcfae7dff8fb`. The clustered map builds on that
release in `codex/clustered-property-map`. GitHub history and Pages deployment
status are authoritative for publication.

## Map release

- A lazy, clustered parcel map shares the existing search and filter results.
  It includes every matching record across list pages and opens the same evidence
  dialog from individual markers.
- All 2,975 existing records have exact PIN/street/ZIP matches to official county
  parcel centroids. Coordinates are approximate parcel locations; builder
  attribution and the existing evidence files remain unchanged.
- Leaflet and its clustering plugin are vendored locally with licenses.
  OpenStreetMap supplies the background tiles, with visible attribution,
  origin-only referrers and normal browser caching. No paid account was created.
- Search remains available when the optional map fails. Geometry has retry;
  tile failures show a notice. Missing locations are explicitly counted.
- Analytics stays disabled until the GA4 account settings in `analytics.md`
  are checked. No GA4 account change is part of this release.

## Verification

Twenty-four checks pass: twelve Python data/geometry checks and twelve Node
analytics/search/map checks. The DOM integration test runs the actual application
and vendored Leaflet libraries in jsdom, without loading external tiles. It covers
lazy loading, geometry failure and retry, cluster navigation, combined filters,
58 Bellevue matches across two list pages, marker-to-evidence opening, empty
results and hiding the map. Geometry regeneration from the same cached county
responses is deterministic. JavaScript syntax and patch whitespace also pass.

DOM tests do not establish visual or real-device performance. Browser/mobile
visual verification remains separate. Earlier local browser preview attempts
were blocked or timed out; no alternative browser surface was used to bypass
those restrictions. The standalone offline preview supports search and evidence;
its map is deliberately disabled with an explanation directing users to the site.

## Publish

1. Fetch `main` and reconcile any changes; do not overwrite unrelated work.
2. Run `npm ci`, `npm test`, and
   `python3 -m unittest discover -s tests -p 'data*.py'`.
3. Include the complete application, vendored assets, geometry and manifest in
   the pull request. Check the tree against the tested local files.
4. Merge the authorized change into `main`, respecting repository checks, and
   wait for the successful Pages deployment for that exact commit.
5. Check deployed HTML, JavaScript, CSS, vendor files and manifest/geometry
   against the tested release. Exercise the public browser when available.

`CNAME` remains `whobuiltmyhome.com`. No domain or hosting migration is needed.
Retain prior hashed data files for cached readers. Reverting the release commit
restores the previous list-only site without recomputing evidence.

## Other collections

The ten-brand roadmap still requires dated entity matching, evidence review and
construction attribution. The 28,131 candidate PINs and 362 held recovery cases
are not part of the published inventory. Adding the map approves no new builder
claims or properties. Parcel outlines and imagery are outside this map release.
