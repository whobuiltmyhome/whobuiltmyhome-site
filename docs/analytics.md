# Search and usage measurement

The existing live site's GA4 identifier is `G-B3FYWYWXTN`. Its earlier code sends
`query_sample` and residential address fields. The replacement module never
forwards these fields. It constructs only the events below from an allowlist.

| Event | Purpose | Custom fields |
| --- | --- | --- |
| `search_performed` | Settled nonempty search or explicit submitted search | query type and length, result count, has-results, selected city/collection, county-year range |
| `property_open` | Open supporting property evidence | constant evidence status |
| `source_click` | Follow an official source | King County property-details category |
| `filter_changed` | Change a filter | filter name only |
| `share` | Successfully copy a property-evidence link | fixed method `copy_link` and content type `property_evidence`; no property ID or copied URL |

All manual events use an allowlisted canonical page URL, path, and title. The
released homepage, King County research guide, Burnstead page, and Quadrant page
have distinct identities. `/index.html` forms map to their canonical directory
paths; unrecognized paths fall back to the homepage identity instead of sending
arbitrary path segments. Query strings, fragments, and `document.title` never
provide measurement fields. Referrers retain
only the origin; raw input, parcel identifiers, property URLs, and residential
addresses are omitted. City and collection values must appear in the released
catalog. Preview domains and localhost never load the Google tag. DNT, Global
Privacy Control, the GA opt-out flag, and local `wbmh.analytics.optout=1` suppress
reporting. Set those preferences before loading the page; after a preference
change, reload for full effect because an already loaded Google tag can still
generate automatic events. These are additional preference checks, not a promise to identify people
or measure every search.

## Launch campaign attribution

Campaign values are captured once during module initialization, before the
explorer replaces its URL with search/filter state. Only these exact lowercase
values are accepted:

| URL field | Accepted values |
| --- | --- |
| `utm_source` | `agent_outreach`, `reddit`, `facebook`, `nextdoor`, `newsletter`, `living_snoqualmie`, `hoa`, `redmond_ridge` |
| `utm_medium` | `email`, `social`, `referral` |
| `utm_campaign` | `launch_2026_10` |

All three fields must appear exactly once and pass their allowlists. Partial,
duplicate, or unrecognized campaign tags use the fixed `unattributed` source and
campaign, with medium `none`. Visits without UTM tags get no campaign override;
their coarse referrer can still identify organic/referral traffic. The original
query string is not retained or sent. `utm_id`, `utm_term`, and `utm_content` values
are never copied; if present they receive a constant `not_collected` override.
Other arbitrary URL parameters are not measurement fields.

The accepted values use Google's documented `campaign_source`,
`campaign_medium`, and `campaign_name` configuration fields. They are included in
the Google tag configuration and manual events, independently of the cleaned
page URL. Example outreach link:

`https://whobuiltmyhome.com/?utm_source=agent_outreach&utm_medium=email&utm_campaign=launch_2026_10`

Use a community/source label rather than a person's name, email, address, or parcel
number in campaigns. The same launch tags can be used on the guide or either
builder page. Register new source/campaign constants in the code when needed;
do not widen this to arbitrary URL strings. Verify actual acquisition reporting
after enabling: mocked transport tests prove our payload construction, not the
Google tag's internal behavior or the GA account's final attribution.

## One account check before enabling

The site supports shareable URLs containing `q` and `pin`. The Google tag can
automatically collect these independently of manual events. The setting
`send_page_view: false` does not disable enhanced history-based pageviews.
Therefore `analytics-config.js` ships with `enhancedMeasurementReviewed: false`.
No Google tag loads until that explicit setting is true on the production domain.

Open Google Analytics **Admin → Data collection and modification → Data streams**,
select the intended web stream (`G-B3FYWYWXTN`), and open Enhanced measurement's
settings. This requires Editor or higher access. For this stream:

1. Disable **Site search** automatic measurement. Do not create an automatic
   event that copies `q`, search input, or property address into an event field.
2. Disable **Page changes based on browser history events** in Page views'
   advanced settings. The app reports one canonical pageview on load.
3. Disable automatic **Outbound clicks**, **Form interactions**, **File downloads**,
   **Video engagement**, and **Scrolls**. The manual source-click event replaces
   URL-level click reporting. Enhanced measurement may also be switched off in
   full; the code still suppresses the default config pageview and sends its own
   sanitized pageview. Save the settings.
4. In the web stream's **Events → Redact data**, enable **Email addresses** and
   **URL query parameters**. Add `q`, `s`, `search`, `query`, `keyword`, `pin`,
   `ParcelNbr`, `utm_source`, `utm_medium`, `utm_campaign`, `utm_id`, `utm_term`,
   `utm_content`, `utm_source_platform`, `utm_creative_format`, and
   `utm_marketing_tactic`; press Enter after each. The manual allowlisted campaign
   fields remain separate from URL query parameters. Use **Test data redaction**
   with a synthetic address, parcel, email, and unsupported UTM value to preview
   what is redacted. Save the configuration. Redaction is a best-effort backup,
   not a replacement for the payload allowlists or disabled automatic events.
5. Check for additional tag destinations or custom event rules that collect
   raw search input. Confirm this is the intended property/stream.
6. Only after observing these account settings, set `enhancedMeasurementReviewed`
   to true. Verify a production test visit and synthetic search in GA4
   DebugView/Realtime and inspect its network event payloads. Test a valid tagged
   arrival, an invalid tag containing an email, a guide/builder arrival, property
   open, official-source click, and successful copy. Confirm the valid campaign
   survives the explorer URL rewrite and the static page has the expected path.
   Confirm no query text, address, PIN, raw link URL, arbitrary UTM text, duplicate
   history pageviews, or automatic `view_search_results` events are present. If
   unexpected fields/events appear, disable the site switch while correcting the
   account/tag setup.

The code and mocked transport tests are completed locally. Account configuration,
actual event receipt, reporting dimensions, consent requirements, and historical
traffic have not been inspected. This change does not remove previously collected
analytics data. The production switch should not be turned on based on unit tests alone.

To report custom fields beyond the event counts, register event-scoped dimensions
for `query_type`, `city`, `collection`, and `source`, plus an
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
- [Campaign configuration fields and overrides](https://developers.google.com/analytics/devguides/collection/ga4/reference/config)
- [Enhanced measurement events and parameters](https://support.google.com/analytics/answer/9216061?hl=en)
- [Data redaction](https://support.google.com/analytics/answer/13544947?hl=en)
- [Avoiding personally identifiable information](https://support.google.com/analytics/answer/6366371?hl=en)
- [Known bot exclusion](https://support.google.com/analytics/answer/9888366?hl=en)

Documentation checked October 9, 2026.
