# Search and usage measurement

The existing live site's GA4 identifier is `G-B3FYWYWXTN`. Its earlier code sends
`query_sample` and residential address fields. The replacement module never
forwards these fields. It constructs only the events below from an allowlist.

| Event | Purpose | Custom fields |
| --- | --- | --- |
| `search_performed` | Settled nonempty search or explicit submitted search | query type and length, result count, has-results, selected city/collection, county-year range, review filter |
| `property_open` | Open supporting property evidence | constant evidence status |
| `source_click` | Follow an official source | King County property-details category |
| `filter_changed` | Change a filter | filter name only |

All manual events use the fixed canonical page URL and title. Referrers retain
only the origin; raw input, parcel identifiers, property URLs, and residential
addresses are omitted. City and collection values must appear in the released
catalog. Preview domains and localhost never load the Google tag. DNT, Global
Privacy Control, the GA opt-out flag, and local `wbmh.analytics.optout=1` suppress
reporting. Set those preferences before loading the page; after a preference
change, reload for full effect because an already loaded Google tag can still
generate automatic events. These are additional preference checks, not a promise to identify people
or measure every search.

## One account check before enabling

The site supports shareable URLs containing `q` and `pin`. The Google tag can
automatically collect these independently of manual events. The setting
`send_page_view: false` does not disable enhanced history-based pageviews.
Therefore `analytics-config.js` ships with `enhancedMeasurementReviewed: false`.
No Google tag loads until that explicit setting is true on the production domain.

For the web stream in Google Analytics Admin → Data streams:

1. Disable **Site search** automatic measurement. Do not create an automatic
   event that copies `q`, search input, or property address into an event field.
2. Disable **Page changes based on browser history events** in Page views'
   advanced settings. The app reports one canonical pageview on load.
3. Disable automatic **Outbound clicks**, **Form interactions**, and
   **File downloads**. The manual source-click event replaces URL-level
   click reporting; the app has no conversion form or download interaction.
4. Enable email and URL data redaction as additional protection. Redact
   `q`, `s`, `search`, `query`, `keyword`, `pin`, and `ParcelNbr`.
5. Check for additional tag destinations or custom event rules that collect
   raw search input. Confirm this is the intended property/stream.
6. Set `enhancedMeasurementReviewed` to true, then verify a production test
   visit and synthetic search in GA4 DebugView/Realtime and inspect its network
   event payloads. Confirm no query text, address, PIN, raw link URL, duplicate
   history pageviews, or automatic `view_search_results` events are present.

The code and mocked transport tests are completed locally. Account configuration,
actual event receipt, reporting dimensions, consent requirements, and historical
traffic have not been inspected. This change does not remove previously collected
analytics data. The production switch should not be turned on based on unit tests alone.

To report custom fields beyond the event counts, register event-scoped dimensions
for `query_type`, `city`, `collection`, `review_filter`, and `source`, plus an
event-scoped custom metric for `result_count`, as needed. A useful report is
searching sessions → property-opening sessions → source-clicking sessions.
Event counts are repeat actions and must not be presented as unique people.

## Bots and measurement limits

GA4 automatically excludes known bots. Google does not show the excluded count,
and this is not a definitive human/bot label for remaining traffic. Repeated
searches, engaged sessions, and evidence clicks are usage signals, not proof of
human identity. No fingerprinting, CAPTCHA, or purported human classifier is added.
Analytics blockers, opt-outs, consent choices, and network errors mean some
activity is never reported. Hosting request totals are a different metric from
browser searches and should not be equated with visitors.

Official references:

- [Manual pageviews and enhanced history measurement](https://developers.google.com/analytics/devguides/collection/ga4/views)
- [Enhanced measurement events and parameters](https://support.google.com/analytics/answer/9216061?hl=en)
- [Data redaction](https://support.google.com/analytics/answer/13544947?hl=en)
- [Avoiding personally identifiable information](https://support.google.com/analytics/answer/6366371?hl=en)
- [Known bot exclusion](https://support.google.com/analytics/answer/9888366?hl=en)

Documentation checked September 14, 2026.
