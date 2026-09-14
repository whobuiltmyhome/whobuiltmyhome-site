# Release and rollback

Source repository: https://github.com/whobuiltmyhome/whobuiltmyhome-site

Baseline inspected: `392d2e510a944f59c2d7956bc0ba23338c66336e`.
The public live HTML matched that revision when checked September 14, 2026.
Current implementation branch: `codex/static-explorer-analytics`.

## Ready for source review

- Static explorer with complete released-data search, combined filters, 50-result
  pages, URL state, and lazy source details.
- Combined Buchan collection with explicit evidence limits; planned collections
  remain unreleased and cannot be mistaken for verified inventories.
- Generated public data uses approved fields and immutable filenames. Original
  evidence stays outside the repository.
- Repaired analytics is prepared with the existing stream ID. The production
  switch remains false until the account setup in `analytics.md` is checked.

## Publish when repository access is available

1. Fetch current `main` and compare with the inspected baseline. Reconcile any
   changes made since this branch was prepared; do not force-push over them.
2. Run the data/analytics/search checks and inspect the browser preview.
3. Open a pull request containing the complete site and referenced data files.
4. Confirm the repository's actual Pages configuration and deployment branch.
   `CNAME` remains `whobuiltmyhome.com`; no domain/hosting migration is needed.
5. Merge and deploy the full commit as one release when authorized. Check the
   homepage, one shared filter URL, and one property URL on the actual domain.
   Verify analytics separately if it has been enabled after the account check.

Repository write access was confirmed on September 14, 2026 after the initial
implementation. This document describes the prepared release; the GitHub pull
request and deployment history are authoritative for its subsequent publication.
No domain migration or GA4 account edit is part of this release.

## Verification completed for this branch

Nineteen checks passed: ten deterministic data-contract checks and nine Node
checks for analytics field privacy, preview suppression, transport configuration,
combined search, review cohorts, URL state, pagination, and official source URLs.
JavaScript syntax and patch whitespace checks passed. The offline review artifact
bundles the exact app code and released JSON, with only its fetch transport
substituted to allow opening a single file.

Live browser interaction and visual/mobile checks remain pending. The remote
browser could not reach the local server, and its security policy rejected the
local preview URL. No alternate browser surface was used to bypass that block.
The offline preview's module syntax was checked; it has not been visually verified.
Actual GA4 delivery and account settings also remain unverified.

The manifest and its referenced immutable files belong to the same release.
Retain earlier data filenames while cached previous pages may reference them.
Keep a previous good commit and its data for rollback. Reverting the deployment
commit restores the earlier release without recomputing source evidence.

## Remaining work toward all ten collections

Resolve dated builder/company aliases, review ambiguous transactions, and
establish construction attribution before publishing the other brands. The
28,131 candidate PINs in the feasibility scan are not an approved release.
The one-building/one-unit identity policy and source-coverage limits remain
applicable. Separately join and validate official home coordinates before adding
an interactive home map. None of those tasks requires a hosted search backend.
