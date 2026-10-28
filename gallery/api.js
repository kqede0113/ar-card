const release = new URL(import.meta.url).search;
let configuration;
export async function apiBase() {
  if (!configuration) configuration = (async () => {
    const response = await fetch('config.json' + release, {cache: 'no-store'});
    if (!response.ok) throw Error('接続設定を読み込めませんでした。');
    const config = await response.json();
    if (config.apiBaseUrl) return String(config.apiBaseUrl).replace(/\/$/, '');
    if (['localhost', '127.0.0.1'].includes(location.hostname)) return 'http://127.0.0.1:5090/api';
    return null;
  })();
  return configuration;
}
export async function request(path, {token, ...options} = {}) {
  const base = await apiBase();
  if (!base) throw Error('管理画面を準備しています。');
  const headers = {...options.headers};
  if (options.body) headers['Content-Type'] = 'application/json';
  if (token) headers.Authorization = 'Bearer ' + token;
  const response = await fetch(base + path, {...options, headers, cache: 'no-store', signal: AbortSignal.timeout(path === '/publish' ? 60000 : 10000)});
  const data = await response.json();
  if (!response.ok) {
    const error = Error(data.error || '通信に失敗しました。');
    error.status = response.status;
    throw error;
  }
  return data;
}
export async function catalog() {
  if (await apiBase()) return request('/works');
  const url = new URL('works.json' + release, location.href);
  url.searchParams.set('updated', String(Math.floor(Date.now() / 20000)));
  const response = await fetch(url, {cache: 'no-store'});
  if (!response.ok) throw Error('作品一覧を読み込めませんでした。');
  return response.json();
}
