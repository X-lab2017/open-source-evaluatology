import hashlib,json,re
from pathlib import Path
r=Path(__file__).resolve().parents[1]
tracked=[p for p in r.rglob('*') if p.is_file() and '.git' not in p.parts]
assert not [p for p in tracked if p.suffix.lower() in ('.pdf','.zip')], 'PDFs/archives must not be published'
expected=json.loads((r/'verification/source-integrity.json').read_text())['chapters']
for name,h in expected.items():assert hashlib.sha256((r/'manuscript'/name).read_bytes()).hexdigest()==h,name
chapters=json.loads((r/'site/chapters.json').read_text()); assert len(chapters)==11
assert sum(len(c['sections']) for c in chapters)==66
for p in (r/'site').glob('*.html'):
 for target in re.findall(r'(?:href|src)="([^"]+)"',p.read_text()):
  if target.startswith(('http:', 'https:', '#','mailto:')):continue
  assert (p.parent/target.split('#')[0]).is_file(),target
print('PASS: 11 unchanged chapters, 66 sections, local site links, no PDFs or archives.')
