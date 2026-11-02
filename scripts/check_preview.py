import hashlib,json,re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote,urlsplit
r=Path(__file__).resolve().parents[1]
tracked=[p for p in r.rglob('*') if p.is_file() and '.git' not in p.parts]
assert not [p for p in tracked if p.suffix.lower() in ('.pdf','.zip')], 'PDFs/archives must not be published'
expected=json.loads((r/'verification/source-integrity.json').read_text())['chapters']
for name,h in expected.items():assert hashlib.sha256((r/'manuscript'/name).read_bytes()).hexdigest()==h,name
chapters=json.loads((r/'site/chapters.json').read_text()); assert len(chapters)==11
assert sum(len(c['sections']) for c in chapters)==66
class Page(HTMLParser):
 def __init__(self,text):
  super().__init__();self.ids=[];self.links=[];self.tags=Counter();self.classes=Counter();self.feed(text)
 def handle_starttag(self,tag,attrs):
  attrs=dict(attrs);self.tags[tag]+=1
  if 'id' in attrs:self.ids.append(attrs['id'])
  self.classes.update(attrs.get('class','').split())
  for key in ('href','src'):
   if attrs.get(key):self.links.append(attrs[key])
pages={p.resolve():Page(p.read_text()) for p in (r/'site').rglob('*.html')}
for p,page in pages.items():
 assert len(page.ids)==len(set(page.ids)),f'Duplicate anchor: {p}'
 for target in page.links:
  url=urlsplit(target)
  if url.scheme or url.netloc:continue
  path=(p.parent/unquote(url.path)).resolve() if url.path else p
  if path.is_dir():path=path/'index.html'
  assert path.is_file(),f'{p.name}: missing {target}'
  if url.fragment and path.suffix=='.html':
   assert unquote(url.fragment) in pages[path].ids,f'{p.name}: missing anchor {target}'
report=json.loads((r/'verification/reader-build.json').read_text())
assert not report['warnings'],report['warnings']
for path,digest in report['inputs'].items():
 assert hashlib.sha256((r/path).read_bytes()).hexdigest()==digest,f'Rebuild reader: {path}'
assert len(report['pages'])==17
assert sum(v['sections'] for v in report['pages'].values())==66
for slug,counts in report['pages'].items():
 page=pages[(r/'site/read'/f'{slug}.html').resolve()]
 assert page.tags['h1']==1,f'{slug}: duplicated chapter title'
 assert page.classes['equation']==counts['equations'],slug
 assert page.classes['table-figure']==counts['tables'],slug
 assert page.tags['table']>=counts['tables'],f'{slug}: unconverted table'
 assert len([i for i in page.ids if i.startswith('ref-')])==counts['references'],slug
 text=(r/'site/read'/f'{slug}.html').read_text()
 assert 'OSEBLOCK' not in text and 'OSETABLE' not in text and 'class="tabularx"' not in text,slug
 assert 'data-reference=' not in text and 'data-cites=' not in text,slug
 assert not [u for u in page.links if not urlsplit(u).scheme and urlsplit(u).path.lower().endswith('.pdf')],slug
for item in json.loads((r/'site/search-index.json').read_text()):
 url=urlsplit(item['url']);page=pages[(r/'site/read'/url.path).resolve()]
 assert url.fragment in page.ids,item['url']
for path in [r/'README.md',r/'README.zh-CN.md',r/'CITATION.cff',*pages]:
 assert not re.search(r'(?:github.com/will-ww|will-ww.github.io)/open-source-evaluatology',path.read_text()),path
print('PASS: 11 unchanged chapters; 66 sections; reader source hashes, tables, equations, citations, local links and search anchors; no PDFs or archives.')
