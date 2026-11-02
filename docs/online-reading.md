# Online edition

The public reader lives at <https://www.x-lab.info/open-source-evaluatology/read/index.html>.
It includes all eleven English chapters, the Chinese authors’ note and its English
translation, the preface, book structure, and the introductions to Parts III and IV.
The interface supports English and Chinese; changing the interface language does
not translate the English manuscript.

## Single manuscript source

Edit the canonical files under `manuscript/`. Run:

```sh
python3 scripts/build_reader.py
python3 scripts/check_preview.py
```

The builder requires Python 3 and Pandoc. It produces static chapter HTML,
MathML equations, semantic HTML tables, chapter-local bibliography links,
cross-chapter references, and a local search index. There is no external font,
math renderer, analytics service, or search API required for reading. Search is
loaded on demand; figures load lazily. Images can be enlarged, and wide tables
and equations scroll within the text column. The last visited section and
reading settings are saved only in the reader’s browser.

Do not hand-edit `site/read/*.html`, `site/search-index.json`, or generated
reader figures. `verification/reader-build.json` records the exact source hashes
and structural counts. The deployment rebuilds the reader before checking it.
The existing chapter-hash check also remains in place: an intentional manuscript
revision must update the reviewed source-integrity baseline explicitly.

## Figures

Existing SVG and PNG sources are copied without redrawing their content. TikZ
figures are compiled with the manuscript’s reviewed Source Serif / Source Sans
fonts and converted to SVG. Their source hashes and generated SVGs are tracked,
so a text-only rebuild does not require TeX. Rebuilding a changed TikZ figure
requires XeLaTeX, `pdftocairo`, and the matching font files listed in
`manuscript/fonts/manifest.json`. Download and verify those fonts before the build;
the manuscript font files are ignored by Git. Intermediate PDFs are created only
in a temporary directory outside the repository and are never published.

Figure 10.6 in the print source has three pages. The initial repository SVG
contained page 1 only. The reader’s page 2 and page 3 SVGs were recovered from
the original reviewed manuscript archive, retaining their image content.
`site/assets/reader-sources/provenance.json` records the original file, SHA-256,
page numbers, and conversion. These supplemental SVGs are inputs, not generated
from the one-page repository SVG. The chapter text remains unchanged.

## Verification

`check_preview.py` validates unchanged reviewed chapters, all 66 sections,
source hashes for the generated reader, local links and fragment destinations,
figure assets, references, table presence, equation counts, search destinations,
absence of old personal-account project links, and the no-PDF/no-archive rule.
Browser QA covers chapter navigation, table and formula rendering, citation
details without leaving the reading position, figure zoom, search, font size,
themes, and responsive layouts down to 320 pixels.

The reader is deployed through the existing GitHub Pages workflow. The
repository and public website retain their established addresses and audience.
