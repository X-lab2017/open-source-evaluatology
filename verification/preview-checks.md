# Preview verification — 2026-11-02

- Passed: all eleven chapter hashes match the reviewed source; 66 section titles extracted.
- Passed: site local asset paths and PDF/archive exclusion checks.
- Passed: all 59 converted SVG figures were converted back to local-only PDF build inputs by CairoSVG.
- Passed: browser desktop preview, Chinese/English switch, dark theme, chapter part filter, reset, expand/collapse (six sections), and no horizontal overflow at 1180px.
- Full manuscript compilation not completed in this recovery environment: the installed TeX distribution lacks the `xelatex.fmt` format. This is not evidence of a content failure. Use a complete TeX Live installation for the documented local build.
- Upstream fonts are pinned by reviewed-content SHA-256. The preparation script rejects changed upstream binaries rather than silently changing typography.
- No claim of final editorial, legal, or publication approval is made.
