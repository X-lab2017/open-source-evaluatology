#!/usr/bin/env python3
"""Generate the online edition from canonical TeX, without publishing PDFs.

Requires Pandoc. Existing SVGs are reused; changed TikZ needs XeLaTeX,
pdftocairo and the reviewed Source Sans/Serif fonts. Its intermediate PDFs
live only in a temporary directory. No chapter text is edited by this build.
"""
from pathlib import Path
import hashlib, html, json, re, shutil, struct, subprocess, tempfile
from collections import defaultdict
from functools import lru_cache

ROOT = Path(__file__).resolve().parents[1]
MS = ROOT / 'manuscript'
SITE = ROOT / 'site'
OUT = SITE / 'read'
ASSETS = SITE / 'assets' / 'reader'
REPO = 'https://github.com/X-lab2017/open-source-evaluatology'
BASE = 'https://www.x-lab.info/open-source-evaluatology/'
CHAPTERS = json.loads((SITE / 'chapters.json').read_text())
LABELS, INPUTS, SOURCES = {}, {}, {}
FIGURE_CACHE = ASSETS / 'tikz-manifest.json'
WARNINGS = []

def esc(s): return html.escape(str(s), quote=True)
def ident(s): return re.sub(r'[^a-zA-Z0-9_-]+', '-', s).strip('-')
def uncomments(s): return re.sub(r'(?<!\\)%[^\n]*', '', s)

def group(s, pos, opener='{', closer='}'):
    while pos < len(s) and s[pos].isspace(): pos += 1
    if pos >= len(s) or s[pos] != opener: raise ValueError((s[max(0,pos-20):pos+60], opener))
    start, depth = pos + 1, 1
    pos += 1
    while pos < len(s):
        if s[pos] == '\\': pos += 2; continue
        if s[pos] == opener: depth += 1
        if s[pos] == closer:
            depth -= 1
            if depth == 0: return s[start:pos], pos+1
        pos += 1
    raise ValueError('Unbalanced TeX group')

def commands(s, name, count=1, optional=False):
    pattern = re.compile(r'\\' + name + r'(?![A-Za-z])')
    for m in pattern.finditer(s):
        end = m.end(); opts=[]; args=[]
        while end < len(s) and s[end].isspace(): end += 1
        if optional:
            while end < len(s) and s[end] == '[':
                v,end=group(s,end,'[',']');opts.append(v)
        for _ in range(count):
            v,end=group(s,end);args.append(v)
        yield m.start(),end,args,opts

def replace(s, name, fn, count=1, optional=False):
    for start,end,args,opts in reversed(list(commands(s,name,count,optional))):
        s=s[:start]+fn(args,opts)+s[end:]
    return s

def first_arg(s, name):
    return next(commands(s,name), (None,None,[''],None))[2][0]

def expand(path):
    path=path.resolve()
    if path not in INPUTS:
        data=path.read_bytes(); INPUTS[path]=hashlib.sha256(data).hexdigest()
    s=uncomments(path.read_text())
    return replace(s,'input',lambda a,o:expand(MS/(a[0] if a[0].endswith('.tex') else a[0]+'.tex')))

def pandoc(s):
    p=subprocess.run(['pandoc','-f','latex','-t','html5','--mathml','--wrap=none'],input=s,text=True,capture_output=True,cwd=MS)
    if p.returncode: raise RuntimeError(p.stderr)
    if p.stderr: WARNINGS.append(p.stderr.strip())
    return p.stdout.strip()

@lru_cache(maxsize=10000)
def inline(s):
    result=pandoc(s)
    return re.sub(r'^<p>|</p>$','',result)

def plain(s):
    s=re.sub(r'<annotation\b[^>]*>[\s\S]*?</annotation>','',s)
    return re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]+>',' ',s))).strip()

ENVS = re.compile(r'\\begin\{(figure|table|equation)\}(?:\[[^\]]*\])?([\s\S]*?)\\end\{\1\}')
HEADINGS = re.compile(r'\\(chapter\*?|section\*?|subsection\*?|paragraph\*?)(?:\[[^\]]*\])?\s*\{')

def index_chapter(c):
    n=c['number']; slug=f'chapter-{n:02d}'; s=expand(MS/f'chapters/chapter{n:02d}.tex')
    SOURCES[slug]=s; counters=defaultdict(int); regions=[]
    for m in ENVS.finditer(s):
        kind,body=m.group(1,2)
        continued='\\contcaption' in body
        if not continued: counters[kind]+=1
        number=f'{n}.{counters[kind]}'
        for label in re.findall(r'\\label\{([^}]+)\}',body):
            LABELS[label]={'page':slug,'anchor':ident(label),'number':number,'kind':kind}
        regions.append((m.start(),m.end()))
    section=0; current=str(n)
    for m in re.finditer(r'\\(?:chapter|section|subsection|paragraph)\*?\s*\{|\\label\{([^}]+)\}',s):
        if any(a<=m.start()<b for a,b in regions): continue
        if m.group(0).startswith('\\section{'):
            section+=1;current=f'{n}.{section}'
        elif m.group(0).startswith('\\chapter'): current=str(n)
        elif m.group(1):
            LABELS[m.group(1)]={'page':slug,'anchor':ident(m.group(1)),'number':current,'kind':'section'}

def bibliography(n):
    s=expand(MS/f'bibliographies/complete/chapter{n:02d}.tex')
    entries={}
    for m in re.finditer(r'\\bibitem\[([^\]]+)\]\{([^}]+)\}([\s\S]*?)(?=\\bibitem|\\end\{thebibliography\})',s):
        label,key,body=m.groups()
        label=label.replace('~',' ')
        match=re.match(r'(.+?)\(([^)]+)\)',label)
        author,year=match.groups() if match else (label,'')
        body=replace(body,'doi',lambda a,o:r'\href{https://doi.org/'+a[0]+'}{DOI: '+a[0]+'}')
        entries[key]={'author':author,'year':year,'html':pandoc(body)}
    return entries

def prepare_text(s, slug, refs):
    def cite(a,o,kind):
        links=[]
        for key in a[0].split(','):
            key=key.strip(); item=refs.get(key)
            if not item: raise ValueError(f'{slug}: unresolved citation {key}')
            label=item['author']+(f" ({item['year']})" if kind=='citet' else f", {item['year']}")
            links.append(r'\href{#ref-'+ident(key)+'}{'+label+'}')
        sep='; ' if kind=='citep' else '; '
        result=sep.join(links)
        if len(o)>1: result=o[0]+' '+result
        if o: result+=', '+o[-1]
        return '('+result+')' if kind=='citep' else result
    s=replace(s,'citep',lambda a,o:cite(a,o,'citep'),optional=True)
    s=replace(s,'citet',lambda a,o:cite(a,o,'citet'),optional=True)
    def ref(a,o):
        label=LABELS.get(a[0])
        if not label: raise ValueError(f'{slug}: unresolved reference {a[0]}')
        href=('' if label['page']==slug else label['page']+'.html')+'#'+label['anchor']
        return r'\href{'+href+'}{'+(a[1] if len(a)>1 else label['number'])+'}'
    s=replace(s,'bookref',ref,2)
    s=replace(s,'ref',ref)
    s=replace(s,'markboth',lambda a,o:'',2)
    s=replace(s,'pdfbookmark',lambda a,o:'',2,True)
    s=replace(s,'tablenote',lambda a,o:r'\par '+a[0]+r'\par ')
    s=s.replace(r'\BookAuthors',' Wei Wang, Shengyu Zhao, Fanyu Han, and Xiaoya Xia ').replace(r'\BookDate',' November 2026 ')
    return s

def remove_print_format(s):
    # Do this only after extracting TikZ: its font/spacing commands are visual data.
    for cmd,n in [('fontsize',2),('setlength',2),('renewcommand',2),('vspace',1),('hspace',1),('color',1),('thispagestyle',1)]:
        s=replace(s,cmd,lambda a,o:' ',n)
    s=re.sub(r'\\(?:selectfont|normalfont|sffamily|bfseries|raggedright|raggedleft|centering|small|smallskip|noindent|clearpage|FloatBarrier|begingroup|endgroup|phantomsection)(?![A-Za-z])',' ',s)
    return s

def split_tex(s, separator):
    """Split top-level TeX rows/cells; escaped ampersands and grouped text survive."""
    chunks=[];start=0;i=0;depth=0
    while i<len(s):
        if depth==0 and s.startswith(separator,i):
            chunks.append(s[start:i]);i+=len(separator)
            if separator==r'\\' and i<len(s) and s[i]=='[':
                _,i=group(s,i,'[',']')
            start=i;continue
        if s[i]=='\\':i+=2;continue
        if s[i]=='{':depth+=1
        elif s[i]=='}':depth-=1
        i+=1
    chunks.append(s[start:]);return chunks

def render_tabulars(s):
    """Render cells individually: Pandoc's tabularx parser can drop leading numbers."""
    blocks={}
    def table(m):
        env=m[1];body=m[2];_,pos=group(body,0)
        if env in ('tabularx','tabular*'):_,pos=group(body,pos)
        content=body[pos:];rows=[];header=True
        for row in split_tex(content,r'\\'):
            if r'\midrule' in row:header=False
            row=re.sub(r'\\(?:toprule|midrule|bottomrule|addlinespace)(?:\[[^\]]*\])?',' ',row).strip()
            if not row:continue
            cells=[]
            for cell in split_tex(row,'&'):
                cell=cell.strip();colspan='';multi=list(commands(cell,'multicolumn',3))
                if multi:
                    _,_,args,_=multi[0];colspan=f' colspan="{int(args[0])}"';cell=args[2]
                bars={}
                def bar(a,o):
                    key=f'OSEBAR{len(bars)}';width=float(re.match(r'[\d.]+',a[0])[0])
                    bars[key]=f'<span class="table-bar" style="width:{width/35*120:.2f}px" aria-hidden="true"></span>'
                    return key
                cell=replace(cell,'rule',bar,2)
                rendered=inline(cell)
                for key,fragment in bars.items():rendered=rendered.replace(key,fragment)
                tag='th' if header else 'td'
                cells.append(f'<{tag}{colspan}'+(' scope="col"' if header else '')+'>'+rendered+f'</{tag}>')
            rows.append('<tr>'+''.join(cells)+'</tr>')
        value='<table><tbody>'+''.join(rows)+'</tbody></table>'
        key=f'OSETABLE{len(blocks)}';blocks[key]=value;return '\n\n'+key+'\n\n'
    pattern=r'\\begin\{(tabularx|tabular\*|tabular)\}([\s\S]*?)\\end\{\1\}'
    s=re.sub(pattern,table,s)
    rendered=pandoc(remove_print_format(s))
    for key,value in blocks.items():rendered=rendered.replace('<p>'+key+'</p>',value).replace(key,value)
    return rendered

def render_tikz(tikz, name, cache):
    style=(MS/'figure-style.tex').read_text()
    colors='\n'.join(re.findall(r'\\definecolor[^\n]+',(MS/'review-layout.tex').read_text()))
    digest=hashlib.sha256((tikz+style+colors+'reader-svg-v1').encode()).hexdigest()
    target=ASSETS/(name+'.svg')
    if cache.get(name)==digest and target.exists(): return '../assets/reader/'+target.name
    fontdir=MS/'fonts'
    for font in ['SourceSans3-Regular.otf','SourceSerif4-Regular.otf']:
        if not (fontdir/font).exists(): raise RuntimeError('Changed TikZ needs reviewed manuscript/fonts inputs: '+font)
    preamble=r'''\documentclass[tikz,border=3pt]{standalone}
\usepackage{fontspec,amsmath,amssymb,xcolor,graphicx}
\defaultfontfeatures{Ligatures=TeX}
\setmainfont{SourceSerif4}[Path=FONTDIR/,Extension=.otf,UprightFont=*-Regular,ItalicFont=*-It,BoldFont=*-Semibold,BoldItalicFont=*-SemiboldIt]
\setsansfont{SourceSans3}[Path=FONTDIR/,Extension=.otf,UprightFont=*-Regular,ItalicFont=*-It,BoldFont=*-Semibold,BoldItalicFont=*-SemiboldIt]
\usetikzlibrary{arrows.meta,calc}
\newcommand{\hyperref}[2][]{#2}
'''.replace('FONTDIR',str(fontdir))
    with tempfile.TemporaryDirectory(prefix='ose-reader-') as tmp:
        tex=Path(tmp)/'figure.tex'
        tex.write_text(preamble+colors+'\n'+style+'\n\\begin{document}\n'+tikz+'\n\\end{document}')
        p=subprocess.run(['xelatex','-interaction=nonstopmode','-halt-on-error',tex.name],cwd=tmp,capture_output=True,text=True)
        if p.returncode: raise RuntimeError(name+'\n'+p.stdout[-4000:])
        subprocess.run(['pdftocairo','-svg',str(tex.with_suffix('.pdf')),str(target)],check=True)
    cache[name]=digest
    return '../assets/reader/'+target.name

def image_asset(path, options=''):
    source=MS/path
    page=re.search(r'page=(\d+)',options)
    if page and int(page[1])>1:
        if source.name!='fig10-06-applications.pdf': raise ValueError('Unmapped multipage figure '+path)
        target=SITE/'assets'/'reader-sources'/f'fig10-06-applications-page-{page[1]}.svg'
        assert target.is_file()
        return '../assets/reader-sources/'+target.name
    if source.suffix=='.pdf': source=source.with_suffix('.svg')
    if not source.is_file(): raise FileNotFoundError(source)
    INPUTS[source.resolve()]=hashlib.sha256(source.read_bytes()).hexdigest()
    target=ASSETS / ('--'.join(source.relative_to(MS).parts))
    shutil.copy2(source,target)
    return '../assets/reader/'+target.name

def image_size(src):
    path=(OUT/src).resolve()
    if path.suffix=='.svg':
        header=path.read_text()[:1500]
        view=re.search(r'viewBox="[\d. -]+ ([\d.]+) ([\d.]+)"',header)
        if view:return f' width="{round(float(view[1]))}" height="{round(float(view[2]))}"'
        width=re.search(r'width="([\d.]+)',header);height=re.search(r'height="([\d.]+)',header)
        if width and height:return f' width="{round(float(width[1]))}" height="{round(float(height[1]))}"'
    elif path.suffix=='.png':
        with path.open('rb') as f:header=f.read(24)
        width,height=struct.unpack('>II',header[16:24]);return f' width="{width}" height="{height}"'
    return ''

def render_content(s, slug, refs, cache, number=0):
    blocks={}; counts=defaultdict(int); toc=[]
    def token(fragment):
        key=f'OSEBLOCK{len(blocks):05d}'; blocks[key]=fragment; return '\n\n'+key+'\n\n'
    s=prepare_text(s,slug,refs)
    def environment(m):
        kind,body=m.group(1,2);continued='\\contcaption' in body
        if not continued: counts[kind]+=1
        num=f'{number}.{counts[kind]}'
        label=first_arg(body,'label'); anchor=ident(label) if label else f'{kind}-{counts[kind]}-continued-{len(blocks)}'
        if kind=='equation':
            equation=replace(body,'label',lambda a,o:'')
            return token(f'<div class="equation" id="{anchor}"><div class="math-scroll" tabindex="0" aria-label="Equation {num}">{pandoc(chr(92)+"["+equation+chr(92)+"]")}</div><a class="equation-number" href="#{anchor}" aria-label="Equation {num}">({num})</a></div>')
        caption=first_arg(body,'contcaption' if continued else 'caption')
        caption_html=inline(caption)
        if kind=='table':
            notes=list(commands(body,'tablenote'))
            # prepare_text already expanded tablenote, so Pandoc keeps it as prose.
            body=replace(body,'caption',lambda a,o:'')
            body=replace(body,'label',lambda a,o:'')
            rendered=render_tabulars(body)
            return token(f'<figure class="table-figure" id="{anchor}"><figcaption><strong>Table {num}.</strong> {caption_html}</figcaption><div class="table-scroll" tabindex="0" role="region" aria-label="Table {num}">{rendered}</div></figure>')
        images=[]
        tikz=re.search(r'\\begin\{tikzpicture\}[\s\S]*?\\end\{tikzpicture\}',body)
        if tikz:
            images=[render_tikz(tikz[0],f'{slug}-figure-{counts[kind]}',cache)]
        else:
            images=[image_asset(a[0],','.join(o)) for _,_,a,o in commands(body,'includegraphics',optional=True)]
        if not images: raise RuntimeError(f'Figure without image: {slug} {num}')
        content=''
        for i,src in enumerate(images):
            alt=f'Figure {num}'+(f', panel {i+1}' if len(images)>1 else '')+'. '+plain(caption_html)[:220]
            content+=f'<a class="figure-zoom" href="{esc(src)}" target="_blank" rel="noopener" aria-label="Enlarge figure {num}{", panel "+str(i+1) if len(images)>1 else ""}"><img src="{esc(src)}" alt="{esc(alt)}"{image_size(src)} loading="lazy" decoding="async"></a>'
        return token(f'<figure class="book-figure" id="{anchor}">{content}<figcaption><strong>Figure {num}{" (continued)" if continued else ""}.</strong> {caption_html}</figcaption></figure>')
    s=ENVS.sub(environment,s)
    # The book-structure plate is outside a figure environment in the source.
    for m in reversed(list(re.finditer(r'\\begin\{tikzpicture\}[\s\S]*?\\end\{tikzpicture\}',s))):
        src=render_tikz(m[0],slug+'-structure',cache)
        block=token(f'<figure class="book-figure"><a class="figure-zoom" href="{src}" target="_blank" rel="noopener" aria-label="Enlarge book structure"><img src="{src}" alt="The architecture of the book: four parts and eleven chapters"{image_size(src)} loading="lazy"></a></figure>')
        s=s[:m.start()]+block+s[m.end():]
    section=0;sub=0
    # Explicit heading IDs give stable links even when titles are copyedited.
    headings=list(HEADINGS.finditer(s))
    replacements=[]
    for idx,m in enumerate(headings):
        title,end=group(s,m.end()-1)
        kind=m[1].rstrip('*')
        segment=s[end:(headings[idx+1].start() if idx+1<len(headings) else len(s))]
        label_match=re.match(r'\s*\\label\{([^}]+)\}',segment)
        label=label_match[1] if label_match else None
        if label_match: end+=label_match.end()
        if kind=='chapter':
            anchor=ident(label) if label else 'chapter-start'
            frag=f'<span id="{anchor}" class="anchor"></span>'
        else:
            if kind=='section':section+=1;sub=0
            elif kind=='subsection':sub+=1
            anchor=ident(label) if label else (f'section-{section}' if kind=='section' else ident(f'{section}-{sub}-{plain(inline(title))}'))
            level={'section':2,'subsection':3,'paragraph':4}[kind]
            prefix=f'<span class="section-number">{number}.{section}</span> ' if kind=='section' and number else ''
            title_html=inline(title)
            frag=f'<h{level} id="{anchor}">{prefix}{title_html}<a class="heading-anchor" href="#{anchor}" aria-label="Link to this section">#</a></h{level}>'
            if kind=='section': toc.append({'id':anchor,'title':plain(title_html),'number':f'{number}.{section}' if number else ''})
        replacements.append((m.start(),end,token(frag)))
    for start,end,value in reversed(replacements):s=s[:start]+value+s[end:]
    # Preserve any remaining explicit labels as addressable anchors.
    s=replace(s,'label',lambda a,o:token(f'<span id="{ident(a[0])}" class="anchor"></span>'))
    result=render_tabulars(s)
    result=re.sub(r'<math display="block"[\s\S]*?</math>',lambda m:'<span class="math-scroll standalone-math" tabindex="0" role="region" aria-label="Mathematical expression">'+m[0]+'</span>',result)
    # Unnumbered tables in part introductions also scroll within the text column.
    result=re.sub(r'<table>[\s\S]*?</table>',lambda m:'<div class="table-scroll" tabindex="0" role="region" aria-label="Part overview">'+m[0]+'</div>',result)
    for key,fragment in blocks.items():
        result=result.replace('<p>'+key+'</p>',fragment).replace(key,fragment)
    # Scroll wide structures locally instead of making the entire page overflow.
    result=re.sub(r'<a href="(#ref-[^"]+)"',r'<a class="citation-link" href="\1"',result)
    return result,toc,dict(counts)

def ui(en,zh):return '<span class="ui-en">'+en+'</span><span class="ui-zh">'+zh+'</span>'

FRONT = [
    {'slug':'authors-note-zh','title':'从开源社区到开源评价学','title_zh':'作者自序 · 中文原文','source':'frontmatter/origins/chinese.tex','lang':'zh'},
    {'slug':'authors-note-en','title':'From Open Source Communities to Open Source Evaluatology','title_zh':'作者自序 · 英文译文','source':'frontmatter/origins/english.tex','lang':'en'},
    {'slug':'preface','title':'Preface','title_zh':'前言','source':'frontmatter/review/preface.tex','lang':'en'},
    {'slug':'book-structure','title':'Book Structure','title_zh':'全书结构','source':'frontmatter/complete/book-structure.tex','lang':'en'},
]
GUIDES=[
    {'slug':'part-3-guide','title':'The Argument of Part III','title_zh':'第三部分导读','source':'frontmatter/complete/part-three-guide.tex','lang':'en'},
    {'slug':'part-4-guide','title':'The Argument of Part IV','title_zh':'第四部分导读','source':'frontmatter/complete/part-four-guide.tex','lang':'en'},
]

def nav_book(slug):
    links=[f'<a href="index.html"'+(' aria-current="page"' if slug=='index' else '')+'>'+ui('Reading guide','阅读指南')+'</a>']
    for f in FRONT:
        links.append(f'<a href="{f["slug"]}.html"'+(' aria-current="page"' if slug==f['slug'] else '')+'>'+ui(esc(f['title'] if f['slug'] not in ('authors-note-zh','authors-note-en') else "Authors’ note · "+('中文' if f['lang']=='zh' else 'English')),esc(f['title_zh']))+'</a>')
    parts=[('Theory','理论基础'),('Methods and Infrastructure','方法与基础设施'),('Empirical Studies','应用与实证'),('Disciplinary Development','学科建设')]
    for part,(en,zh) in enumerate(parts,1):
        links.append('<p class="nav-part">'+ui(f'PART {part} · {en}',f'第 {part} 部分 · {zh}')+'</p>')
        if part in (3,4):
            key=f'part-{part}-guide'
            links.append(f'<a class="part-guide" href="{key}.html"'+(' aria-current="page"' if slug==key else '')+'>'+ui('Part introduction','本部分导读')+'</a>')
        for c in CHAPTERS:
            if c['part']!=part:continue
            key=f'chapter-{c["number"]:02d}'
            links.append(f'<a class="nav-chapter" href="{key}.html"'+(' aria-current="page"' if slug==key else '')+f'><span class="nav-number">{c["number"]:02d}</span><span>'+ui(esc(c['title']),esc(c['title_zh']))+'</span></a>')
    return ''.join(links)

def template(slug,title,title_zh,body,toc,source='',number=0,language='en',prev=None,next=None,minutes=0):
    local_toc=''.join(f'<a href="#{t["id"]}"><span>{t["number"]}</span>{esc(t["title"])}</a>' for t in toc)
    chapter_label=ui(f'CHAPTER {number:02d}',f'第 {number} 章') if number else ui('OPEN SOURCE EVALUATOLOGY','开源评价学')
    metadata=ui(f'{minutes} min read · '+('Chinese original' if language=='zh' else 'English text'),f'约 {minutes} 分钟 · '+('中文原文' if language=='zh' else '英文原文')) if minutes else ui('Four parts · Eleven chapters','四个部分 · 十一章')
    sequence=''
    for key,label_en,label_zh in [(prev,'← Previous','← 上一篇'),(next,'Next →','下一篇 →')]:
        if key:sequence+=f'<a href="{key["slug"]}.html"><small>{ui(label_en,label_zh)}</small><strong>{ui(esc(key["title"]),esc(key["title_zh"]))}</strong></a>'
        else:sequence+='<span></span>'
    source_link=f'<a href="{REPO}/blob/main/manuscript/{source}" target="_blank" rel="noopener">{ui("View source ↗","查看源稿 ↗")}</a>' if source else ''
    return f'''<!doctype html>
<html lang="en" data-lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · Open Source Evaluatology</title><meta name="description" content="{esc(title)} — read the public review edition of Open Source Evaluatology online."><meta name="color-scheme" content="light dark"><link rel="canonical" href="{BASE}read/{slug}.html"><link rel="stylesheet" href="../reader.css"><script src="../reader.js" defer></script></head>
<body data-page="{slug}"><a class="skip" href="#reading-content">{ui('Skip to text','跳到正文')}</a>
<header class="reader-header"><a class="reader-brand" href="../index.html"><b>OSE</b><span>Open Source<br>Evaluatology</span></a><div class="reader-controls"><button id="contents-toggle" aria-controls="book-navigation" aria-expanded="false">☰ {ui('Contents','目录')}</button><button id="search-open" aria-label="Search the book">⌕ {ui('Search','搜索')}</button><div class="type-controls" aria-label="Text size"><button id="type-smaller" aria-label="Smaller text">A−</button><button id="type-larger" aria-label="Larger text">A+</button></div><button id="focus-toggle" aria-pressed="false">{ui('Focus','专注')}</button><button id="language" aria-label="Switch interface language">中文</button><button id="theme" aria-label="Switch color theme">◐</button></div></header>
<div class="reading-progress" role="progressbar" aria-label="Reading progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><div></div></div>
<button class="nav-backdrop" aria-label="Close contents" hidden></button>
<div class="reader-layout"><aside id="book-navigation" class="book-navigation" aria-label="Book contents"><div class="sidebar-top">{ui('IN THIS BOOK','全书目录')}<button id="contents-close" aria-label="Close contents">×</button></div><nav>{nav_book(slug)}</nav><div class="mobile-section-toc">{ui('ON THIS PAGE','本篇目录')}{local_toc}</div><a class="sidebar-home" href="../index.html">{ui('← About this book','← 返回书籍首页')}</a></aside>
<main id="reading-content" class="reading-main"><div class="chapter-opening"><p class="eyebrow">{chapter_label}</p><h1>{esc(title)}</h1><p class="chinese-title ui-zh">{esc(title_zh)}</p><p class="reading-meta">{metadata}</p><p class="edition-note">{ui('Public review edition · November 2026','公开评审预览版 · 2026 年 11 月')}</p></div>
<article class="prose" lang="{language}">{body}</article><nav class="chapter-pagination" aria-label="Continue reading">{sequence}</nav><footer class="reader-footer"><a href="index.html">{ui('All chapters','全书目录')}</a>{source_link}<a href="{REPO}/issues/new?template=review.yml" target="_blank" rel="noopener">{ui('Suggest a correction ↗','反馈勘误 ↗')}</a><p>{ui('Book text and third-party materials retain their existing rights.','正文与第三方素材保留原有权利。')}</p></footer></main>
<aside class="section-navigation" aria-label="On this page"><p>{ui('ON THIS PAGE','本篇目录')}</p><nav>{local_toc}</nav><a class="back-top" href="#reading-content">{ui('↑ Back to top','↑ 回到顶部')}</a></aside></div>
<dialog id="search-dialog" aria-labelledby="search-title"><div class="dialog-top"><h2 id="search-title">{ui('Search the book','搜索全书')}</h2><button data-close aria-label="Close search">×</button></div><label class="search-label" for="book-search">{ui('A concept, phrase, or chapter title','输入概念、词句或章节名称')}</label><input id="book-search" type="search" placeholder="OpenRank, sustainability, 开源…" autocomplete="off"><p id="search-status" role="status">{ui('Search the full text, including references.','搜索正文与参考文献。')}</p><div id="search-results"></div></dialog>
<dialog id="citation-dialog" aria-labelledby="citation-title"><div class="dialog-top"><h2 id="citation-title">{ui('Reference','参考文献')}</h2><button data-close aria-label="Close reference">×</button></div><div class="citation-detail"></div><a class="citation-destination">{ui('View in chapter references →','前往本章参考文献 →')}</a></dialog>
<dialog id="figure-dialog" aria-labelledby="figure-title"><div class="dialog-top"><h2 id="figure-title">{ui('Figure detail','图件详情')}</h2><div><button id="zoom-out" aria-label="Zoom out">−</button><button id="zoom-in" aria-label="Zoom in">+</button><button data-close aria-label="Close figure">×</button></div></div><div class="figure-viewport"><img alt=""></div><a class="original-figure" target="_blank" rel="noopener">{ui('Open original image ↗','打开原图 ↗')}</a></dialog>
<p class="reader-status" role="status" aria-live="polite"></p></body></html>'''

def main():
    OUT.mkdir(exist_ok=True);ASSETS.mkdir(parents=True,exist_ok=True)
    cache=json.loads(FIGURE_CACHE.read_text()) if FIGURE_CACHE.exists() else {}
    for c in CHAPTERS:index_chapter(c)
    for f in FRONT+GUIDES:
        for label in re.findall(r'\\label\{([^}]+)\}',expand(MS/f['source'])):
            LABELS[label]={'page':f['slug'],'anchor':ident(label),'number':f['title'],'kind':'front'}
    sequence=FRONT.copy()
    for c in CHAPTERS:
        if c['number'] in (7,10):sequence.append(GUIDES[0 if c['number']==7 else 1])
        sequence.append({**c,'slug':f'chapter-{c["number"]:02d}','source':f'chapters/chapter{c["number"]:02d}.tex','lang':'en'})
    search=[];stats={}
    for pos,page in enumerate(sequence):
        slug=page['slug'];n=page.get('number',0);refs=bibliography(n) if n else {}
        s=SOURCES[slug] if n else expand(MS/page['source'])
        if slug.startswith('authors-note'):
            # Drop print-only heading/font declarations, retain every prose paragraph and signature.
            raw=(MS/page['source']).read_text()
            s=uncomments(raw[raw.index('% Paragraph 01'):])
            s=s.replace('\\ChineseBody','')
        body,toc,counts=render_content(s,slug,refs,cache,n)
        if refs:
            body+='<section class="references"><h2 id="references">References<a class="heading-anchor" href="#references" aria-label="Link to references">#</a></h2><ol class="reference-list">'
            for key,item in refs.items():body+=f'<li id="ref-{ident(key)}">{item["html"]}</li>'
            body+='</ol></section>'
            toc.append({'id':'references','title':'References','number':''})
        text=plain(body)
        minutes=max(1,round((len(re.findall(r'\b\w+\b',text))/230) if page['lang']=='en' else len(text)/450))
        document=template(slug,page['title'],page['title_zh'],body,toc,page['source'],n,page['lang'],sequence[pos-1] if pos else None,sequence[pos+1] if pos+1<len(sequence) else None,minutes)
        (OUT/(slug+'.html')).write_text(document)
        stats[slug]={'sections':len(toc)-(1 if refs else 0),'figures':counts.get('figure',0),'tables':counts.get('table',0),'equations':counts.get('equation',0),'references':len(refs),'source':page['source']}
        # Section-sized records keep search snippets and destination anchors meaningful.
        sections=re.split(r'(<h2\b[^>]*id="[^"]+"[^>]*>.*?</h2>)',body)
        anchor='reading-content';heading=page['title']
        for part in sections:
            if part.startswith('<h2'):
                anchor=re.search(r'id="([^"]+)"',part)[1];heading=plain(part).rstrip('#');continue
            txt=plain(re.sub(r'<annotation[\s\S]*?</annotation>','',part))
            txt=re.sub(r'\s+',' ',txt)
            if txt:search.append({'url':slug+'.html#'+anchor,'title':page['title'],'title_zh':page['title_zh'],'heading':heading,'text':txt})
        print(f'{slug}: {counts}, {len(refs)} references',flush=True)
    cards='<p class="reading-intro">'+ui('Read the complete review manuscript, from the authors’ story to the theory, methods and studies. Choose a chapter below, or begin with the preface.','从作者自序，到理论、方法与实证，在线阅读完整评审书稿。可按顺序阅读，也可直接进入感兴趣的章节。')+'</p><div class="start-reading"><a class="reader-primary" href="preface.html">'+ui('Start with the preface →','从前言开始 →')+'</a><a href="authors-note-zh.html">作者自序 · 中文原文 →</a><a id="resume-reading" hidden></a></div>'
    cards+='<p class="reading-note">'+ui('The eleven chapters are in English. The authors’ note is available in Chinese and English. The language button changes the reading interface.','十一章正文为英文，作者自序提供中英双语。语言按钮用于切换阅读界面。')+'</p>'
    for part in range(1,5):
        part_names=[('Theory','理论基础'),('Methods and Infrastructure','方法与基础设施'),('Empirical Studies','应用与实证'),('Disciplinary Development','学科建设')]
        cards+=f'<section class="reading-part"><h2 id="part-{part}"><span class="section-number">0{part}</span> '+ui(*part_names[part-1])+'</h2><div class="reading-cards">'
        for c in CHAPTERS:
            if c['part']==part:cards+=f'<a href="chapter-{c["number"]:02d}.html"><span>{c["number"]:02d}</span><div><h3>{esc(c["title"])}</h3><p>{esc(c["title_zh"])}</p></div><span>→</span></a>'
        cards+='</div></section>'
    (OUT/'index.html').write_text(template('index','Read the book','在线阅读',cards,[{'id':f'part-{i}','title':title,'number':f'0{i}'} for i,title in enumerate(['Theory','Methods and Infrastructure','Empirical Studies','Disciplinary Development'],1)]))
    (SITE/'search-index.json').write_text(json.dumps(search,ensure_ascii=False,separators=(',',':'))+'\n')
    FIGURE_CACHE.write_text(json.dumps(cache,indent=2,sort_keys=True)+'\n')
    report={'source_commit_note':'Source hashes identify the exact canonical inputs; chapter files are never rewritten by this build.','inputs':{str(p.relative_to(ROOT)):h for p,h in sorted(INPUTS.items())},'pages':stats,'warnings':sorted(set(WARNINGS))}
    (ROOT/'verification/reader-build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    if WARNINGS:print('\n'.join(sorted(set(WARNINGS))))
    print(f'Built {len(sequence)+1} reading pages and {len(search)} search sections.')

if __name__=='__main__':main()
