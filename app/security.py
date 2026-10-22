"""Provisioned accounts: high-entropy passwords, scrypt hashes, no public signup."""
import base64
import hashlib
import json
import os
import re
import secrets


def password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return salt.hex() + ':' + digest.hex()


def accounts() -> dict:
    users = json.loads(os.getenv('LIBRARY_USERS', '{}'))
    if not isinstance(users, dict):
        raise ValueError('LIBRARY_USERS must be an object')
    for user, value in users.items():
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', user):
            raise ValueError('Invalid account name')
        salt, digest = value.split(':')
        if len(bytes.fromhex(salt)) != 16 or len(bytes.fromhex(digest)) != 64:
            raise ValueError('Invalid password hash')
    return users


def authenticate(header: str) -> str | None:
    users = accounts()
    try:
        scheme, encoded = header.split(' ', 1)
        if scheme.lower() != 'basic':
            return None
        user, password = base64.b64decode(encoded, validate=True).decode().split(':', 1)
        if len(password) > 512:
            return None
        stored = users.get(user, '00' * 16 + ':' + '00' * 64)
        salt, _ = stored.split(':')
        valid = secrets.compare_digest(password_hash(password, bytes.fromhex(salt)), stored)
        return user if valid and user in users else None
    except (ValueError, UnicodeError):
        return None


if __name__ == '__main__':
    import getpass
    print(password_hash(getpass.getpass('Account password (use 32+ random characters): ')))
