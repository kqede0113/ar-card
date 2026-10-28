"""Small shared catalog API; run behind HTTPS in production."""
import base64
import mimetypes
import subprocess
import urllib.request
import urllib.error
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
env_file = ROOT / '.env.local'
if env_file.exists():
    for line in env_file.read_text(encoding='utf-8').splitlines():
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ.setdefault(key, value)

PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH', '')
if not PASSWORD_HASH:
    raise SystemExit('Set ADMIN_PASSWORD_HASH before starting the admin API.')
DATA = Path(os.environ.get('DATA_DIR', str(ROOT / 'data')))
DATA.mkdir(parents=True, exist_ok=True)
DB = DATA / 'catalog.sqlite3'
CATALOG = json.loads(Path(os.environ.get('CATALOG_FILE', str(ROOT / 'catalog.json'))).read_text(encoding='utf-8'))
KNOWN = {work['id'] for work in CATALOG}
GALLERY = Path(os.environ.get('GALLERY_DIR', str(ROOT.parent / 'gallery')))
PUBLISH_REPO = os.environ.get('GITHUB_REPOSITORY', 'kqede0113/ar-card')
publish_lock = threading.Lock()
catalog_write_lock = threading.Lock()
ORIGINS = set(os.environ.get('ALLOWED_ORIGINS', 'https://kqede0113.github.io,http://127.0.0.1:5088,http://localhost:5088,http://127.0.0.1:5090,http://localhost:5090').split(','))
sessions, attempts = {}, {}
lock = threading.Lock()
SESSION_SECONDS = 3 * 60 * 60


@contextmanager
def database():
    connection = sqlite3.connect(DB, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


with database() as connection:
    connection.execute('CREATE TABLE IF NOT EXISTS edits (id TEXT PRIMARY KEY, price INTEGER, description TEXT NOT NULL, sold_out INTEGER NOT NULL, version INTEGER NOT NULL, updated_at INTEGER NOT NULL, published_version INTEGER NOT NULL DEFAULT 0)')


def works():
    with database() as connection:
        edits = {row['id']: dict(row) for row in connection.execute('SELECT * FROM edits')}
    result = []
    for original in CATALOG:
        item = {**original, 'soldOut': False, 'version': 0}
        if original['id'] in edits:
            row = edits[original['id']]
            item.update(price=row['price'], description=row['description'], soldOut=bool(row['sold_out']), version=row['version'], updatedAt=row['updated_at'])
        result.append(item)
    return result


def save_local_catalog():
    with catalog_write_lock:
        destination = GALLERY / 'works.json'
        temporary = destination.with_suffix('.json.tmp')
        public = [{key: value for key, value in item.items() if key not in ('version', 'updatedAt')} for item in works()]
        temporary.write_text(json.dumps(public, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(destination)


def github_request(path, token, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request('https://api.github.com/repos/' + PUBLISH_REPO + path, data=data, method='GET' if payload is None else 'PUT', headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json', 'Content-Type': 'application/json', 'User-Agent': 'DCC-local-gallery-admin', 'X-GitHub-Api-Version': '2022-11-28'})
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.load(response)


def publish():
    with publish_lock:
        with database() as connection:
            pending = {row['id']: dict(row) for row in connection.execute('SELECT * FROM edits WHERE version > published_version')}
        if not pending:
            return {'ok': True, 'changed': False, 'message': '公開する変更はありません。'}
        token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
        if not token:
            try:
                result = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True, timeout=10, check=True)
                token = result.stdout.strip()
            except (subprocess.SubprocessError, OSError):
                raise RuntimeError('このPCでGitHubへのログインが必要です。初回設定を確認してください。')
        current = github_request('/contents/gallery/works.json?ref=main', token)
        remote = json.loads(base64.b64decode(current['content']))
        found = set()
        for item in remote:
            if item['id'] in pending:
                row = pending[item['id']]
                item.update(price=row['price'], description=row['description'], soldOut=bool(row['sold_out']))
                found.add(item['id'])
        if found != set(pending):
            raise RuntimeError('公開先の作品一覧が変わっています。設定を確認してください。')
        content = json.dumps(remote, ensure_ascii=False, indent=2).encode()
        result = github_request('/contents/gallery/works.json', token, {'message': 'Update work prices, descriptions and availability from local admin', 'branch': 'main', 'sha': current['sha'], 'content': base64.b64encode(content).decode()})
        with database() as connection:
            for key, row in pending.items():
                connection.execute('UPDATE edits SET published_version=? WHERE id=?', (row['version'], key))
        return {'ok': True, 'changed': True, 'commit': result['commit']['sha'], 'message': 'GitHubへ公開しました。サイトへの反映まで少しお待ちください。'}


def password_matches(password):
    try:
        kind, salt, expected = PASSWORD_HASH.split('$')
        if kind != 'scrypt' or not isinstance(password, str) or len(password) > 256:
            return False
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1, maxmem=64 * 1024 * 1024).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


class Handler(BaseHTTPRequestHandler):
    server_version = 'DCCGallery'

    def origin_allowed(self):
        origin = self.headers.get('Origin')
        return not origin or origin in ORIGINS

    def reply(self, code, value=None):
        body = b'' if value is None else json.dumps(value, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        origin = self.headers.get('Origin')
        if origin in ORIGINS:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
        self.end_headers()
        self.wfile.write(body)

    def json_body(self, limit=32768):
        length = int(self.headers.get('Content-Length', '0'))
        if not 0 < length <= limit or self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            raise ValueError('Invalid request')
        body = json.loads(self.rfile.read(length))
        if not isinstance(body, dict):
            raise ValueError('Invalid request')
        return body

    def session_key(self):
        authorization = self.headers.get('Authorization', '')
        if not authorization.startswith('Bearer '):
            return None
        key = hashlib.sha256(authorization[7:].encode()).hexdigest()
        with lock:
            if sessions.get(key, 0) <= time.time():
                sessions.pop(key, None)
                return None
        return key

    def do_OPTIONS(self):
        if not self.origin_allowed():
            self.reply(403, {'error': 'アクセスできません。'})
            return
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', self.headers.get('Origin', ''))
        self.send_header('Vary', 'Origin')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PATCH, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Max-Age', '600')
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_GET(self):
        path = urlsplit(self.path).path.rstrip('/')
        static = {'/admin': 'admin.html', '/admin/admin.html': 'admin.html', '/admin/admin.js': 'admin.js', '/admin/api.js': 'api.js', '/admin/styles.css': 'styles.css', '/admin/config.json': 'config.json', '/admin/logo.jpg': 'logo.jpg'}
        filename = static.get(path)
        if path.startswith('/admin/posters/') and path.removeprefix('/admin/posters/').removesuffix('.webp') in KNOWN:
            filename = 'posters/' + path.rsplit('/', 1)[-1]
        if filename:
            file = GALLERY / filename
            if not file.is_file():
                self.reply(404, {'error': '見つかりません。'})
                return
            body = file.read_bytes()
            content_type = 'text/javascript' if file.suffix == '.js' else mimetypes.guess_type(str(file))[0] or 'application/octet-stream'
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.end_headers()
            self.wfile.write(body)
        elif path == '/api/health':
            self.reply(200, {'ok': True})
        elif path == '/api/works':
            self.reply(200, works())
        elif path == '/api/session':
            self.reply(200 if self.session_key() else 401, {'authenticated': bool(self.session_key())})
        else:
            self.reply(404, {'error': '見つかりません。'})

    def do_POST(self):
        if not self.origin_allowed():
            self.reply(403, {'error': 'アクセスできません。'})
            return
        path = urlsplit(self.path).path.rstrip('/')
        if path == '/api/logout':
            key = self.session_key()
            with lock:
                sessions.pop(key, None)
            self.reply(200, {'ok': True})
            return
        if path == '/api/publish':
            if not self.session_key():
                self.reply(401, {'error': 'ログインし直してください。'})
                return
            try:
                self.reply(200, publish())
            except urllib.error.HTTPError as error:
                message = 'GitHubへのログインが必要です。初回設定を確認してください。' if error.code in (401, 403) else 'GitHubへの公開に失敗しました。もう一度お試しください。'
                self.reply(502, {'error': message})
            except (RuntimeError, OSError, ValueError, KeyError, subprocess.SubprocessError):
                self.reply(502, {'error': 'このPCでGitHubへのログインが必要です。初回設定を確認してください。'})
            return
        if path != '/api/login':
            self.reply(404, {'error': '見つかりません。'})
            return
        address, now = self.client_address[0], time.time()
        with lock:
            for key in list(attempts):
                attempts[key] = [stamp for stamp in attempts[key] if now - stamp < 300]
                if not attempts[key]:
                    del attempts[key]
            if len(attempts.get(address, [])) >= 5 or sum(map(len, attempts.values())) >= 100:
                self.reply(429, {'error': '少し時間をおいてから、もう一度お試しください。'})
                return
            attempts.setdefault(address, []).append(now)
        try:
            body = self.json_body(2048)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            self.reply(400, {'error': '入力を確認してください。'})
            return
        if not password_matches(body.get('password')):
            self.reply(401, {'error': 'パスワードが違います。'})
            return
        token = secrets.token_urlsafe(32)
        with lock:
            for key in list(sessions):
                if sessions[key] < now:
                    del sessions[key]
            sessions[hashlib.sha256(token.encode()).hexdigest()] = now + SESSION_SECONDS
            attempts.pop(address, None)
        self.reply(200, {'token': token, 'expiresIn': SESSION_SECONDS})

    def do_PATCH(self):
        if not self.origin_allowed():
            self.reply(403, {'error': 'アクセスできません。'})
            return
        if not self.session_key():
            self.reply(401, {'error': 'ログインし直してください。'})
            return
        path = urlsplit(self.path).path.rstrip('/')
        key = path.removeprefix('/api/works/')
        if not path.startswith('/api/works/') or key not in KNOWN:
            self.reply(404, {'error': '作品が見つかりません。'})
            return
        try:
            body = self.json_body()
            if set(body) != {'price', 'description', 'soldOut', 'version'}:
                raise ValueError()
            if type(body['price']) is not int or not 0 <= body['price'] <= 1000000:
                raise ValueError()
            if not isinstance(body['description'], str) or len(body['description']) > 10000:
                raise ValueError()
            if type(body['soldOut']) is not bool or type(body['version']) is not int:
                raise ValueError()
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            self.reply(400, {'error': '価格・説明文・売り切れの入力を確認してください。'})
            return
        with database() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row = connection.execute('SELECT version FROM edits WHERE id=?', (key,)).fetchone()
            current = row['version'] if row else 0
            if current != body['version']:
                self.reply(409, {'error': 'ほかの画面で更新されています。読み込み直してから編集してください。'})
                return
            connection.execute('INSERT INTO edits (id,price,description,sold_out,version,updated_at) VALUES (?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET price=excluded.price, description=excluded.description, sold_out=excluded.sold_out, version=excluded.version, updated_at=excluded.updated_at', (key, body['price'], body['description'], int(body['soldOut']), current + 1, int(time.time())))
        save_local_catalog()
        self.reply(200, next(work for work in works() if work['id'] == key))


if __name__ == '__main__':
    address = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', '5090'))
    print(f'DCC gallery API listening on {address}:{port}', flush=True)
    ThreadingHTTPServer((address, port), Handler).serve_forever()
