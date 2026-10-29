#!/usr/bin/env python3
"""Generate publications.html from a cached Zotero export.

Zotero's local API does not return creatorSummary, so dump your own items with:

    python3 - <<'EOF'
    import json, urllib.request
    items, start = [], 0
    while True:
        d = json.load(urllib.request.urlopen(
            f"http://127.0.0.1:23119/api/users/0/items/top?limit=100&start={start}"))
        if not d:
            break
        items += d
        start += len(d)
    mine = [x["data"] for x in items
            if any((c.get("lastName") or "") == "Liu" and (c.get("firstName") or "").startswith("Tong")
                   for c in x["data"].get("creators", []))]
    json.dump(mine, open("_tools/zotero-mine.json", "w"), ensure_ascii=False)
    EOF

Then run: python3 _tools/build_pubs.py
"""

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SELF = ("Liu", "Tong")

# DOIs of records where Tong Liu is the corresponding author (confirmed by CV).
CORRESPONDING = {
    "10.1016/j.susmat.2025.e01460",
    "10.1016/j.marpolbul.2025.118205",
    "10.1016/j.watres.2026.126137",
}

# Papers where Tong Liu shares first authorship (co-first), confirmed by the user.
CO_FIRST = {
    "10.1016/j.matlet.2024.136135",
    "10.1016/j.jhazmat.2022.128258",
    "10.1016/j.chemosphere.2021.132476",
    "10.1016/j.scitotenv.2021.147396",
}

# Duplicate preprints of already published articles, and other noise.
SKIP_DOIS = {
    "10.2139/ssrn.4379128",   # -> Chem. Eng. J. 2023
    "10.2139/ssrn.3967291",   # -> J. Water Process Eng. 2022
    "10.2139/ssrn.4074368",   # -> Appl. Surf. Sci. 2025
    "10.1101/2020.02.17.952168",
    "10.5281/zenodo.5112147",  # software release
}

# Extra records not in the Zotero library (manual entries).
# `issue` is only rendered when `volume` is set.
EXTRA = [
    dict(date="2026", publicationTitle="Earth Science Frontiers",
         title="煤源有机质生物可利用性机制、影响因素与应用前景",
         creators=[dict(lastName="刘", firstName="通")], DOI="10.13745/j.esf.sf.2025.5.4",
         volume="33", issue="5", pages="471-486",
         extra_authors="孟令子, 葛潇, 刘菲菲, 丁竑瑞, 鲁安怀",
         note="in Chinese; published online 2025"),
    dict(date="2026", publicationTitle="Acta Mineralogica Sinica",
         title="河口-近海水体水铁矿光催化作用与有机碳转化机制",
         creators=[dict(lastName="孟", firstName="令子"), dict(lastName="刘", firstName="通"),
                   dict(lastName="丁", firstName="竑瑞"), dict(lastName="鲁", firstName="安怀")],
         DOI=None, volume=None, pages=None,
         note="in Chinese; in press (KWXB-2026-0068.R1), volume and DOI to be completed"),
    dict(date="2022", publicationTitle="Geoscience",
         title="麦饭石促进异养反硝化去除水中硝酸盐的研究",
         creators=[dict(lastName="刘", firstName="文君"), dict(lastName="刘", firstName="通"),
                   dict(lastName="胡", firstName="伟武"), dict(lastName="陈", firstName="男"),
                   dict(lastName="冯", firstName="传平")],
         DOI="10.19657/j.geoscience.1000-8527.2021.105", volume=None, pages="574-582",
         note="in Chinese; volume not confirmed"),
]

# Field sections in display order, matching the three threads on research.html.
# DOI-keyed; no-DOI records are matched by a lowercase title fragment.
THREADS = [
    ("Sulfide mineral interfaces: oxidation and reduction", {
        "10.1016/j.electacta.2021.139078",
        "10.1016/j.jhazmat.2021.125844",
        "10.1016/j.apsusc.2025.163594",
        "10.1039/d0ra01177k",
        "10.1016/j.seppur.2026.140480",
    }, ("electrochemical stimulation",)),
    ("Mineral photocatalysis and iron cycling in the euphotic zone", {
        "10.1038/s41467-026-73469-3",
        "10.1016/j.marpolbul.2025.118205",
        "10.1080/01490451.2025.2523822",
        "10.3390/catal15080739",
        "10.1016/j.matlet.2024.136135",
    }, ("水铁矿光催化",)),
    ("Tailings to soil: aggregates, metals, and organic matter", {
        "10.1038/s43247-026-03718-2",
    }, ("vegetation succession",)),
]
EARLIER_HEADING = "Earlier work: water treatment and groundwater remediation"

JOURNAL_ABBREV = {
    "Nature Communications": "Nat. Commun.",
    "Environmental Science & Technology": "Environ. Sci. Technol.",
    "Water Research": "Water Res.",
    "Journal of Hazardous Materials": "J. Hazard. Mater.",
    "Chemical Engineering Journal": "Chem. Eng. J.",
    "Applied Surface Science": "Appl. Surf. Sci.",
    "Electrochimica Acta": "Electrochim. Acta",
    "Science of The Total Environment": "Sci. Total Environ.",
    "Science of the Total Environment": "Sci. Total Environ.",
    "Environmental Research": "Environ. Res.",
    "Bioresource Technology": "Bioresour. Technol.",
    "Journal of Cleaner Production": "J. Clean. Prod.",
    "Journal of Cleaner Production": "J. Clean. Prod.",
    "Chemosphere": "Chemosphere",
    "Journal of Environmental Management": "J. Environ. Manage.",
    "Journal of Environmental Sciences": "J. Environ. Sci.",
    "Communications Earth & Environment": "Commun. Earth Environ.",
    "Marine Pollution Bulletin": "Mar. Pollut. Bull.",
    "Sustainable Materials and Technologies": "Sustain. Mater. Technol.",
    "Materials Letters": "Mater. Lett.",
    "Geomicrobiology Journal": "Geomicrobiol. J.",
    "Water, Air, & Soil Pollution": "Water Air Soil Pollut.",
    "Catalysts": "Catalysts",
    "Water Science and Engineering": "Water Sci. Eng.",
    "Separation and Purification Technology": "Sep. Purif. Technol.",
    "RSC Advances": "RSC Adv.",
    "PLOS ONE": "PLoS ONE",
    "Environmental Engineering Science": "Environ. Eng. Sci.",
    "Journal of Water Process Engineering": "J. Water Process Eng.",
    "Journal of Chemical Technology and Biotechnology": "J. Chem. Technol. Biotechnol.",
    "Journal of Chemical Technology & Biotechnology": "J. Chem. Technol. Biotechnol.",
    "Nitrogen Cycling": "Nitrogen Cycling",
    "Earth Science Frontiers": "Earth Sci. Front.",
    "Acta Mineralogica Sinica": "Acta Mineral. Sin.",
    "Geoscience": "Geoscience",
}


def date_key(item):
    """Sort by year first, then by the raw Zotero date string (year-month-day)."""
    d = (item.get("date") or "").strip()
    m = re.match(r"(\d{4})", d)
    return (int(m.group(1)) if m else 0, d)


def initials(first):
    parts = re.split(r"[\s.\-]+", first.strip())
    return " ".join(p[0].upper() + "." for p in parts if p)


def author_list(creators):
    out = []
    for c in creators:
        if c.get("creatorType") not in (None, "author"):
            continue
        last = (c.get("lastName") or "").strip()
        first = (c.get("firstName") or "").strip()
        if not last and c.get("name"):
            out.append(c["name"])
        elif re.search(r"[\u4e00-\u9fff]", last):
            out.append(last + first)          # CJK: keep as written
        else:
            out.append(f"{last}, {initials(first)}" if first else last)
    return out


def clean(text):
    text = re.sub(r"<[^>]+>", "", text or "")
    return html.unescape(text).strip()


def fmt_journal(name):
    name = clean(name)
    return JOURNAL_ABBREV.get(name, name)


def is_self(creator):
    last = creator.get("lastName") or ""
    first = creator.get("firstName") or ""
    if last == "刘":
        return first.startswith("通")
    # exact given name only: "Liu, Tongxu" and "Liu, Tongyi" are different people
    return last == SELF[0] and first.strip() in ("Tong", "T")


def role_of(item):
    authors = [c for c in item.get("creators", []) if c.get("creatorType") in (None, "author")]
    if not authors:
        return "co"
    if is_self(authors[0]):
        return "first"
    if item.get("DOI") in CORRESPONDING:
        return "corr"
    if item.get("DOI") in CO_FIRST:
        return "cofirst"
    return "co"

def entry(item):
    authors = author_list(item.get("creators", []))
    if item.get("extra_authors"):
        authors = authors + item["extra_authors"].split(", ")
    marked = []
    for a in authors:
        if a.startswith("刘通") or a.startswith("Liu, T."):
            marked.append(f'<span class="me">{html.escape(a)}</span>')
        else:
            marked.append(html.escape(a))
    role = role_of(item)
    badge = {"first": '<span class="role">first</span>',
             "corr": '<span class="role">corresp.</span>',
             "cofirst": '<span class="role">co-first</span>'}.get(role, "")
    year = (item.get("date") or "")[:4]
    journal = fmt_journal(item.get("publicationTitle", ""))
    vol = item.get("volume")
    pages = clean(item.get("pages", ""))
    tail = ""
    if vol:
        tail = f" <strong>{html.escape(str(vol))}</strong>"
        if item.get("issue"):
            tail += f"({html.escape(str(item['issue']))})"
        if pages:
            tail += f", {html.escape(pages)}"
    elif pages:
        tail = f" {html.escape(pages)}"
    doi = item.get("DOI")
    doi_html = ""
    if doi:
        doi_html = f' <a href="https://doi.org/{html.escape(doi)}">doi</a>'
    title = html.escape(clean(item.get("title"))).replace("&lt;i&gt;", "").replace("&lt;/i&gt;", "")
    zh = " (in Chinese)" if (item.get("note") or "").startswith("in Chinese") else ""
    auth = ", ".join(marked).rstrip(".")
    ref = f'<span class="jr">{html.escape(journal)}</span>{tail}'
    visible_tail = (tail or journal).strip()
    if visible_tail and not visible_tail.endswith("."):
        ref += "."
    return (f'<li><span class="yr">{html.escape(year)}</span>'
            f'{auth}. {title}. {ref}{zh}{doi_html}{(" " + badge) if badge else ""}</li>')


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Publications — Tong Liu</title>
<meta name="description" content="Publications by Tong Liu on pyrite oxidation, mineral photocatalysis, iron cycling, and mineral-interface reactivity.">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>

<header class="site">
  <div class="wrap">
    <a class="site-name" href="index.html">Tong Liu</a>
    <nav class="site">
      <a href="index.html">About</a>
      <a href="research.html">Research</a>
      <a class="here" href="publications.html">Publications</a>
      <a href="cv.html">CV</a>
      <a href="notes/index.html">Notes</a>
    </nav>
  </div>
</header>

<main class="wrap">

  <h1>Publications</h1>

  <p class="note">
    {n_lead} papers as first or corresponding author ({n_cofirst} of them co-first), {n_co} as co-author.
    Grouped first by authorship role, then by research thread; the earlier water-treatment and
    groundwater work is listed last within each group.
    Also indexed on <a href="https://orcid.org/0000-0001-6829-0727">ORCID</a>.
  </p>

{sections}

  <p class="note">
    Conference presentations and invited talks are listed on the <a href="cv.html">CV</a> page.
  </p>

</main>

<footer class="site">
  <div class="wrap">
    <span>© 2026 Tong Liu</span>
    <span>Last updated October 2026</span>
  </div>
</footer>

</body>
</html>
"""


def main():
    data = json.loads((ROOT / "_tools/zotero-mine.json").read_text())
    items = [x for x in data
             if any(is_self(c) for c in x.get("creators", []))
             and x.get("itemType") == "journalArticle"
             and x.get("publicationTitle")
             and x.get("DOI") not in SKIP_DOIS]
    items += EXTRA
    items.sort(key=date_key, reverse=True)

    first = [i for i in items if role_of(i) == "first"]
    corr = [i for i in items if role_of(i) == "corr"]
    cofirst = [i for i in items if role_of(i) == "cofirst"]
    co = [i for i in items if role_of(i) == "co"]

    print("first:", len(first), "corr:", len(corr), "cofirst:", len(cofirst),
          "co:", len(co), "total:", len(items))
    for label, group in (("FIRST", first), ("CORR", corr), ("CO-FIRST", cofirst)):
        print(f"--- {label}")
        for i in group:
            print("  ", (i.get('date') or '')[:4], clean(i.get('publicationTitle')), "|", clean(i.get('title'))[:60])

    lead_items = sorted(first + corr + cofirst, key=date_key, reverse=True)

    sections_html = "\n\n".join([
        group_html("First, co-first, and corresponding author", lead_items),
        group_html("Co-authored", co),
    ])

    page = PAGE.format(
        sections=sections_html,
        n_lead=len(lead_items),
        n_cofirst=len(cofirst),
        n_co=len(co),
    )
    (ROOT / "publications.html").write_text(page)
    print(f"wrote publications.html ({len(lead_items)} lead incl. {len(cofirst)} co-first, "
          f"{len(co)} co-authored)")


def section(title, group):
    body = "\n".join(entry(i) for i in group)
    return f'  <h3>{html.escape(title)}</h3>\n\n  <ol class="pubs">\n{body}\n  </ol>'


def group_html(label, group):
    """One role block (h2) with one h3 subsection per thread, empty ones skipped."""
    parts = [f'  <h2>{html.escape(label)}</h2>']
    for name, _, _ in THREADS:
        sub = [i for i in group if thread_of(i) == name]
        if sub:
            parts.append(section(name, sub))
    sub = [i for i in group if thread_of(i) is None]
    if sub:
        parts.append(section(EARLIER_HEADING, sub))
    return "\n\n".join(parts)


def thread_of(item):
    """Return the thread name for an item, or None for earlier work."""
    doi = item.get("DOI")
    title_l = clean(item.get("title", "")).lower()
    for name, dois, title_frags in THREADS:
        if (doi and doi in dois) or any(f in title_l for f in title_frags):
            return name
    return None


if __name__ == "__main__":
    main()
