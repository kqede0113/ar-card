"""Set the local admin password without saving plaintext."""
import getpass
import hashlib
from pathlib import Path
import secrets

password = getpass.getpass('Admin password: ')
if not password or password != getpass.getpass('Confirm password: '):
    raise SystemExit('Passwords do not match.')
salt = secrets.token_bytes(16)
value = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, maxmem=64 * 1024 * 1024).hex()
path = Path(__file__).resolve().parent / '.env.local'
path.write_text('ADMIN_PASSWORD_HASH=scrypt$' + salt.hex() + '$' + value + '\n', encoding='utf-8')
path.chmod(0o600)
print('Local password configured. Restart the management app.')
