# Launch handoff

Updated November 13, 2026. See `analytics.md` for Analytics account and transport evidence.

## Project accounts

- Google: `whobuiltmyhome@gmail.com` for Analytics and Search Console.
- GitHub: `whobuiltmyhome`, repository `whobuiltmyhome/whobuiltmyhome-site`.
- Production: https://whobuiltmyhome.com/
- GitHub connector identity verified as `whobuiltmyhome` on November 13.

## Verified

- Live homepage: 16,025 homes across nine builders; Buchan filter: 2,975 homes.
- Buchan restoration: PR #11. Dedicated account policy: PR #12.
- November 12 checks: 19 Node tests and eight Python data/geometry tests passed.
- Dedicated GA4 stream `G-YG0TM1H4F3`: privacy settings, production transport, and production Realtime receipt verified. Acquisition reporting should be reviewed once real traffic accumulates.
- November 13: existing Search Console URL-prefix property ownership verified for the dedicated Google account using `google6cf7727a32fd35b3.html`. Keep this file deployed. Existing owners and history were not removed.
- Search Console sitemap status: Success, five discovered pages, last read November 12. Overview showed four indexed pages and six total search clicks.
- November 13 public checks: all five sitemap URLs return HTTP 200; robots.txt allows crawling and names the sitemap; the verification file serves Google's exact content.
- November 13 production mobile-emulation checks passed at 375, 390, and 430 CSS-pixel widths in Chromium: Buchan count, map status, address search, county-details link, clipboard contents, reopening shared parcel link, clearing filters, contact mailto target, and no document horizontal overflow. No page JavaScript errors were observed.
- Mobile test evidence: https://github.com/whobuiltmyhome/whobuiltmyhome-site/actions/runs/43490039482
- Repeatable check: `scripts/verify-mobile-launch.mjs`, workflow `Verify mobile launch flow`. It runs on changes to its test/workflow files and can be run manually. It checks the live production site.
- November 13: an independent-sender contact test addressed to `hello@whobuiltmyhome.com` was received in the dedicated `whobuiltmyhome@gmail.com` Inbox. The public contact email route is verified end to end.
- Standard free GA4 and standard public-repository GitHub Actions only. No paid upgrade or billing commitment was added.

## Remaining before complete handoff

1. Perform a physical-phone check of touch scrolling, keyboard behavior, map interaction, and opening a shared link. Mobile Chromium emulation passed; physical iOS/Android behavior was not tested.
2. Before external outreach, refresh the October 9 demo/outreach material to show the restored Buchan collection. No outreach was sent.
3. After a small soft launch, review actual user feedback and acquisition reporting. No revenue or traffic outcome is guaranteed.

## Data limitation

The independent eight-builder raw-source audit was not rerun successfully during Buchan restoration: the available source ZIPs did not match the pinned snapshot hashes. Existing source evidence was preserved; passing software tests do not prove every builder association. Retain the visible county-record association disclaimer and correction route. This audit remains necessary for a future data rebuild.

## Operations

Use `AGENTS.md` for account selection and `release.md` for publishing/rollback.
Use `analytics.md` for account settings and safe activation. Any future data rebuild must retain Buchan and pass the frozen-fixture restoration checks.
Do not put credentials, private mail, or raw county owner/seller exports in this public repository.
