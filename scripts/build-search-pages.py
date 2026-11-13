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
                "image": BASE + "/assets/social-preview.png?v=20261113-simple",
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
  <meta property="og:image" content="{BASE}/assets/social-preview.png?v=20261113-simple" />
  <meta property="og:image:alt" content="Who Built My Home? Search King County homes." />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{escape(title, quote=True)}" />
  <meta name="twitter:description" content="{escape(description, quote=True)}" />
  <meta name="twitter:image" content="{BASE}/assets/social-preview.png?v=20261113-simple" />
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
    <nav aria-label="Main navigation"><a href="/#collections">Builders</a><a href="{GUIDE}">Research guide</a><a href="/#contact">Contact</a></nav>
  </header>
  <main id="research-content" class="research-wrap">
    <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a><span aria-hidden="true">/</span><span>{escape(label)}</span></nav>
    <article>
      <header class="research-intro">
        <h1>{escape(heading)}</h1>
        <p class="research-lead">{intro}</p>
        <p class="research-date">Updated <time datetime="{modified}">{day(modified)}</time></p>
      </header>
      {body}
    </article>
  </main>
  <footer class="research-footer wrap">
    <p>Who Built My Home? · Independent project. Not affiliated with King County or the builders listed.</p>
    <p>King County records through <time datetime="{source_as_of}">{day(source_as_of)}</time>.</p>
    <nav aria-label="Footer navigation"><a href="/#explorer">Search homes</a><a href="/#about">About the records</a><a href="/#contact">Contact</a></nav>
  </footer>
</body>
</html>
'''


def guide_body(manifest):
    total = manifest["verifiedPropertyCount"]
    builders = len(manifest["collections"])
    return f'''
      <section class="research-section" aria-labelledby="step-parcel">
        <p class="step-label">Step 1</p><h2 id="step-parcel">Find the parcel number</h2>
        <p>Search the address in {link(PARCEL, 'King County Parcel Viewer')}. Check the location and note the ten-digit parcel number. For a condo or subdivided lot, check that you have the right unit or lot.</p>
        <p>You can also <a href="/#explorer">search this site</a> by address, city, ZIP, or parcel number. It includes {total:,} homes matched to {builders} builders.</p>
      </section>
      <section class="research-section" aria-labelledby="step-assessor">
        <p class="step-label">Step 2</p><h2 id="step-assessor">Check the property record</h2>
        <p>Open {link(EREAL, 'King County eReal Property')} and compare the address, year built, and sales history. On this site, each home's details include a link to its county property record.</p>
        <p>Note the sale date and recording number. The sale date and year built refer to different events.</p>
      </section>
      <section class="research-section" aria-labelledby="step-deed">
        <p class="step-label">Step 3</p><h2 id="step-deed">Read the deed</h2>
        <p>Look up the recording number in the {link(RECORDER, "King County Recorder's search")}. Check the property description and company names in the document.</p>
        <p>Older documents may require a name or property-description search. If you cannot find a document online, check with the Recorder's Office or county Archives.</p>
      </section>
      <section class="research-section" aria-labelledby="step-permit">
        <p class="step-label">Step 4</p><h2 id="step-permit">Find the building permit</h2>
        <p>Check the property's jurisdiction in Parcel Viewer. Ask the city's permit office for the original construction permit. For unincorporated areas, contact {link(PERMITS, 'King County Permits')}. The city in a mailing address may differ from the permit jurisdiction.</p>
        <p>Check the contractor's name, address or parcel, dates, and work described. Make sure the permit covers the original home, rather than an addition or remodel. Ask about archived files if older permits are not online.</p>
      </section>
      <section class="research-section" aria-labelledby="keep-notes">
        <h2 id="keep-notes">Save the records</h2>
        <p>Keep the source links, recording numbers, permit numbers, and company names. If a home is missing from this site, check the county records directly.</p>
        <p>See {link(RESEARCH, "King County's property research tools")}, or browse <a href="/builders/buchan/">Buchan</a>, <a href="/builders/burnstead/">Burnstead</a>, and <a href="/builders/quadrant/">Quadrant Homes</a>.</p>
      </section>
      <div class="research-action"><a class="button button-primary" href="/#explorer">Search homes</a><a href="/#contact">Report an error</a></div>
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
    return f'''<div class="city-table-wrap"><table class="city-table"><caption>Six cities with the most results</caption><thead><tr><th scope="col">City</th><th scope="col">Homes</th></tr></thead><tbody>{rows}</tbody></table></div><p class="table-note">Select a city to see its homes. City names come from county mailing addresses.</p>'''


def stats_panel(stats):
    return f'''<dl class="research-stats"><div><dt>Homes</dt><dd>{stats['count']:,}</dd></div><div><dt>Cities</dt><dd>{len(stats['cities'])}</dd></div><div><dt>Year built</dt><dd>{stats['year_min']}–{stats['year_max']}</dd></div></dl><p class="stats-note">Years are from county property records.</p>'''


def record_details(slug, stats, manifest, extra=""):
    flags = stats["flags"]
    multi = f"<li>{flags['multi-parcel-recording']:,} have a recording that covers several parcels.</li>" if flags['multi-parcel-recording'] else ""
    return f'''<details class="research-section"><summary>Record details</summary>
        <p>King County data through {day(manifest['sourceAsOf'])}. The first matching recording for each property is dated between {day(stats['record_min'])} and {day(stats['record_max'])}.</p>
        {extra}
        <ul><li>{flags['land-only-evidence']:,} properties have matching sales classified only as land.</li><li>{flags['chronology-review']:,} have a year built at least three years after the first matching recording.</li>{multi}</ul>
        <p>A property can appear in more than one count.</p>
      </details>'''


def sources_section(slug):
    return f'''<section class="research-sources" aria-labelledby="{slug}-sources"><h2 id="{slug}-sources">Sources</h2><p>King County property, building, and sales records. See <a href="/#about">how we match records</a> and {link(RESEARCH, "King County's property research tools")}.</p></section>'''


def check_section(slug):
    return f'''<section class="research-section" aria-labelledby="{slug}-check"><h2 id="{slug}-check">Check a home</h2><p>Open the home's details and follow the county property link. Look up its recording number in the {link(RECORDER, "Recorder's search")}. Check the original building permit for the contractor's name.</p><p>For instructions, see <a href="{GUIDE}">how to find a home's builder</a>.</p></section>'''


def buchan_body(stats, manifest):
    return f'''
      {stats_panel(stats)}
      <section class="research-section" aria-labelledby="buchan-coverage"><h2 id="buchan-coverage">Homes by city</h2>{city_table('buchan', stats)}</section>
      {check_section('buchan')}
      {record_details('buchan', stats, manifest)}
      {sources_section('buchan')}
      <div class="research-action"><a class="button button-primary" href="{explorer('buchan')}">View Buchan homes</a><a href="{GUIDE}">Research guide</a></div>
'''


def burnstead_body(stats, manifest):
    names = "<p>Names include Burnstead Construction LLC, Rick Burnstead Construction LLC, Steve Burnstead Construction LLC, and older Burnstead construction or homes companies.</p>"
    return f'''
      {stats_panel(stats)}
      <section class="research-section" aria-labelledby="burnstead-coverage"><h2 id="burnstead-coverage">Homes by city</h2>{city_table('burnstead', stats)}</section>
      {check_section('burnstead')}
      {record_details('burnstead', stats, manifest, names)}
      {sources_section('burnstead')}
      <div class="research-action"><a class="button button-primary" href="{explorer('burnstead')}">View Burnstead homes</a><a href="/builders/quadrant/">Quadrant Homes</a></div>
'''


def quadrant_body(stats, manifest):
    names = "<p>Matches use five Quadrant company names through 2020.</p>"
    return f'''
      {stats_panel(stats)}
      <section class="research-section" aria-labelledby="quadrant-coverage"><h2 id="quadrant-coverage">Homes by city</h2>{city_table('quadrant', stats)}</section>
      {check_section('quadrant')}
      {record_details('quadrant', stats, manifest, names)}
      {sources_section('quadrant')}
      <div class="research-action"><a class="button button-primary" href="{explorer('quadrant')}">View Quadrant homes</a><a href="/builders/burnstead/">Burnstead</a></div>
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lastmod", default="2026-10-11", help="Date these page files changed, YYYY-MM-DD")
    parser.add_argument("--pages-only", action="store_true", help="Leave sitemap.xml and robots.txt unchanged")
    args = parser.parse_args()
    modified = date.fromisoformat(args.lastmod).isoformat()
    manifest = json.loads((ROOT / "data/manifest.json").read_text())
    with gzip.open(ROOT / manifest["indexUrl"], "rt") as source:
        index = json.load(source)
    with gzip.open(ROOT / manifest["detailsUrl"], "rt") as source:
        details = json.load(source)
    assert len({p["pin"] for p in index}) == manifest["verifiedPropertyCount"]
    buchan = collection_stats("buchan", manifest, index, details)
    burnstead = collection_stats("burnstead", manifest, index, details)
    quadrant = collection_stats("quadrant", manifest, index, details)
    pages = [
        (GUIDE, "Find Your Home's Builder in King County | Who Built My Home?", "Find a home's builder using King County property records, deeds, and building permits.", "How to find your home's builder", "Research guide", "Start with the address, then check county records and the original building permit.", guide_body(manifest)),
        ("/builders/buchan/", "Buchan Homes in King County | Who Built My Home?", f"Search {buchan['count']:,} homes matched to Buchan company names in King County sales records.", "Buchan homes in King County", "Buchan", f"{buchan['count']:,} homes matched to Buchan company names in King County sales records.", buchan_body(buchan, manifest)),
        ("/builders/burnstead/", "Burnstead Homes in King County | Who Built My Home?", f"Search {burnstead['count']:,} homes matched to Burnstead company names in King County sales records.", "Burnstead homes in King County", "Burnstead", f"{burnstead['count']:,} homes matched to Burnstead company names in King County sales records.", burnstead_body(burnstead, manifest)),
        ("/builders/quadrant/", "Quadrant Homes in King County | Who Built My Home?", f"Search {quadrant['count']:,} homes matched to Quadrant company names in King County sales records.", "Quadrant homes in King County", "Quadrant", f"{quadrant['count']:,} homes matched to Quadrant company names in King County sales records.", quadrant_body(quadrant, manifest)),
    ]
    for path, title, description, heading, label, intro, body in pages:
        target = ROOT / path.strip("/") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        rendered = shell(path, title, description, heading, label, intro, body, modified, manifest["sourceAsOf"])
        target.write_text("\n".join(line.rstrip() for line in rendered.splitlines()) + "\n")
        print(f"Built {target.relative_to(ROOT)}")
    if args.pages_only:
        return
    locations = ["/"] + [page[0] for page in pages]
    entries = "\n".join(f"  <url><loc>{BASE}{path}</loc><lastmod>{modified}</lastmod></url>" for path in locations)
    (ROOT / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}\n</urlset>\n')
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n")


if __name__ == "__main__":
    main()
