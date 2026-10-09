#!/usr/bin/env python3
"""Build crawlable research pages from the same release as the property explorer.

Run from any directory. Counts describe distinct parcels in a collection, never
confirmed construction projects. The script fails if manifest counts drift.
"""
import argparse
from collections import Counter
from datetime import date
import gzip
from html import escape
import json
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://whobuiltmyhome.com"
GUIDE = "/guides/find-home-builder-king-county/"
EREAL = "https://blue.kingcounty.com/Assessor/eRealProperty/default.aspx"
PARCEL = "https://gismaps.kingcounty.gov/parcelviewer2/"
RESEARCH = "https://kingcounty.gov/en/dept/kcit/data-information-services/gis-center/property-research"
RECORDER = "https://kingcounty.gov/en/dept/executive-services/certificates-permits-licenses/records-licensing/recorders-office/records-search"
PERMITS = "https://kingcounty.gov/en/dept/local-services/certificates-permits-licenses/permits"


def link(url, label):
    return f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{escape(label)} ↗</a>'


def day(value):
    return date.fromisoformat(value).strftime("%B %-d, %Y")


def explorer(slug, city=None):
    values = {"collection": slug}
    if city:
        values["city"] = city
    return "/?" + escape(urlencode(values), quote=True) + "#explorer"


def shell(path, title, description, heading, label, intro, body, modified, source_as_of):
    canonical = BASE + path
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Article" if path == GUIDE else "CollectionPage",
                "headline" if path == GUIDE else "name": heading,
                "description": description,
                "url": canonical,
                "dateModified": modified,
                "inLanguage": "en-US",
                "image": BASE + "/assets/social-preview.png",
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Who Built My Home?", "item": BASE + "/"},
                    {"@type": "ListItem", "position": 2, "name": heading, "item": canonical},
                ],
            },
        ],
    }
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="referrer" content="no-referrer" />
  <meta name="description" content="{escape(description, quote=True)}" />
  <meta name="theme-color" content="#214f40" />
  <meta property="og:type" content="{"article" if path == GUIDE else "website"}" />
  <meta property="og:site_name" content="Who Built My Home?" />
  <meta property="og:title" content="{escape(title, quote=True)}" />
  <meta property="og:description" content="{escape(description, quote=True)}" />
  <meta property="og:url" content="{canonical}" />
  <meta property="og:image" content="{BASE}/assets/social-preview.png" />
  <meta property="og:image:alt" content="Who Built My Home? Research builder connections in King County." />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{escape(title, quote=True)}" />
  <meta name="twitter:description" content="{escape(description, quote=True)}" />
  <meta name="twitter:image" content="{BASE}/assets/social-preview.png" />
  <title>{escape(title)}</title>
  <link rel="canonical" href="{canonical}" />
  <link rel="stylesheet" href="../../styles.css" />
  <link rel="stylesheet" href="../../search-pages.css" />
  <script type="module" src="../../analytics.js"></script>
  <script type="application/ld+json">{json.dumps(schema, ensure_ascii=False).replace('</', '<\\/')}</script>
</head>
<body class="research-page">
  <a class="skip-link" href="#research-content">Skip to page content</a>
  <header class="site-header wrap">
    <a class="wordmark" href="/" aria-label="Who Built My Home? Home"><span class="brand-icon" aria-hidden="true"></span>Who Built My Home<span class="wordmark-question">?</span></a>
    <nav aria-label="Main navigation"><a href="/#collections">Builders</a><a href="{GUIDE}">Research guide</a><a href="/#contact">Feedback</a></nav>
  </header>
  <main id="research-content" class="research-wrap">
    <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a><span aria-hidden="true">/</span><span>{escape(label)}</span></nav>
    <article>
      <header class="research-intro">
        <p class="eyebrow">{escape(label)} · King County, Washington</p>
        <h1>{escape(heading)}</h1>
        <p class="research-lead">{intro}</p>
        <p class="research-date">Updated <time datetime="{modified}">{day(modified)}</time></p>
      </header>
      {body}
    </article>
  </main>
  <footer class="research-footer wrap">
    <p>Who Built My Home? · An independent property-research tool.</p>
    <p>County source snapshot: <time datetime="{source_as_of}">{day(source_as_of)}</time>. Associations do not confirm the builder.</p>
    <nav aria-label="Footer navigation"><a href="/#explorer">Search homes</a><a href="/#about">About the data</a><a href="/#contact">Share feedback</a></nav>
  </footer>
</body>
</html>
'''


def guide_body(manifest):
    total = manifest["verifiedPropertyCount"]
    builders = len(manifest["collections"])
    return f'''
      <aside class="research-note" aria-label="What a match means"><strong>Start with a lead, then verify it.</strong><p>A company name in a property sale identifies a connection to that parcel. It can concern a home, undeveloped land, or a transfer between companies. It does not, by itself, identify the builder of today's structure.</p></aside>
      <section class="research-section" aria-labelledby="step-parcel">
        <p class="step-label">Step 1</p><h2 id="step-parcel">Find the right address and parcel</h2>
        <p>Open {link(PARCEL, 'King County Parcel Viewer')} and search the street address. Check the location and save the ten-digit parcel number. For a condominium or a subdivided lot, make sure you have the unit or parcel you actually mean. Use that identifier to keep later searches tied to the same property.</p>
        <p>You can also start in our <a href="/#explorer">property explorer</a>, using an address, city, ZIP, or parcel number. Its current release includes {total:,} distinct parcels associated with {builders} builder collections. It is a partial discovery index, not a census of King County homes.</p>
      </section>
      <section class="research-section" aria-labelledby="step-assessor">
        <p class="step-label">Step 2</p><h2 id="step-assessor">Read the Assessor's property report</h2>
        <p>Follow the parcel's link to {link(EREAL, 'eReal Property')}. Compare the address, county year built, and sale history. If you arrived through this site's results, open the home's details and copy its matching company-record dates and recording numbers. Keep the construction year separate from the transaction date; they answer different questions.</p>
        <p>A sale near the construction year can help focus your investigation. A much earlier sale may concern the land. A later sale can involve an existing home. None of these timing patterns alone establishes who carried out construction.</p>
      </section>
      <section class="research-section" aria-labelledby="step-deed">
        <p class="step-label">Step 3</p><h2 id="step-deed">Inspect the recorded document</h2>
        <p>Use the {link(RECORDER, "Recorder's official records search")} to look up a recording number or parcel. Read the document image, compare its legal description with the property, and record the company names. A seller, owner, developer, and construction contractor can be different parties.</p>
        <p>The county says most documents recorded from August 1, 1991 onward are online; earlier documents require the Archives. Parcel-number searches cover 1997 onward, so an older record may need a recording number, name, or legal-description search. Missing one search result is not proof that no document exists.</p>
      </section>
      <section class="research-section" aria-labelledby="step-permit">
        <p class="step-label">Step 4</p><h2 id="step-permit">Check the original construction permit</h2>
        <p>Find the property's jurisdiction in Parcel Viewer. For a home inside a city, ask that city's permit office for the original construction file; for an unincorporated property, use {link(PERMITS, 'King County Permits')}. Postal city labels are useful search filters, but they do not determine which office issued the permit.</p>
        <p>Look for the permit's project description, named contractor, address or parcel, and dates. Distinguish original construction from additions or replacement buildings. If the online portal lacks an older file, ask the responsible office about its archived records.</p>
      </section>
      <section class="research-section" aria-labelledby="keep-notes">
        <h2 id="keep-notes">Keep an evidence trail</h2>
        <p>Save source links, recording and permit numbers, relevant names, and unresolved date differences. Describe the result at the level the documents support: a company-sale association, a permit naming a contractor, or an unresolved lead. A no-match here means the home is outside this release's reviewed matches; it does not mean the builder never worked there.</p>
        <p>For more official resources, see {link(RESEARCH, "King County's property-research directory")}. To explore a specific collection, start with <a href="/builders/burnstead/">Burnstead</a> or <a href="/builders/quadrant/">Quadrant Homes</a>.</p>
      </section>
      <div class="research-action"><a class="button button-primary" href="/#explorer">Search a King County home</a><a href="/#contact">Report an issue or missing result</a></div>
'''


def collection_stats(slug, manifest, index, details):
    collection = next(c for c in manifest["collections"] if c["id"] == slug)
    rows = [p for p in index if slug in p["collectionIds"]]
    assert len({p["pin"] for p in rows}) == len(rows) == collection["propertyCount"], slug
    years = [p["yearBuilt"] for p in rows if isinstance(p["yearBuilt"], int)]
    connections = [c for p in rows for c in details[p["pin"]]["connections"] if c["collectionId"] == slug]
    recordings = [c["firstCompanyRecording"] for c in connections]
    flags = Counter(f for c in connections for f in set(c.get("reviewFlags", [])))
    return {
        "collection": collection,
        "count": len(rows),
        "cities": Counter(p["city"] for p in rows),
        "year_min": min(years),
        "year_max": max(years),
        "year_missing": len(rows) - len(years),
        "record_min": min(recordings),
        "record_max": max(recordings),
        "flags": flags,
    }


def city_table(slug, stats):
    rows = "\n".join(
        f'<tr><th scope="row"><a href="{explorer(slug, city)}">{escape(city.title())}</a></th><td>{count:,}</td></tr>'
        for city, count in stats["cities"].most_common(6)
    )
    return f'''<div class="city-table-wrap"><table class="city-table"><caption>Six largest postal-city groups in this collection</caption><thead><tr><th scope="col">County postal-city label</th><th scope="col">Associated parcels</th></tr></thead><tbody>{rows}</tbody></table></div><p class="table-note">Select a city to open its filtered results. Postal-city labels are not municipal boundaries. Each count is a distinct parcel within this collection; it is not a verified number of homes built.</p>'''


def stats_panel(stats):
    return f'''<dl class="research-stats"><div><dt>Associated parcels</dt><dd>{stats['count']:,}</dd></div><div><dt>Postal-city labels</dt><dd>{len(stats['cities'])}</dd></div><div><dt>County year built</dt><dd>{stats['year_min']}–{stats['year_max']}</dd></div></dl><p class="stats-note">Year range describes the county's current structure records, not the builder's operating history.</p>'''


def burnstead_body(stats, manifest):
    flags = stats["flags"]
    return f'''
      {stats_panel(stats)}
      <aside class="research-note"><strong>What the Burnstead label means</strong><p>This collection groups reviewed Burnstead-named companies for discovery. A sale-record association does not certify the builder, and grouping names does not establish legal succession between companies.</p></aside>
      <section class="research-section" aria-labelledby="burnstead-coverage">
        <h2 id="burnstead-coverage">Explore the county-record coverage</h2>
        <p>The collection contains {stats['count']:,} distinct King County parcels across {len(stats['cities'])} postal-city labels. Sammamish and Redmond have the largest included groups, followed by Issaquah. Counts describe dataset coverage, not complete builder output or market share.</p>
        {city_table('burnstead', stats)}
      </section>
      <section class="research-section" aria-labelledby="burnstead-evidence">
        <h2 id="burnstead-evidence">How the names and dates are matched</h2>
        <p>Matching includes the documented names Burnstead Construction LLC, Rick Burnstead Construction LLC, and Steve Burnstead Construction LLC, plus reviewed historical seller names containing Burnstead and an explicit construction or homes business term. Open a property's evidence panel to see the particular company group associated with its sale.</p>
        <p>The county source snapshot is dated {day(manifest['sourceAsOf'])}. Among included parcels, the earliest matching company recording is {day(stats['record_min'])}; the latest first matching recording is {day(stats['record_max'])}. These are transaction dates, separate from the county year-built range of {stats['year_min']}–{stats['year_max']}. The collection is not a timeline of every Burnstead project.</p>
      </section>
      <section class="research-section" aria-labelledby="burnstead-check">
        <h2 id="burnstead-check">Verify the connection to a particular home</h2>
        <p>Begin with the exact address or ten-digit parcel number. Open the county property report from the result, then inspect the cited recording in the {link(RECORDER, "Recorder's search")}. Check the legal description and seller name before comparing the original construction permit from the responsible city or county office.</p>
        <p>This collection includes {flags['land-only-evidence']:,} parcel associations whose supporting sales have land-only classifications without an improved-residential classification, and {flags['chronology-review']:,} whose county construction year is at least three years after the first matching recording. These flags identify questions to investigate; they do not establish a different builder or a replacement home. Some flags overlap.</p>
        <p>If a home is missing, try its parcel number and check the county sources directly. A different company name, an unreviewed transaction, or coverage outside this release can prevent a match. Read the <a href="{GUIDE}">step-by-step builder research guide</a> for the full workflow.</p>
      </section>
      <section class="research-sources" aria-labelledby="burnstead-sources"><h2 id="burnstead-sources">Sources and scope</h2><p>Counts come from this site's released King County parcel, residential-building, and sale-record data. {link(RESEARCH, 'Official county property-research tools')} help check individual records. See <a href="/#about">the matching methodology</a> for release details. This is an independent research page, not an endorsement or an active-listings feed.</p></section>
      <div class="research-action"><a class="button button-primary" href="{explorer('burnstead')}">Explore Burnstead associations</a><a href="/builders/quadrant/">Explore Quadrant Homes records</a></div>
'''


def quadrant_body(stats, manifest):
    flags = stats["flags"]
    return f'''
      {stats_panel(stats)}
      <aside class="research-note"><strong>Historical Quadrant company matches</strong><p>This collection covers five reviewed corporate-name forms through 2020. It does not automatically extend the historical Quadrant label to later transactions or another brand.</p></aside>
      <section class="research-section" aria-labelledby="quadrant-coverage">
        <h2 id="quadrant-coverage">Find Quadrant-linked parcels by city</h2>
        <p>The release includes {stats['count']:,} distinct King County parcels linked to reviewed Quadrant company names in Assessor sale records, across {len(stats['cities'])} postal-city labels. Redmond, Snoqualmie, and Renton have the largest included groups. These counts describe dataset coverage, not all historical Quadrant homes or market share.</p>
        {city_table('quadrant', stats)}
      </section>
      <section class="research-section" aria-labelledby="quadrant-dates">
        <h2 id="quadrant-dates">Keep the recording date separate from year built</h2>
        <p>Among included parcels, the earliest first matching company recording is {day(stats['record_min'])}, and the latest is {day(stats['record_max'])}. The underlying county source snapshot is dated {day(manifest['sourceAsOf'])}, but this collection's reviewed company matches stop in 2020. Misspellings, other entities, combined sellers, and transactions from 2021 onward await review.</p>
        <p>County year-built values range from {stats['year_min']} to {stats['year_max']}. A construction year after the company sale does not establish that Quadrant built that structure. Resolve the property's chronology with the original documents and permits.</p>
      </section>
      <section class="research-section" aria-labelledby="quadrant-evidence">
        <h2 id="quadrant-evidence">What to check before naming the builder</h2>
        <p>Open a parcel in the explorer and follow its county property link. Use its recording references in the {link(RECORDER, "official Recorder's search")}, then compare the legal description, company name, and dates. A property seller can differ from the contractor who constructed the home.</p>
        <p>For this collection, {flags['land-only-evidence']:,} associations have only land-classified supporting sales rather than an improved-residential classification. Another review flag marks {flags['chronology-review']:,} parcels where county year built is at least three years after the earliest matching recording. There are also {flags['multi-parcel-recording']:,} associations with a recording covering multiple parcels. Flags can overlap, and these counts are prompts for document review, not proven errors.</p>
        <p>Ask the correct city or county permit office for the original construction file. Check its named contractor and project description against the parcel. Our <a href="{GUIDE}">King County builder research guide</a> explains how to find the jurisdiction and work through older recorded documents.</p>
      </section>
      <section class="research-sources" aria-labelledby="quadrant-sources"><h2 id="quadrant-sources">Coverage limits and official sources</h2><p>A no-match here means there is no reviewed association in this release. It does not rule out a historical Quadrant connection. Counts are computed from the released county records, not current sale listings. Use {link(RESEARCH, "King County's property-research tools")} and <a href="/#about">our data methodology</a> to continue checking the evidence.</p></section>
      <div class="research-action"><a class="button button-primary" href="{explorer('quadrant')}">Explore Quadrant associations</a><a href="/builders/burnstead/">Explore Burnstead records</a></div>
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lastmod", default="2026-10-09", help="Date these page files changed, YYYY-MM-DD")
    args = parser.parse_args()
    modified = date.fromisoformat(args.lastmod).isoformat()
    manifest = json.loads((ROOT / "data/manifest.json").read_text())
    with gzip.open(ROOT / manifest["indexUrl"], "rt") as source:
        index = json.load(source)
    with gzip.open(ROOT / manifest["detailsUrl"], "rt") as source:
        details = json.load(source)
    assert len({p["pin"] for p in index}) == manifest["verifiedPropertyCount"]
    burnstead = collection_stats("burnstead", manifest, index, details)
    quadrant = collection_stats("quadrant", manifest, index, details)
    pages = [
        (GUIDE, "How to Find Who Built Your Home in King County | Who Built My Home?", "Research a King County home's builder using parcel records, eReal Property, recorded deeds, and original permits. Learn what a company match does and does not prove.", "How to find who built your home in King County", "Research guide", "Follow the evidence from your address to the parcel, recorded documents, and original construction permit.", guide_body(manifest)),
        ("/builders/burnstead/", "Burnstead Homes in King County: Research County Records | Who Built My Home?", f"Explore {burnstead['count']:,} King County parcels associated with reviewed Burnstead company names. Browse city counts, county year-built ranges, and evidence limits.", "Research Burnstead homes in King County", "Builder records", "Explore county sale-record connections to Burnstead-named companies, then verify the evidence for a particular home.", burnstead_body(burnstead, manifest)),
        ("/builders/quadrant/", "Quadrant Homes in King County: County-Record Explorer | Who Built My Home?", f"Explore {quadrant['count']:,} King County parcels associated with reviewed historical Quadrant company names. Browse city counts and learn how to verify a home's builder.", "Research Quadrant homes in King County", "Builder records", "Find historical Quadrant company-sale associations and the county records you can use to investigate them.", quadrant_body(quadrant, manifest)),
    ]
    for path, title, description, heading, label, intro, body in pages:
        target = ROOT / path.strip("/") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(shell(path, title, description, heading, label, intro, body, modified, manifest["sourceAsOf"]))
        print(f"Built {target.relative_to(ROOT)}")
    locations = ["/"] + [page[0] for page in pages]
    entries = "\n".join(f"  <url><loc>{BASE}{path}</loc><lastmod>{modified}</lastmod></url>" for path in locations)
    (ROOT / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}\n</urlset>\n')
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n")


if __name__ == "__main__":
    main()
