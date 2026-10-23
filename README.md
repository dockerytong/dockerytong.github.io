# dockerytong.github.io

Source of <https://dockerytong.github.io/>. Plain static HTML and one CSS file, no build step.

```
index.html          about
research.html       research threads
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

Served by GitHub Pages from `main`; `.nojekyll` is present, so files are served as they are.
