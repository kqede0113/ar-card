const viewer=document.getElementById('viewer');
const title=document.getElementById('piece-title');
const description=document.getElementById('description');
const status=document.getElementById('viewer-status');
const grid=document.getElementById('works-grid');
let works=[],current='',loadingTimer;
function note(text){status.hidden=false;status.textContent=text;}
function reset(){viewer.cameraOrbit='25deg 72deg auto';viewer.cameraTarget='auto auto auto';viewer.fieldOfView='32deg';viewer.jumpCameraToGoal?.();}
function select(id,fromCard=false){
 const index=works.findIndex(w=>w.id===id);if(index<0||id===current)return;
 const work=works[index];current=id;clearTimeout(loadingTimer);title.textContent=work.name;description.replaceChildren();
 const price=document.getElementById('piece-price');price.hidden=!Number.isFinite(work.price);price.textContent=Number.isFinite(work.price)?work.price.toLocaleString('ja-JP')+'円':'';
 work.description.split(/\n\s*\n/).filter(Boolean).forEach(text=>{const paragraph=document.createElement('p');paragraph.textContent=text;description.append(paragraph);});
 document.getElementById('piece-number').textContent=String(index+1).padStart(2,'0')+' / '+String(works.length).padStart(2,'0');
 grid.querySelectorAll('button').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.id===id)));
 note('作品を読み込んでいます…');viewer.alt=work.name;viewer.poster='posters/'+work.id+'.webp';viewer.src='models/'+work.id+'.glb';reset();
 loadingTimer=setTimeout(()=>note('読み込みに時間がかかっています。通信を確認して、ページを再読み込みしてください。'),30000);
 if(fromCard){history.replaceState(null,'','#'+id);document.querySelector('.showcase').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});}
}
viewer.addEventListener('progress',event=>{if(event.detail.totalProgress<1)note('作品を読み込んでいます… '+Math.round(event.detail.totalProgress*100)+'%');});
viewer.addEventListener('load',()=>{clearTimeout(loadingTimer);status.hidden=true;});
viewer.addEventListener('error',()=>{clearTimeout(loadingTimer);note('作品を読み込めませんでした。通信を確認して、もう一度お試しください。');});
document.getElementById('reset').addEventListener('click',reset);
fetch('works.json'+new URL(import.meta.url).search).then(response=>{if(!response.ok)throw Error(response.status);return response.json();}).then(data=>{
 works=data;document.getElementById('works-count').textContent=String(works.length).padStart(2,'0')+' WORKS';
 for(const [index,work] of works.entries()){
  const button=document.createElement('button');button.type='button';button.className='work-card';button.dataset.id=work.id;button.setAttribute('aria-pressed','false');
  const art=document.createElement('span');art.className='work-art';const image=document.createElement('img');image.src='posters/'+work.id+'.webp';image.alt='';image.width=600;image.height=600;image.loading='lazy';art.append(image);
  const name=document.createElement('span');name.className='work-name';const text=document.createElement('span');text.textContent=work.name;const arrow=document.createElement('span');arrow.textContent='↗';arrow.setAttribute('aria-hidden','true');name.append(text,arrow);button.append(art,name);if(Number.isFinite(work.price)){const price=document.createElement('span');price.className='work-card-price';price.textContent=work.price.toLocaleString('ja-JP')+'円';button.append(price);}button.addEventListener('click',()=>select(work.id,true));grid.append(button);
 }
 select(works.some(w=>w.id===location.hash.slice(1))?location.hash.slice(1):works[0].id);
 window.addEventListener('hashchange',()=>select(location.hash.slice(1)));
}).catch(()=>note('作品一覧を読み込めませんでした。ページを再読み込みしてください。'));
setTimeout(()=>{if(!customElements.get('model-viewer'))note('3D表示を読み込めませんでした。通信を確認してください。');},15000);
