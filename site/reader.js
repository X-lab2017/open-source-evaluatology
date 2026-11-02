/* Reading enhancements; all chapter text and navigation remain static HTML. */
(()=>{
  'use strict';
  const root=document.documentElement,body=document.body,$=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
  root.classList.add('js');
  const get=(key,fallback)=>{try{return localStorage.getItem(key)||fallback}catch{return fallback}};
  const save=(key,value)=>{try{localStorage.setItem(key,value)}catch{}};
  let lang=get('ose-language',navigator.language.startsWith('zh')?'zh':'en');
  const tr=(en,zh)=>lang==='zh'?zh:en;
  function language(value){lang=value==='zh'?'zh':'en';root.lang=lang;root.dataset.lang=lang;$('#language').textContent=lang==='en'?'中文':'English';save('ose-language',lang);updateResume()}
  language(lang);
  root.dataset.theme=get('ose-theme','light');
  $('#language').addEventListener('click',()=>language(lang==='en'?'zh':'en'));
  $('#theme').addEventListener('click',()=>{root.dataset.theme=root.dataset.theme==='dark'?'light':'dark';save('ose-theme',root.dataset.theme)});
  let size=Number(get('ose-reading-size',matchMedia('(max-width:600px)').matches?'18':'20'));
  function textSize(){size=Math.max(16,Math.min(26,Number.isFinite(size)?size:20));root.style.setProperty('--reading-size',size+'px');$('#type-smaller').disabled=size<=16;$('#type-larger').disabled=size>=26;save('ose-reading-size',String(size))}
  textSize();
  $('#type-smaller').addEventListener('click',()=>{size-=2;textSize();announce(tr('Text size: ','字号：')+size)});
  $('#type-larger').addEventListener('click',()=>{size+=2;textSize();announce(tr('Text size: ','字号：')+size)});
  function focusMode(value){root.classList.toggle('focus-mode',value);$('#focus-toggle').setAttribute('aria-pressed',String(value));save('ose-focus',String(value))}
  focusMode(get('ose-focus','false')==='true');
  $('#focus-toggle').addEventListener('click',()=>focusMode(!root.classList.contains('focus-mode')));
  let returnFocus=null;
  const sidebar=$('#book-navigation');
  function menu(open){
    sidebar.inert=mobile.matches&&!open;
    root.classList.toggle('nav-open',open);$('.nav-backdrop').hidden=!open;$('#contents-toggle').setAttribute('aria-expanded',String(open));
    if(open){returnFocus=document.activeElement;$('#contents-close').focus();sidebar.setAttribute('role','dialog');sidebar.setAttribute('aria-modal','true')}
    else{sidebar.removeAttribute('role');sidebar.removeAttribute('aria-modal');if(returnFocus){returnFocus.focus();returnFocus=null}}
  }
  $('#contents-toggle').addEventListener('click',()=>menu(true));$('#contents-close').addEventListener('click',()=>menu(false));$('.nav-backdrop').addEventListener('click',()=>menu(false));
  sidebar.addEventListener('click',e=>{if(e.target.closest('a')&&root.classList.contains('nav-open'))menu(false)});
  document.addEventListener('keydown',e=>{
    if(e.key==='Escape'&&root.classList.contains('nav-open'))menu(false);
    if(e.key==='Tab'&&root.classList.contains('nav-open')){
      const nodes=[...sidebar.querySelectorAll('button,a')].filter(x=>x.getClientRects().length),first=nodes[0],last=nodes[nodes.length-1];
      if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus()}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus()}
    }
  });
  const mobile=matchMedia('(max-width:900px)');sidebar.inert=mobile.matches;mobile.addEventListener('change',()=>menu(false));
  const current=sidebar.querySelector('[aria-current=page]');if(current&&!mobile.matches)sidebar.scrollTop=Math.max(0,current.offsetTop-sidebar.clientHeight*.4);
  const sections=$$('.prose h2[id]'),article=$('.prose'),progress=$('.reading-progress');let active='reading-content',scheduled=false;
  function updateProgress(){
    scheduled=false;const top=window.scrollY+112,total=Math.max(1,article.offsetTop+article.offsetHeight-innerHeight);
    const percent=Math.min(100,Math.max(0,Math.round(window.scrollY/total*100)));
    progress.firstElementChild.style.width=percent+'%';progress.setAttribute('aria-valuenow',String(percent));
    let heading=sections[0];for(const s of sections){if(s.getBoundingClientRect().top<=145)heading=s;else break}
    const id=heading&&heading.getBoundingClientRect().top<=145?heading.id:'reading-content';
    if(id!==active){active=id;$$('.section-navigation nav a').forEach(a=>{const on=a.hash==='#'+id;a.classList.toggle('is-active',on);if(on)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current')})}
  }
  addEventListener('scroll',()=>{if(!scheduled){scheduled=true;requestAnimationFrame(updateProgress)}},{passive:true});addEventListener('resize',updateProgress);updateProgress();
  function remember(){if(body.dataset.page==='index')return;save('ose-last-read',JSON.stringify({page:body.dataset.page,anchor:active,title:$('.chapter-opening h1').textContent,title_zh:$('.chinese-title').textContent,time:Date.now()}))}
  addEventListener('pagehide',remember);document.addEventListener('visibilitychange',()=>{if(document.hidden)remember()});
  let memoryTimer;addEventListener('scroll',()=>{clearTimeout(memoryTimer);memoryTimer=setTimeout(remember,800)},{passive:true});
  function updateResume(){
    const resume=$('#resume-reading');if(!resume)return;
    try{const saved=JSON.parse(get('ose-last-read','null'));if(!saved||!/^chapter-\d{2}$|^authors-note-(zh|en)$|^preface$|^book-structure$|^part-[34]-guide$/.test(saved.page))return;
      resume.href=saved.page+'.html#'+encodeURIComponent(saved.anchor||'reading-content');resume.textContent=tr('Continue reading: ','继续阅读：')+(lang==='zh'?saved.title_zh:saved.title);resume.hidden=false;
    }catch{}
  }
  let statusTimer;function announce(message){const s=$('.reader-status');s.textContent=message;s.classList.add('shown');clearTimeout(statusTimer);statusTimer=setTimeout(()=>s.classList.remove('shown'),1800)}
  // Dialogs provide native focus trapping and Escape support.
  $$('dialog [data-close]').forEach(button=>button.addEventListener('click',()=>button.closest('dialog').close()));
  $$('dialog').forEach(d=>d.addEventListener('click',e=>{if(e.target===d){const r=d.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)d.close()}}));
  const citationDialog=$('#citation-dialog'),citationDetail=citationDialog.querySelector('.citation-detail'),citationDestination=citationDialog.querySelector('.citation-destination');
  $$('.citation-link').forEach(a=>a.addEventListener('click',e=>{
    if(e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;
    const reference=document.getElementById(decodeURIComponent(a.hash.slice(1)));if(!reference)return;
    e.preventDefault();citationDetail.replaceChildren(...[...reference.childNodes].map(node=>node.cloneNode(true)));
    citationDetail.querySelectorAll('[id]').forEach(node=>node.removeAttribute('id'));
    citationDetail.querySelectorAll('a[href^="http"]').forEach(link=>{link.target='_blank';link.rel='noopener'});
    citationDestination.href=a.hash;citationDialog.showModal();
  }));
  citationDestination.addEventListener('click',()=>citationDialog.close());
  const figureDialog=$('#figure-dialog'),figureImage=figureDialog.querySelector('img');let zoom=100;
  $$('.figure-zoom').forEach(a=>a.addEventListener('click',e=>{if(e.ctrlKey||e.metaKey||e.shiftKey)return;e.preventDefault();figureImage.src=a.href;figureImage.alt=a.querySelector('img').alt;figureDialog.querySelector('.original-figure').href=a.href;zoom=100;figureImage.style.width='100%';figureDialog.showModal()}));
  $('#zoom-in').addEventListener('click',()=>{zoom=Math.min(400,zoom+50);figureImage.style.width=zoom+'%'});$('#zoom-out').addEventListener('click',()=>{zoom=Math.max(50,zoom-50);figureImage.style.width=zoom+'%'});
  // Local search is fetched only when used. It sends no query to an external service.
  const searchDialog=$('#search-dialog'),input=$('#book-search'),results=$('#search-results'),searchStatus=$('#search-status');let index=null,loading=null,queryTimer;
  async function loadIndex(){if(index)return index;if(!loading)loading=fetch('../search-index.json').then(r=>{if(!r.ok)throw Error('Search index unavailable');return r.json()}).then(data=>index=data).catch(err=>{loading=null;throw err});return loading}
  async function openSearch(){searchDialog.showModal();input.focus();try{await loadIndex();if(input.value.trim())runSearch()}catch{searchStatus.textContent=tr('Search could not load. Please try again.','搜索暂未加载，请重试。')}}
  $('#search-open').addEventListener('click',openSearch);
  document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();if(!searchDialog.open)openSearch()} });
  function highlighted(text,terms){const fragment=document.createDocumentFragment(),low=text.toLowerCase();let at=0;while(at<text.length){let next=-1,term='';for(const t of terms){const p=low.indexOf(t,at);if(p>=0&&(next<0||p<next)){next=p;term=t}}if(next<0){fragment.append(text.slice(at));break}fragment.append(text.slice(at,next));const mark=document.createElement('mark');mark.textContent=text.slice(next,next+term.length);fragment.append(mark);at=next+term.length}return fragment}
  async function runSearch(){
    const query=input.value.trim().toLowerCase();results.replaceChildren();if(query.length<2){searchStatus.textContent=tr('Enter at least two characters.','请输入至少两个字符。');return}
    searchStatus.textContent=tr('Searching…','正在搜索…');
    let data;try{data=await loadIndex()}catch{searchStatus.textContent=tr('Search could not load. Please try again.','搜索暂未加载，请重试。');return}
    if(input.value.trim().toLowerCase()!==query)return;
    const terms=query.split(/\s+/).slice(0,8);
    const matches=data.map(item=>{const title=(item.title+' '+item.title_zh+' '+item.heading).toLowerCase(),full=title+' '+item.text.toLowerCase();return {item,score:terms.every(t=>full.includes(t))?terms.reduce((s,t)=>s+(title.includes(t)?5:1),0):0}}).filter(x=>x.score).sort((a,b)=>b.score-a.score);
    searchStatus.textContent=tr(`${matches.length} sections found${matches.length>30?' · showing the first 30':''}`,`找到 ${matches.length} 处${matches.length>30?' · 显示前 30 处':''}`);
    if(!matches.length){searchStatus.textContent=tr('No matches. Try a shorter phrase or an English term.','未找到结果。可尝试更短的词句或英文术语。');return}
    for(const {item} of matches.slice(0,30)){
      const a=document.createElement('a');a.className='search-result';a.href=item.url;const small=document.createElement('small');small.textContent=lang==='zh'?item.title_zh:item.title;const strong=document.createElement('strong');strong.append(highlighted(item.heading,terms));
      const low=item.text.toLowerCase(),p=terms.map(t=>low.indexOf(t)).find(n=>n>=0)||0,start=Math.max(0,p-75),end=Math.min(item.text.length,start+260),snippet=(start?'…':'')+item.text.slice(start,end)+(end<item.text.length?'…':'');const excerpt=document.createElement('p');excerpt.append(highlighted(snippet,terms));a.append(small,strong,excerpt);a.addEventListener('click',()=>searchDialog.close());results.append(a);
    }
  }
  input.addEventListener('input',()=>{clearTimeout(queryTimer);queryTimer=setTimeout(runSearch,160)});
})();
