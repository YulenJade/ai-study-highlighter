import base64
from io import BytesIO
import json
import os
from concurrent.futures import ThreadPoolExecutor
import zipfile

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.extraction import extract
from app.library import Library, users
from app.main import app
from app.security import password_hash


class MemoryStorage:
    def __init__(self):
        self.objects = {}
        self.fail_put = self.fail_delete = False

    def put_object(self, Bucket, Key, Body, **kwargs):
        self.objects[Key] = Body
        if self.fail_put:
            raise OSError('ambiguous write')

    def get_object(self, Bucket, Key):
        return {'Body': BytesIO(self.objects[Key])}

    def delete_object(self, Bucket, Key):
        if self.fail_delete:
            raise OSError('delete failed')
        self.objects.pop(Key, None)


def auth(user='alice', password='a' * 32):
    encoded = base64.b64encode(f'{user}:{password}'.encode()).decode()
    return {'Authorization': 'Basic ' + encoded, 'X-Library-Request': '1'}


@pytest.fixture
def library(tmp_path, monkeypatch):
    monkeypatch.setenv('LIBRARY_USERS', json.dumps({'alice': password_hash('a' * 32), 'bob': password_hash('b' * 32)}))
    url = os.getenv('TEST_DATABASE_URL', 'sqlite:///' + str(tmp_path / 'metadata.db'))
    storage = MemoryStorage()
    if os.getenv('TEST_S3_ENDPOINT'):
        import boto3
        storage = boto3.client('s3', endpoint_url=os.environ['TEST_S3_ENDPOINT'],
                               aws_access_key_id='minioadmin', aws_secret_access_key='minioadmin',
                               region_name='us-east-1')
        from botocore.exceptions import ClientError
        try:
            storage.create_bucket(Bucket='private')
        except ClientError as exc:
            if exc.response['Error']['Code'] not in {'BucketAlreadyOwnedByYou', 'BucketAlreadyExists'}:
                raise
    lib = Library(url, storage, 'private')
    if os.getenv('TEST_DATABASE_URL'):
        from app.library import metadata
        metadata.drop_all(lib.engine)
    lib.initialize(['alice', 'bob'])
    app.state.library = lib
    yield lib
    app.state.library = None
    lib.engine.dispose()


def test_private_lifecycle_and_restart(library):
    client = TestClient(app)
    assert client.get('/books').status_code == 401
    assert client.get('/books', headers=auth(password='wrong')).status_code == 401
    result = client.post('/books', headers=auth(), files={'file': ('book.md', '# Biology\nphotosynthesis')})
    assert result.status_code == 201, result.text
    book = result.json()['id']
    assert client.get('/books', headers=auth()).json()['used_bytes'] > 0
    assert client.get('/books', headers=auth('bob', 'b' * 32)).json()['books'] == []
    for suffix in ['text', 'original']:
        assert client.get(f'/books/{book}/{suffix}', headers=auth('bob', 'b' * 32)).status_code == 404
    assert client.delete(f'/books/{book}', headers=auth('bob', 'b' * 32)).status_code == 404
    assert client.post(f'/books/{book}/preview', headers=auth('bob', 'b' * 32), data={'notes': 'test'}).status_code == 404
    # New application-side library instance, same external metadata and objects.
    restarted = Library(library.engine.url.render_as_string(hide_password=False), library.storage, 'private')
    app.state.library = restarted
    assert client.get(f'/books/{book}/text', headers=auth()).json()['sections'][0]['text'].startswith('# Biology')
    assert client.get(f'/books/{book}/original', headers=auth()).content.startswith(b'# Biology')
    assert client.post(f'/books/{book}/highlight', headers=auth(), data={'notes': 'Biology'}).status_code == 400
    assert client.delete(f'/books/{book}', headers=auth()).status_code == 204
    assert client.get('/books', headers=auth()).json()['used_bytes'] == 0
    if isinstance(library.storage, MemoryStorage):
        assert not library.storage.objects
    restarted.engine.dispose()


def test_csrf_and_security_headers(library):
    client = TestClient(app)
    assert client.post('/extract', headers={'Authorization': auth()['Authorization']}, files={'file': ('a.txt', 'text')}).status_code == 403
    response = client.get('/', headers=auth())
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'


def test_quota_is_atomic_and_failure_recovery(library):
    # Failure injection uses the same metadata backend but deterministic storage.
    library.storage = MemoryStorage()
    library.quota = 6
    def save():
        try:
            return library.save('alice', 'a.txt', 'txt', b'1234')['id']
        except HTTPException as exc:
            return exc.status_code
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: save(), range(2)))
    assert results.count(413) == 1
    book = next(x for x in results if isinstance(x, str))
    library.storage.fail_delete = True
    with pytest.raises(HTTPException):
        library.remove('alice', book)
    assert library.listing('alice')['used_bytes'] == 4
    library.storage.fail_delete = False
    library.remove('alice', book)
    library.storage.fail_put = True
    with pytest.raises(HTTPException):
        library.save('alice', 'b.txt', 'txt', b'1234')
    listing = library.listing('alice')
    assert listing['used_bytes'] == 4 and listing['books'][0]['state'] == 'pending'
    pending = listing['books'][0]['id']
    with pytest.raises(HTTPException) as error:
        library.read('alice', pending)
    assert error.value.status_code == 409
    library.remove('alice', pending)
    assert library.listing('alice')['used_bytes'] == 0
    assert not library.storage.objects


def office(extension, payload=None):
    stream = BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', '<Types/>')
        path = 'word/document.xml' if extension == 'docx' else 'ppt/slides/slide1.xml'
        archive.writestr(path, payload or '<w:document xmlns:w="urn:test"><w:p><w:r><w:t>教材 study</w:t></w:r></w:p></w:document>')
    return stream.getvalue()


@pytest.mark.parametrize('extension', ['pdf', 'docx', 'pptx', 'txt', 'md'])
def test_five_formats(extension):
    from test_main import make_pdf
    data = make_pdf() if extension == 'pdf' else office(extension) if extension in {'docx', 'pptx'} else '教材 study'.encode()
    response = TestClient(app).post('/extract', files={'file': ('book.' + extension, data)})
    assert response.status_code == 200, response.text
    assert response.json()['characters'] > 0


@pytest.mark.parametrize('name,data', [('bad.docx', b'not a zip'), ('bad.pdf', b'not a pdf'), ('bad.txt', b'\xff\x00'), ('bad.exe', b'abc'), ('empty.md', b'')])
def test_invalid_formats(name, data):
    assert TestClient(app).post('/extract', files={'file': (name, data)}).status_code in {400, 422}


def test_office_bombs_entities_traversal_and_empty():
    with pytest.raises(Exception):
        extract(office('docx', '<!DOCTYPE x [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><x>&xxe;</x>'), 'docx')
    data = BytesIO(office('docx'))
    with zipfile.ZipFile(data, 'a') as archive:
        archive.writestr('../escape', 'x')
    with pytest.raises(ValueError):
        extract(data.getvalue(), 'docx')
    from app import extraction
    original = extraction.MAX_EXPANDED
    extraction.MAX_EXPANDED = 2
    try:
        with pytest.raises(ValueError):
            extract(office('docx'), 'docx')
    finally:
        extraction.MAX_EXPANDED = original
    with pytest.raises(ValueError):
        extract(b'   ', 'txt')


def test_body_limit_before_multipart(monkeypatch):
    from app import main
    monkeypatch.setattr(main, 'MAX_BYTES', 10)
    response = TestClient(app).post('/extract', content=b'x', headers={'content-length': str(2 * 1024 * 1024)})
    assert response.status_code == 413
    assert TestClient(app).post('/extract', files={'file': ('b.txt', b'x' * 11)}).status_code == 413


def test_hosted_startup_fails_closed(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.delenv('LIBRARY_USERS', raising=False)
    monkeypatch.delenv('DATABASE_URL', raising=False)
    with pytest.raises(RuntimeError):
        with TestClient(app):
            pass


def test_parser_timeout_and_capacity(monkeypatch):
    from app import processing
    import subprocess
    monkeypatch.setattr(processing.subprocess, 'run', lambda *a, **k: (_ for _ in ()).throw(subprocess.TimeoutExpired('worker', 45)))
    with pytest.raises(HTTPException) as error:
        processing.process(b'hello', 'txt')
    assert error.value.status_code == 422
    assert processing.SLOTS.acquire(blocking=False)
    try:
        with pytest.raises(HTTPException) as error:
            processing.process(b'hello', 'txt')
        assert error.value.status_code == 429
    finally:
        processing.SLOTS.release()


def test_saved_pdf_uses_original_highlight_engine(library):
    from test_main import make_pdf
    client = TestClient(app)
    response = client.post('/books', headers=auth(), files={'file': ('book.pdf', make_pdf())})
    assert response.status_code == 201
    book = response.json()['id']
    response = client.post(f'/books/{book}/preview', headers=auth(), data={'notes': '[定义] photosynthesis'})
    assert response.status_code == 200 and response.json()['match_count'] == 1
    response = client.post(f'/books/{book}/highlight', headers=auth(), data={'notes': '[定义] photosynthesis'})
    assert response.status_code == 200 and response.content.startswith(b'%PDF-')
    if os.getenv('TEST_S3_ENDPOINT'):
        import httpx
        row = library.get('alice', book)
        response = httpx.get(os.environ['TEST_S3_ENDPOINT'] + '/private/' + library.key(row))
        assert response.status_code == 403
    library.remove('alice', book)


def test_book_above_old_15mb_limit(library):
    data = BytesIO(office('docx'))
    with zipfile.ZipFile(data, 'a', zipfile.ZIP_STORED) as archive:
        archive.writestr('word/media/image.bin', b'0' * (16 * 1024 * 1024))
    response = TestClient(app).post('/books', headers=auth(), files={'file': ('large.docx', data.getvalue())})
    assert response.status_code == 201, response.text
    assert response.json()['size'] > 15 * 1024 * 1024
    library.remove('alice', response.json()['id'])


def test_count_quota_and_integrity(library):
    library.storage = MemoryStorage()
    library.book_limit = 1
    book = library.save('alice', 'a.txt', 'txt', b'hello')
    with pytest.raises(HTTPException) as error:
        library.save('alice', 'b.txt', 'txt', b'world')
    assert error.value.status_code == 413
    library.storage.objects[library.key(book)] = b'wrong'
    with pytest.raises(HTTPException) as error:
        library.read('alice', book['id'])
    assert error.value.status_code == 503
    library.remove('alice', book['id'])


def test_postgres_only_and_tls_endpoint(monkeypatch):
    from app.library import configured_library
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///local.db')
    monkeypatch.setenv('S3_BUCKET', 'private')
    with pytest.raises(ValueError, match='PostgreSQL'):
        configured_library()
    monkeypatch.setenv('DATABASE_URL', 'postgresql://u:p@example.test/db')
    monkeypatch.setenv('S3_ENDPOINT_URL', 'http://example.test')
    with pytest.raises(ValueError, match='HTTPS'):
        configured_library()


def test_encrypted_pdf_and_text_limits():
    import fitz
    document = fitz.open()
    document.new_page().insert_text((72, 72), 'secret')
    data = document.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw='owner', user_pw='user')
    document.close()
    response = TestClient(app).post('/extract', files={'file': ('secret.pdf', data)})
    assert response.status_code == 422
    with pytest.raises(ValueError):
        extract(b'x' * 2_000_001, 'txt')
