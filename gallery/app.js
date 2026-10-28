import {catalog} from './api.js?v=admin-20261028';
const viewer=document.getElementById('viewer'),title=document.getElementById('piece-title'),description=document.getElementById('description'),status=document.getElementById('viewer-status'),grid=document.getElementById('works-grid');
let works=[],current='',loadingTimer,refreshing=false;
function note(text){status.hidden=false;status.textContent=text;}
function reset(){viewer.cameraOrbit='25deg 72deg auto';viewer.cameraTarget='auto auto auto';viewer.fieldOfView='32deg';viewer.jumpCameraToGoal?.();}
function updateCopy(work){
 title.textContent=work.name;description.replaceChildren();
 const price=document.getElementById('piece-price');price.hidden=!Number.isFinite(work.price);price.textContent=Number.isFinite(work.price)?work.price.toLocaleString('ja-JP')+'円':'';
 document.getElementById('piece-stock').hidden=!work.soldOut;
 work.description.split(/\n\s*\n/).filter(Boolean).forEach(text=>{const p=document.createElement('p');p.textContent=text;description.append(p);});
 document.getElementById('piece-number').textContent=String(works.findIndex(w=>w.id===work.id)+1).padStart(2,'0')+' / '+String(works.length).padStart(2,'0');
}
function select(id,fromCard=false){
 const work=works.find(w=>w.id===id);if(!work)return;
 updateCopy(work);grid.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.id===id)));
 if(current!==id){current=id;clearTimeout(loadingTimer);note('作品を読み込んでいます…');viewer.alt=work.name;viewer.poster='posters/'+work.id+'.webp';viewer.src='models/'+work.id+'.glb';reset();loadingTimer=setTimeout(()=>note('読み込みに時間がかかっています。通信を確認して再読み込みしてください。'),30000);}
 if(fromCard){history.replaceState(null,'','#'+id);document.querySelector('.showcase').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});}
}
function renderCards(){
 const focused=document.activeElement?.dataset.id;grid.replaceChildren();
 for(const work of works){
  const button=document.createElement('button');button.type='button';button.className='work-card';button.dataset.id=work.id;button.setAttribute('aria-pressed',String(work.id===current));button.classList.toggle('is-sold-out',!!work.soldOut);
  const art=document.createElement('span');art.className='work-art';const image=document.createElement('img');image.src='posters/'+work.id+'.webp';image.alt='';image.width=600;image.height=600;image.loading='lazy';art.append(image);
  if(work.soldOut){const badge=document.createElement('span');badge.className='stock-badge';badge.textContent='売り切れ';art.append(badge);}
  const name=document.createElement('span');name.className='work-name';const text=document.createElement('span');text.textContent=work.name;const arrow=document.createElement('span');arrow.textContent='↗';arrow.setAttribute('aria-hidden','true');name.append(text,arrow);button.append(art,name);
  if(Number.isFinite(work.price)){const price=document.createElement('span');price.className='work-card-price';price.textContent=work.price.toLocaleString('ja-JP')+'円';button.append(price);}
  button.addEventListener('click',()=>select(work.id,true));grid.append(button);
 }
 if(focused){const previous=[...grid.querySelectorAll('button')].find(b=>b.dataset.id===focused);previous?.focus({preventScroll:true});}
}
async function refresh(){
 if(refreshing||document.hidden)return;refreshing=true;
 try{
  const next=await catalog();if(!Array.isArray(next)||!next.length)throw Error('作品がありません。');
  if(JSON.stringify(next)!==JSON.stringify(works)){
   works=next;document.getElementById('works-count').textContent=String(works.length).padStart(2,'0')+' WORKS';renderCards();
   select(works.some(w=>w.id===current)?current:works.some(w=>w.id===location.hash.slice(1))?location.hash.slice(1):works[0].id);
  }
 }catch{if(!works.length)note('作品情報を読み込めませんでした。ページを再読み込みしてください。');}
 finally{refreshing=false;}
}
viewer.addEventListener('progress',e=>{if(e.detail.totalProgress<1)note('作品を読み込んでいます… '+Math.round(e.detail.totalProgress*100)+'%');});
viewer.addEventListener('load',()=>{clearTimeout(loadingTimer);status.hidden=true;});
viewer.addEventListener('error',()=>{clearTimeout(loadingTimer);note('作品を読み込めませんでした。通信を確認して、もう一度お試しください。');});
document.getElementById('reset').addEventListener('click',reset);
window.addEventListener('hashchange',()=>select(location.hash.slice(1)));
window.addEventListener('focus',refresh);document.addEventListener('visibilitychange',refresh);setInterval(refresh,20000);refresh();
setTimeout(()=>{if(!customElements.get('model-viewer'))note('3D表示を読み込めませんでした。通信を確認してください。');},15000);
