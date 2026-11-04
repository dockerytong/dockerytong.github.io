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

1. **Add to Zotero, re-dump, rebuild.** A record enters the page only if it is a journal article with a journal name and you are one of its creators. Preprints of published papers go in `SKIP_DOIS`.
2. **Section** (computed): first author → *First, co-first, and corresponding author*, otherwise *Co-authored*. Within a section, `CO_FIRST` and `CORRESPONDING` (by DOI) set the co-first and corresponding flags.
3. **Research thread**: put the DOI in the matching set in `THREADS` (or, for records without a DOI, a lowercase title fragment). The three threads mirror *Current threads* on `research.html`. A paper that fits none goes to *Earlier work*, which is folded by default at the end of each section.
4. **Manual records** not yet in the Zotero dump go in `EXTRA`, deduplicated by DOI in `main()`. Delete the entry once the dump catches up.
5. **Journal names**: add new journals to `JOURNAL_ABBREV`, otherwise the full name is printed.
6. **Counts** in the lead sentence are computed; do not type them.

Served by GitHub Pages from `main`; `.nojekyll` is present, so files are served as they are.
