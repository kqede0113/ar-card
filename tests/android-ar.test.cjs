const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function setup({android = true, framed = false, rejects = false} = {}) {
  const timers = new Map(); let sequence = 0;
  const element = () => ({hidden: false, disabled: false, textContent: '', style: {}, listeners: {}, attributes: {}, setAttribute(name, value) { this.attributes[name] = value; },
    classList: {toggle() {}}, addEventListener(name, listener) { this.listeners[name] = listener; }});
  const elements = Object.fromEntries(['avatar-viewer', 'launch-ar', 'launch-label', 'ar-message', 'progress-fill', 'android-help', 'open-ar-page'].map(id => [id, element()]));
  elements['android-help'].hidden = elements['open-ar-page'].hidden = true;
  const links = [{target: '', rel: ''}, {target: '', rel: ''}];
  const document = {hidden: false, listeners: {}, getElementById: id => elements[id], querySelectorAll: () => links,
    addEventListener(name, listener) { this.listeners[name] = listener; }};
  const window = {self: {}, listeners: {}, addEventListener(name, listener) { this.listeners[name] = listener; }};
  window.top = framed ? {} : window.self;
  let activations = 0;
  elements['avatar-viewer'].canActivateAR = true;
  elements['avatar-viewer'].activateAR = () => { activations++; return rejects ? Promise.reject(Error('Cannot launch AR')) : Promise.resolve(); };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../app.js'), 'utf8'), {
    document, window, navigator: {userAgent: android ? 'Mozilla/5.0 (Linux; Android 15) Chrome/124' : 'Mozilla/5.0 (iPhone) Safari'},
    customElements: {get: () => ({})},
    setTimeout: (fn, delay) => { timers.set(++sequence, {fn, delay}); return sequence; }, clearTimeout: id => timers.delete(id)
  });
  const event = (type, detail = {}) => elements['avatar-viewer'].listeners[type]({detail});
  const run = delay => { for (const [id, timer] of [...timers]) if (timer.delay === delay) { timers.delete(id); timer.fn(); } };
  return {elements, links, document, window, timers, event, run, activations: () => activations,
    load() { event('load'); }, click() { elements['launch-ar'].listeners.click(); }};
}

(async () => {
  const framed = setup({framed: true}); framed.load(); framed.click();
  assert.match(framed.elements['avatar-viewer'].attributes.src, /android-compatible-20261029/);
  assert.equal(framed.elements['launch-ar'].hidden, true);
  assert.equal(framed.elements['open-ar-page'].hidden, false);
  assert.match(framed.elements['open-ar-page'].attributes.href, /^intent:\/\/arvr\.google\.com/);
  assert.match(framed.elements['open-ar-page'].attributes.href, /android-compatible-20261029/);
  assert.match(framed.elements['open-ar-page'].innerHTML, /ARで開く/);
  assert.equal(framed.activations(), 0, 'Never launch AR inside Hark iframe');
  assert.ok(framed.links.every(link => link.target === '_blank' && link.rel.includes('noopener')));
  framed.event('error');
  assert.match(framed.elements['ar-message'].textContent, /別の画面/);

  const stalled = setup(); stalled.load(); stalled.click();
  assert.equal(stalled.activations(), 1);
  assert.equal(stalled.elements['launch-ar'].disabled, true);
  stalled.run(12000);
  assert.equal(stalled.elements['android-help'].hidden, false);
  assert.equal(stalled.elements['launch-ar'].disabled, false);
  assert.match(stalled.elements['ar-message'].textContent, /開いていない場合/);
  stalled.window.listeners.focus(); stalled.run(2200);
  assert.match(stalled.elements['ar-message'].textContent, /開いていない場合/, 'Focus/load recheck must not erase failure help');
  stalled.click(); assert.equal(stalled.activations(), 2);
  assert.equal(stalled.elements['android-help'].hidden, true);

  const rejected = setup({rejects: true}); rejected.load(); rejected.click();
  await Promise.resolve();
  assert.match(rejected.elements['ar-message'].textContent, /起動できません/);
  assert.equal(rejected.elements['android-help'].hidden, false);

  const native = setup(); native.load(); native.click();
  native.document.hidden = true; native.document.listeners.visibilitychange(); native.run(12000);
  assert.equal(native.elements['android-help'].hidden, true, 'No timeout while native AR app is foreground');
  native.document.hidden = false; native.document.listeners.visibilitychange();
  assert.match(native.elements['ar-message'].textContent, /ARから戻りました/);
  assert.equal(native.elements['launch-ar'].disabled, false);

  const webxr = setup(); webxr.load(); webxr.click(); webxr.event('ar-status', {status: 'session-started'}); webxr.run(12000);
  assert.equal(webxr.elements['android-help'].hidden, true);
  webxr.event('ar-status', {status: 'not-presenting'});
  assert.equal(webxr.elements['launch-ar'].disabled, false);
  webxr.click(); webxr.event('ar-status', {status: 'failed'});
  assert.equal(webxr.elements['android-help'].hidden, false);

  const unsupported = setup(); unsupported.elements['avatar-viewer'].canActivateAR = false; unsupported.load();
  assert.equal(unsupported.elements['launch-ar'].disabled, true);
  assert.equal(unsupported.elements['android-help'].hidden, false);
  assert.match(unsupported.elements['ar-message'].textContent, /3Dモデル/);
  unsupported.elements['avatar-viewer'].canActivateAR = true; unsupported.run(800);
  assert.equal(unsupported.elements['launch-ar'].disabled, false, 'Delayed AR capability detection must still enable launch');

  for (const isFramed of [false, true]) {
    const ios = setup({android: false, framed: isFramed}); ios.load(); ios.click(); ios.run(12000);
    assert.equal(ios.activations(), 1);
    assert.equal(ios.elements['launch-ar'].hidden, false);
    assert.equal(ios.elements['open-ar-page'].hidden, true);
    assert.equal(ios.elements['android-help'].hidden, true);
    assert.equal(ios.links[0].target, '', 'iPhone navigation is unchanged');
    assert.equal(ios.elements['avatar-viewer'].attributes.src, undefined, 'iPhone model URL is unchanged');
    assert.match(ios.elements['ar-message'].textContent, /ARを開いています/);
  }
  console.log('PASS: Android iframe escape, timeout/retry, rejection, focus, native app return, WebXR, unsupported device; iPhone unchanged.');
})().catch(error => { console.error(error); process.exitCode = 1; });
