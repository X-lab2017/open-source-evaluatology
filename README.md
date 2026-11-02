# Open Source Evaluatology
## Theory, Methods, and Empirical Studies

**Public review draft · 2026-11-02**  
Wei Wang · Shengyu Zhao · Fanyu Han · Xiaoya Xia

[Preview website](https://will-ww.github.io/open-source-evaluatology/) · [中文说明](README.zh-CN.md) · [Evidence index](docs/evidence-index.md) · [Contribute](CONTRIBUTING.md)

![The Living Commons](site/assets/commons.webp)

A monograph connecting the theory of evaluation with open source collaboration, measurement, evidence, and institutional practice.

## Four parts, eleven chapters

1. [Foundations of Open Source Evaluatology](manuscript/chapters/chapter01.tex)
2. [Value and Sustainability in Open Collaboration](manuscript/chapters/chapter02.tex)
3. [A Framework for Open Source Evaluation](manuscript/chapters/chapter03.tex)
4. [Measuring Activity in Open Collaboration](manuscript/chapters/chapter04.tex)
5. [OpenRank: Influence and Contribution](manuscript/chapters/chapter05.tex)
6. [OpenDigger: Evaluation in Practice](manuscript/chapters/chapter06.tex)
7. [Recognizing Contributions in Open Collaboration](manuscript/chapters/chapter07.tex)
8. [Evaluating Community Sustainability](manuscript/chapters/chapter08.tex)
9. [Evaluating Ecosystem Governance](manuscript/chapters/chapter09.tex)
10. [Open Source Science and Technology Think Tanks](manuscript/chapters/chapter10.tex)
11. [Disciplinary Development and the Tool Ecosystem](manuscript/chapters/chapter11.tex)

## Reading and status

The bilingual website provides chapter navigation, an evidence index, and contribution routes. The editable LaTeX manuscript is canonical. The Chinese authors’ note and English translation are under `manuscript/frontmatter/origins/`.

**PDF publication is intentionally deferred. No PDFs or PDF archives are committed.** This is a review version, not a final published edition. Cite a commit when referring to this evolving draft; see `CITATION.cff`.

## Build locally

Install Python 3, XeLaTeX/latexmk with a suitable TeX Live distribution, and CairoSVG (`python3 -m pip install cairosvg`). Then:

```sh
python3 scripts/prepare_manuscript.py
cd manuscript
latexmk -xelatex main.tex
```

The preparation script retrieves official upstream fonts with reviewed-content SHA-256 checks and converts included SVG figures to local-only PDFs. A changed upstream font is rejected rather than silently substituted. Font notices remain in `manuscript/fonts/`. Generated PDFs and font binaries are ignored. The static site requires no package installation; deploy the `site/` directory.

## Integrity and rights

Chapter prose is copied without rewriting from the reviewed manuscript. `verification/source-integrity.json` records chapter hashes. `python3 scripts/check_preview.py` verifies those hashes, chapter structure, local links, and the no-PDF rule before deployment.

Book text, figures, artwork, trademarks, and third-party content retain existing rights. New website/build code is MIT-licensed; see [rights and reuse](LICENSE.md). A blanket open-content license for the manuscript has not yet been assigned.
