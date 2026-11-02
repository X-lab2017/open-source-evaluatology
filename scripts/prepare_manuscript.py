#!/usr/bin/env python3
"""Restore local-only fonts and PDF figures; never commit generated files."""
import hashlib,json,urllib.request
import cairosvg
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'manuscript'
for item in json.loads((root/'fonts/manifest.json').read_text()):
    target=root/'fonts'/item['name']
    if not target.exists():
        with urllib.request.urlopen(item['url']) as response: data=response.read()
        if hashlib.sha256(data).hexdigest()!=item['sha256']:
            raise SystemExit('Font version differs from reviewed source: '+item['name']+'. Obtain the matching upstream font; do not silently substitute.')
        target.write_bytes(data)
    if hashlib.sha256(target.read_bytes()).hexdigest()!=item['sha256']:raise SystemExit('Font hash mismatch: '+item['name'])
for item in json.loads((root/'pdf-figure-manifest.json').read_text()):
    cairosvg.svg2pdf(url=str(root/item['svg']),write_to=str(root/item['pdf']))
print('Prepared local build inputs. Run: cd manuscript && latexmk -xelatex main.tex')
