import {apiBase, request} from './api.js?v=admin-20261028';
const loginPanel = document.getElementById('login-panel');
const editorPanel = document.getElementById('editor-panel');
const loginStatus = document.getElementById('login-status');
const adminStatus = document.getElementById('admin-status');
let token = '';
try { token = sessionStorage.getItem('dcc-gallery-session') || ''; } catch {}
function session(value) {
  token = value;
  try { if (value) sessionStorage.setItem('dcc-gallery-session', value); else sessionStorage.removeItem('dcc-gallery-session'); } catch {}
}
function showLogin(message = '') {
  session('');
  editorPanel.hidden = true;
  loginPanel.hidden = false;
  document.getElementById('editors').replaceChildren();
  loginStatus.textContent = message;
}
function field(label, element) {
  const wrapper = document.createElement('label');
  wrapper.className = 'admin-field';
  const text = document.createElement('span');
  text.textContent = label;
  wrapper.append(text, element);
  return wrapper;
}
async function loadEditors() {
  const works = await request('/works', {token});
  const editors = document.getElementById('editors');
  editors.replaceChildren();
  for (const work of works) {
    let version = work.version;
    const form = document.createElement('form');
    form.className = 'admin-work';
    form.dataset.id = work.id;
    const header = document.createElement('div');
    header.className = 'admin-work-heading';
    const image = document.createElement('img');
    image.src = 'posters/' + work.id + '.webp'; image.alt = ''; image.width = 80; image.height = 80;
    const name = document.createElement('h2'); name.textContent = work.name;
    header.append(image, name);
    const fields = document.createElement('fieldset');
    const price = document.createElement('input');
    price.type = 'number'; price.name = 'price'; price.min = '0'; price.max = '1000000'; price.step = '1'; price.required = true; price.value = work.price;
    const description = document.createElement('textarea');
    description.name = 'description'; description.rows = 6; description.maxLength = 10000; description.value = work.description;
    const soldOut = document.createElement('input');
    soldOut.type = 'checkbox'; soldOut.name = 'soldOut'; soldOut.checked = !!work.soldOut;
    const soldLabel = field('売り切れ', soldOut); soldLabel.classList.add('admin-stock');
    fields.append(soldLabel, field('価格（円）', price), field('説明文', description));
    const save = document.createElement('button');
    save.type = 'submit'; save.className = 'admin-primary'; save.textContent = '保存する';
    const message = document.createElement('p'); message.className = 'save-status'; message.setAttribute('role', 'status');
    form.append(header, fields, save, message);
    form.addEventListener('submit', async event => {
      event.preventDefault(); if (!form.reportValidity()) return;
      const payload = {price: Number(price.value), description: description.value, soldOut: soldOut.checked, version};
      fields.disabled = true; save.disabled = true; message.textContent = '保存しています…'; message.classList.remove('is-error');
      try {
        const updated = await request('/works/' + encodeURIComponent(work.id), {method: 'PATCH', token, body: JSON.stringify(payload)});
        version = updated.version; message.textContent = 'このPCに保存しました。公開ボタンでサイトへ反映できます。';
      } catch (error) {
        if (error.status === 401) { showLogin('ログインし直してください。'); return; }
        message.textContent = error.message; message.classList.add('is-error');
      } finally { fields.disabled = false; save.disabled = false; }
    });
    editors.append(form);
  }
}
async function showEditor() {
  loginPanel.hidden = true; editorPanel.hidden = false; adminStatus.textContent = '読み込んでいます…';
  try { await loadEditors(); adminStatus.textContent = ''; }
  catch (error) { if (error.status === 401) showLogin('ログインし直してください。'); else adminStatus.textContent = error.message; }
}
document.getElementById('login-form').addEventListener('submit', async event => {
  event.preventDefault();
  const button = document.getElementById('login-button');
  const password = document.getElementById('password');
  button.disabled = true; loginStatus.textContent = '確認しています…';
  try {
    const result = await request('/login', {method: 'POST', body: JSON.stringify({password: password.value})});
    password.value = ''; session(result.token); await showEditor();
  } catch (error) { loginStatus.textContent = error.message; }
  finally { button.disabled = false; }
});
document.getElementById('logout').addEventListener('click', async () => {
  try { await request('/logout', {method: 'POST', token}); } catch {}
  showLogin('ログアウトしました。');
});
document.getElementById('reload-works').addEventListener('click', showEditor);
try {
  if (!await apiBase()) {
    loginStatus.textContent = '管理画面を準備しています。';
    document.getElementById('login-button').disabled = true;
    document.getElementById('password').disabled = true;
  } else if (token) {
    try { await request('/session', {token}); await showEditor(); }
    catch { showLogin('ログインし直してください。'); }
  }
} catch { loginStatus.textContent = '接続できませんでした。時間をおいてお試しください。'; }

document.getElementById('publish').addEventListener('click',async()=>{
 const button=document.getElementById('publish'),message=document.getElementById('publish-status');button.disabled=true;message.textContent='公開しています…';
 try{const result=await request('/publish',{method:'POST',token});message.textContent=result.message;}
 catch(error){if(error.status===401)showLogin('ログインし直してください。');else message.textContent=error.message;}
 finally{button.disabled=false;}
});
