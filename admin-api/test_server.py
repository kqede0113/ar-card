"""Exercise auth, persistence, conflict detection and publication without live writes."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as directory:
    temp = Path(directory)
    salt = b'isolated-test-salt'
    password = 'test-password-only'
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, maxmem=64 * 1024 * 1024).hex()
    os.environ.update(ADMIN_PASSWORD_HASH='scrypt$' + salt.hex() + '$' + digest, DATA_DIR=str(temp / 'data'), GALLERY_DIR=str(temp), CATALOG_FILE=str(ROOT / 'catalog.json'))
    spec = importlib.util.spec_from_file_location('isolated_gallery_server', ROOT / 'server.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    server = module.ThreadingHTTPServer(('127.0.0.1', 0), module.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'

    def call(path, method='GET', data=None, token=None, origin='http://127.0.0.1:5090'):
        headers = {'Origin': origin}
        if data is not None:
            headers['Content-Type'] = 'application/json'
        if token:
            headers['Authorization'] = 'Bearer ' + token
        request = urllib.request.Request(base + path, method=method, headers=headers, data=None if data is None else json.dumps(data).encode())
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as response:
            return response.code, json.load(response)

    try:
        assert call('/api/health')[0] == 200
        original = call('/api/works')[1]
        assert len(original) == 8
        assert next(work for work in original if work['id'] == 'dragon')['price'] == 500
        payload = {'price': 432, 'description': '<test> plain text\nSecond line', 'soldOut': True, 'version': 0}
        assert call('/api/works/deer', 'PATCH', payload)[0] == 401
        assert call('/api/login', 'POST', {'password': 'wrong'})[0] == 401
        assert call('/api/login', 'POST', {'password': password}, origin='https://unexpected.example')[0] == 403
        code, login = call('/api/login', 'POST', {'password': password})
        assert code == 200 and len(login['token']) > 30
        token = login['token']
        assert call('/api/session', token=token)[0] == 200
        assert call('/api/works/deer', 'PATCH', {**payload, 'price': -1}, token)[0] == 400
        code, updated = call('/api/works/deer', 'PATCH', payload, token)
        assert code == 200 and updated['soldOut'] and updated['price'] == 432 and updated['version'] == 1
        assert call('/api/works/deer', 'PATCH', payload, token)[0] == 409
        saved = json.loads((temp / 'works.json').read_text(encoding='utf-8'))
        assert next(work for work in saved if work['id'] == 'deer')['description'] == payload['description']
        assert next(work for work in call('/api/works')[1] if work['id'] == 'deer')['soldOut']
        remote = [*module.CATALOG, {'id': 'new-work', 'name': 'Preserve remote addition', 'price': 100}]
        writes = []

        def fake_github(path, token, data=None):
            if data is None:
                return {'sha': 'remote-lease', 'content': base64.b64encode(json.dumps(remote).encode()).decode()}
            assert data['sha'] == 'remote-lease'
            writes.append(json.loads(base64.b64decode(data['content'])))
            return {'commit': {'sha': 'test-commit'}}

        module.github_request = fake_github
        os.environ['GITHUB_TOKEN'] = 'test-only-never-transmitted'
        code, published = call('/api/publish', 'POST', token=token)
        assert code == 200 and published['changed'] and published['commit'] == 'test-commit'
        assert next(work for work in writes[0] if work['id'] == 'deer')['price'] == 432
        assert any(work['id'] == 'new-work' for work in writes[0])
        assert not call('/api/publish', 'POST', token=token)[1]['changed']
        assert call('/api/logout', 'POST', token=token)[0] == 200
        assert call('/api/works/deer', 'PATCH', {**payload, 'version': 1}, token)[0] == 401
        for _ in range(5):
            assert call('/api/login', 'POST', {'password': 'wrong'})[0] == 401
        assert call('/api/login', 'POST', {'password': 'wrong'})[0] == 429
        print('PASS: authentication, CORS, validation, persistence, optimistic lock, publication merge, logout and rate limiting')
    finally:
        server.shutdown()
        server.server_close()
