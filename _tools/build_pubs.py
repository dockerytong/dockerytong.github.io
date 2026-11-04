#!/usr/bin/env python3
"""Generate publications.html from a cached Zotero export.

Processing rules for adding papers (tags, threads, EXTRA, folding): see README.md, "Adding a paper".

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
    "10.1016/j.jhazmat.2026.144077",
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
    # Not in the cached Zotero dump yet; delete once zotero-mine.json is refreshed (DOI dedupe is in main()).
    dict(date="2026", publicationTitle="Journal of Environmental Sciences",
         title="To protect landscapes, why can't suitable mine wastes be converted into constructed technosols?",
         creators=[dict(lastName="Wu", firstName="S."), dict(lastName="Liu", firstName="Tong"),
                   dict(lastName="Werner", firstName="T. T."), dict(lastName="Zhu", firstName="F."),
                   dict(lastName="Li", firstName="H."), dict(lastName="Chen", firstName="B."),
                   dict(lastName="Xue", firstName="S.")],
         DOI="10.1016/j.jes.2026.105867", volume=None, pages=None),
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
        "10.1016/j.jhazmat.2026.144077",
        # sulfate reduction on sulfur/iron-carbon/maifanite substrates, Fenton-type cathodes
        "10.1016/j.jenvman.2025.128343",
        "10.1016/j.cej.2024.157180",
        "10.1016/j.watres.2024.121775",
        "10.1016/j.envres.2024.120166",
        "10.1016/j.jclepro.2023.136332",
        "10.1016/j.cej.2023.143780",
        "10.1016/j.jwpe.2022.102954",
    }, ("electrochemical stimulation",)),
    ("Mineral photocatalysis and iron cycling in the euphotic zone", {
        "10.1038/s41467-026-73469-3",
        "10.1016/j.marpolbul.2025.118205",
        "10.1080/01490451.2025.2523822",
        "10.3390/catal15080739",
        "10.1016/j.matlet.2024.136135",
        # Fe-mineral transformation and Fe(II) cycling in the same systems
        "10.1021/acs.est.6c05850",
        "10.1016/j.scitotenv.2021.147396",
        "10.1016/j.envres.2020.109391",
    }, ("水铁矿光催化",)),
    ("Tailings to soil: aggregates, metals, and organic matter", {
        "10.1038/s43247-026-03718-2",
        "10.1016/j.jes.2026.105867",
        "10.1016/j.jes.2026.105835",
        # coal-derived organic matter; biochar sorption of Pb/Cd
        "10.13745/j.esf.sf.2025.5.4",
        "10.1016/j.jhazmat.2021.128059",
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

def one_author(c):
    last = (c.get("lastName") or "").strip()
    first = (c.get("firstName") or "").strip()
    if not last and c.get("name"):
        return c["name"]
    if re.search(r"[\u4e00-\u9fff]", last):
        return last + first               # CJK: keep as written
    return f"{last}, {initials(first)}" if first else last


TRUNC_OVER = 5   # lists up to this length are shown whole
KEEP_HEAD = 3    # names shown before the fold; the user's own name is always shown


def authors_html(item):
    people = [(one_author(c), is_self(c)) for c in item.get("creators", [])
              if c.get("creatorType") in (None, "author") and one_author(c)]
    people += [(n, n.startswith("刘通")) for n in (item.get("extra_authors") or "").split(", ") if n]

    def show(p):
        t = html.escape(p[0])
        return f'<span class="me">{t}</span>' if p[1] else t

    if len(people) <= TRUNC_OVER:
        return ", ".join(show(p) for p in people)
    out, hidden = [], []

    def flush():
        if hidden:
            out.append(f'<details class="more"><summary>+{len(hidden)}</summary>'
                       + ", ".join(show(p) for p in hidden) + "</details>")
            hidden.clear()

    for i, p in enumerate(people):
        if i < KEEP_HEAD or p[1]:
            flush()
            out.append(show(p))
        else:
            hidden.append(p)
    flush()
    return ", ".join(out)


TAG = {"first": "First", "corr": "Corresp.", "cofirst": "Co-first"}


def entry(item):
    """Plain title on its own line; authors and venue share the next line."""
    role = role_of(item)
    year = (item.get("date") or "")[:4]
    title = html.escape(clean(item.get("title")))
    if title and title[-1] not in ".?!":
        title += "."
    tag = f'<span class="tag {role}">{TAG[role]}</span> ' if role in TAG else ""
    journal = html.escape(fmt_journal(item.get("publicationTitle", "")))
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
    auth = authors_html(item)
    auth_sep = "" if auth.endswith(".") else "."
    ref = f'<span class="jr">{journal}</span>{tail}'
    if not clean(ref).endswith("."):
        ref += "."
    zh = " (in Chinese)" if (item.get("note") or "").startswith("in Chinese") else ""
    doi = item.get("DOI")
    doi_html = f' <a href="https://doi.org/{html.escape(doi)}">doi</a>' if doi else ""
    return (f'<li><span class="yr">{html.escape(year)}</span>'
            f'<div class="ttl">{tag}{title}</div>'
            f'<div class="venue">{auth}{auth_sep} {ref}{zh}{doi_html}</div></li>')


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Publications — Tong Liu</title>
<meta name="description" content="Publications by Tong Liu on pyrite oxidation, mineral photocatalysis, iron cycling, organo-mineral coupling, and mineral-interface reactivity.">
<link rel="canonical" href="https://dockerytong.github.io/publications.html">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Tong Liu">
<meta property="og:title" content="Publications — Tong Liu">
<meta property="og:description" content="Publications by Tong Liu on sulfide mineral interfaces, mineral photocatalysis, and tailings-to-soil formation.">
<meta property="og:url" content="https://dockerytong.github.io/publications.html">
<meta name="twitter:card" content="summary">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>

<header class="site">
  <div class="wrap">
    <a class="site-name" href="index.html">Tong Liu</a>
    <nav class="site">
      <a href="index.html">About</a>
      <a href="research.html">Research</a>
      <a href="methods.html">Methods</a>
      <a class="here" href="publications.html">Publications</a>
      <a href="cv.html">CV</a>
      <a href="notes/index.html">Notes</a>
    </nav>
  </div>
</header>

<main class="wrap pubs-page">

  <h1>Publications</h1>

  <p class="note">
    {n_lead} papers as first or corresponding author ({n_cofirst} of them co-first), {n_co} as co-author.
    Grouped by research thread, matching the <a href="research.html">Research</a> page; older
    water-treatment and microbiology papers that fall outside the threads are collapsed at the end.
    Also indexed on <a href="https://scholar.google.com/citations?user=Fs0dsfMAAAAJ&amp;hl=en">Google Scholar</a>, <a href="https://www.researchgate.net/profile/Tong-Liu-25">ResearchGate</a>, and <a href="https://orcid.org/0000-0001-6829-0727">ORCID</a>.
  </p>

  <p class="note legend">
    <span class="tag first">First</span> first author &middot;
    <span class="tag cofirst">Co-first</span> shared first authorship &middot;
    <span class="tag corr">Corresp.</span> corresponding author &middot;
    <span class="more-hint">+N</span> further co-authors, click to expand.
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
    have = {i.get("DOI") for i in items if i.get("DOI")}
    items += [e for e in EXTRA if e.get("DOI") not in have]
    items.sort(key=date_key, reverse=True)

    first = [i for i in items if role_of(i) == "first"]
    corr = [i for i in items if role_of(i) == "corr"]
    cofirst = [i for i in items if role_of(i) == "cofirst"]
    co = [i for i in items if role_of(i) == "co"]
    lead = first + corr + cofirst

    print("first:", len(first), "corr:", len(corr), "cofirst:", len(cofirst),
          "co:", len(co), "total:", len(items))

    parts = [section(name, [i for i in items if thread_of(i) == name]) for name, _, _ in THREADS]
    parts.append(section(EARLIER_HEADING, [i for i in items if thread_of(i) is None], collapsed=True))
    page = PAGE.format(
        sections="\n\n".join(p for p in parts if p),
        n_lead=len(lead),
        n_cofirst=len(cofirst),
        n_co=len(co),
    )
    (ROOT / "publications.html").write_text(page, encoding="utf-8")
    print(f"wrote publications.html ({len(lead)} lead incl. {len(cofirst)} co-first, "
          f"{len(co)} co-authored, {len(items)} total)")


def section(title, group, collapsed=False):
    if not group:
        return ""
    body = "\n".join(entry(i) for i in group)
    ol = f'  <ol class="pubs">\n{body}\n  </ol>'
    if collapsed:
        return (f'  <details class="earlier">\n'
                f'  <summary>{html.escape(title)} <span class="count">{len(group)}</span></summary>\n\n'
                f'{ol}\n  </details>')
    return (f'  <h2>{html.escape(title)} <span class="count">{len(group)}</span></h2>\n\n{ol}')


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
