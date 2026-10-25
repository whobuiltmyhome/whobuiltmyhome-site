# Launch handoff

Checked October 25, 2026. This is a status record, not a claim that Google
account setup or Analytics activation is complete.

## Project accounts

- Google: `whobuiltmyhome@gmail.com` for Analytics and Search Console.
- GitHub: `whobuiltmyhome`, repository `whobuiltmyhome/whobuiltmyhome-site`.
- Production: https://whobuiltmyhome.com/
- GitHub connector identity verified as `whobuiltmyhome` on October 25.

## Verified

- Live homepage: 16,025 homes across nine builders.
- Buchan filter: 2,975 homes, all 2,975 mapped; a restored home opens its
  county-record details and official source link.
- Local checks: 19 Node tests and eight Python data/geometry tests pass.
- Published restoration: PR #11; dedicated Google account policy: PR #12.
- Analytics retains existing measurement ID `G-B3FYWYWXTN` and stays disabled
  until the settings and event-receipt checks in `analytics.md` are completed.

## Still required for complete handoff

1. Sign into the dedicated Google account. Confirm ownership of the existing
   Search Console property and administration of the intended GA4 stream.
   Preserve history and existing access until the dedicated account works.
2. Apply the Analytics privacy settings, activate the production switch, and
   verify actual sanitized event receipt as described in `analytics.md`.
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
