# dockerytong.github.io

Source of <https://dockerytong.github.io/>. Plain static HTML and one CSS file, no build step.

```
index.html          about
research.html       research threads
methods.html        methods and capabilities
publications.html   generated — do not edit by hand
cv.html             positions, education, grants, talks
notes/              archived working notes (2021–2023)
assets/style.css    the whole stylesheet
_tools/             publication-list generator
```

Publications are regenerated from the Zotero library:

```bash
python3 _tools/build_pubs.py     # rewrites publications.html
```

Adding a paper means re-dumping `_tools/zotero-mine.json` (command in the script header) and
re-running. Corresponding-author marks live in the `CORRESPONDING` set at the top of the script.

## Adding a paper: processing rules

Never edit `publications.html` by hand; it is overwritten on every run. Change data or rules in `_tools/build_pubs.py`, then regenerate.

1. **Add to Zotero, re-dump, rebuild.** A record enters the page only if it is a journal article with a journal name, and you are one of its creators. Preprints of published papers go in `SKIP_DOIS`.
2. **Authorship tag** (computed, not typed):
   - `First`: you are the first listed author.
   - `Co-first`: DOI in `CO_FIRST`.
   - `Corresp.`: DOI in `CORRESPONDING`.
   - No tag: co-authored.
   Precedence is First, then Corresp., then Co-first.
3. **Research thread**: put the DOI in the matching set in `THREADS` (or, for records without a DOI, a lowercase title fragment). The three threads mirror the *Current threads* section of `research.html`. A paper that fits none goes to *Earlier work*, which is collapsed by default. Reassigning a paper is a one-line edit in `THREADS`.
4. **Manual records** (not yet in the Zotero dump) go in `EXTRA`. They are deduplicated by DOI against the dump, so delete the entry once the dump catches up.
5. **Journal names**: add new journals to `JOURNAL_ABBREV`, otherwise the full name is printed.
6. **Authors**: lists of up to 5 names are shown in full. Longer lists show the first 3 names, your own name wherever it falls, and fold the rest behind `+N`.
7. **Entry layout**: title in plain type on its own line, then authors and journal on the next line. Do not bold titles.
8. **Counts** in the lead sentence and the section headings are computed; do not type them.

Served by GitHub Pages from `main`; `.nojekyll` is present, so files are served as they are.
