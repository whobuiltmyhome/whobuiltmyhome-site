# Launch handoff

Updated November 12, 2026. See `analytics.md` for the verified account and transport evidence.

## Project accounts

- Google: `whobuiltmyhome@gmail.com` for Analytics and Search Console.
- GitHub: `whobuiltmyhome`, repository `whobuiltmyhome/whobuiltmyhome-site`.
- Production: https://whobuiltmyhome.com/
- GitHub connector identity verified as `whobuiltmyhome` on November 12.

## Verified

- Live homepage: 16,025 homes across nine builders.
- Buchan filter: 2,975 homes, all 2,975 mapped; a restored home opens its
  county-record details and official source link.
- Local checks: 19 Node tests and eight Python data/geometry tests pass.
- Published restoration: PR #11; dedicated Google account policy: PR #12.
- The user-approved dedicated GA4 stream is `G-YG0TM1H4F3`. Privacy settings
  and real network payloads passed verification; the production gate is enabled.
- Standard free GA4 and public-repository standard GitHub Actions only. No paid
  upgrade or billing commitment was added.

## Still required for complete handoff

1. Confirm dedicated-account ownership of the existing Search Console property.
   Google sign-in and GA4 administration are complete; Search Console is separate.
2. Review acquisition reporting once traffic accumulates. Production Realtime
   receipt is verified: one active user and homepage page_view after deployment.
3. Recheck the five-page sitemap in Search Console; its earlier fetch error
   has not been verified as resolved. Public search-tool retrieval of the XML
   was unavailable on October 25, which does not establish a site error.
4. Confirm that `hello@whobuiltmyhome.com` delivers to a monitored project
   inbox. The site opens an email draft; delivery has not been tested.
5. Complete a real phone walkthrough of search, filters, map, evidence, and
   sharing. Desktop interaction and automated checks do not establish this.
6. Refresh the October 9 demo/outreach material to show the restored Buchan
   collection before using those materials publicly.

The independent eight-builder raw-source audit was not rerun successfully
during Buchan restoration: the available source ZIPs did not match the pinned
snapshot hashes. Existing source evidence was preserved; the passing tests
above are not a replacement for that independent source audit on a data rebuild.

## Operations

Use `AGENTS.md` for account selection and `release.md` for publishing/rollback.
Use `analytics.md` for account settings and safe activation. Any future data
rebuild must retain Buchan and pass the frozen-fixture restoration checks.
Do not put credentials, private mail, or raw county owner/seller exports in
this public repository.
