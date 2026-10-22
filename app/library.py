"""Durable metadata + private S3 objects; quota reservations precede every write."""
from datetime import datetime, timezone
import hashlib
import os
import uuid

import boto3
from botocore.config import Config
from fastapi import HTTPException
from sqlalchemy import (BigInteger, Column, Integer, MetaData, String, Table,
                        create_engine, delete, insert, select, update)

metadata = MetaData()
users = Table('library_users', metadata, Column('id', String(64), primary_key=True),
              Column('used', BigInteger, nullable=False, default=0),
              Column('count', Integer, nullable=False, default=0))
books = Table('library_books', metadata, Column('id', String(32), primary_key=True),
              Column('owner', String(64), nullable=False, index=True),
              Column('name', String(255), nullable=False), Column('extension', String(8)),
              Column('size', BigInteger, nullable=False), Column('sha256', String(64)),
              Column('state', String(16)), Column('created', String(40)))


class Library:
    def __init__(self, url, storage, bucket):
        self.engine = create_engine(url, pool_pre_ping=True)
        self.storage, self.bucket = storage, bucket
        self.quota = int(os.getenv('USER_QUOTA_MB', '1024')) * 1024 * 1024
        self.book_limit = int(os.getenv('USER_BOOK_LIMIT', '100'))

    def initialize(self, account_names):
        # Schema v1: additive only. Future changes require explicit migrations.
        metadata.create_all(self.engine)
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        statement = pg_insert if self.engine.dialect.name == 'postgresql' else sqlite_insert
        with self.engine.begin() as connection:
            for name in account_names:
                connection.execute(statement(users).values(id=name, used=0, count=0).on_conflict_do_nothing())

    def listing(self, owner):
        with self.engine.connect() as c:
            account = c.execute(select(users).where(users.c.id == owner)).mappings().one()
            rows = c.execute(select(books).where(books.c.owner == owner).order_by(books.c.created.desc())).mappings()
            return {'books': [dict(row) for row in rows], 'used_bytes': account['used'],
                    'quota_bytes': self.quota, 'book_limit': self.book_limit}

    def get(self, owner, book_id):
        with self.engine.connect() as c:
            row = c.execute(select(books).where(books.c.id == book_id, books.c.owner == owner)).mappings().first()
            if not row:
                raise HTTPException(404, 'Book not found')
            return dict(row)

    @staticmethod
    def key(row):
        # Only server-generated identifiers; never a supplied filename.
        return f"books/{row['owner']}/{row['id']}/original"

    def save(self, owner, name, extension, data):
        row = dict(id=uuid.uuid4().hex, owner=owner, name=name[:255], extension=extension,
                   size=len(data), sha256=hashlib.sha256(data).hexdigest(), state='pending',
                   created=datetime.now(timezone.utc).isoformat())
        with self.engine.begin() as c:
            # Atomic conditional UPDATE locks the account across concurrent uploads.
            reserved = c.execute(update(users).where(
                users.c.id == owner, users.c.used + len(data) <= self.quota,
                users.c.count < self.book_limit).values(used=users.c.used + len(data), count=users.c.count + 1))
            if reserved.rowcount != 1:
                raise HTTPException(413, 'Private library quota exceeded')
            c.execute(insert(books).values(**row))
        try:
            with self.engine.begin() as c:
                c.execute(update(users).where(users.c.id == owner).values(used=users.c.used))
                if not c.execute(select(books.c.id).where(books.c.id == row['id'])).first():
                    raise ValueError('Upload cancelled by deletion')
                self.storage.put_object(Bucket=self.bucket, Key=self.key(row), Body=data,
                                        ContentType='application/octet-stream')
                c.execute(update(books).where(books.c.id == row['id']).values(state='ready'))
            row['state'] = 'ready'
            return row
        except Exception as exc:
            # An ambiguous object write remains reserved and deletable. Never free
            # quota while a possibly successful remote write may still exist.
            raise HTTPException(503, 'Storage unavailable; refresh library and delete pending entry before retry') from exc

    def read(self, owner, book_id):
        row = self.get(owner, book_id)
        if row['state'] != 'ready':
            raise HTTPException(409, 'Book not ready; delete pending entry and upload again')
        try:
            body = self.storage.get_object(Bucket=self.bucket, Key=self.key(row))['Body']
            try:
                data = body.read(row['size'] + 1)
            finally:
                body.close()
            if len(data) != row['size'] or hashlib.sha256(data).hexdigest() != row['sha256']:
                raise ValueError('Object integrity mismatch')
            return row, data
        except Exception as exc:
            raise HTTPException(503, 'Stored book temporarily unavailable') from exc

    def remove(self, owner, book_id):
        row = self.get(owner, book_id)
        try:
            # Serialize deletion against quota mutations, including retry requests.
            with self.engine.begin() as c:
                c.execute(update(users).where(users.c.id == owner).values(used=users.c.used))
                current = c.execute(select(books).where(books.c.id == book_id, books.c.owner == owner)).first()
                if not current:
                    return
                self.storage.delete_object(Bucket=self.bucket, Key=self.key(row))
                c.execute(delete(books).where(books.c.id == book_id, books.c.owner == owner))
                c.execute(update(users).where(users.c.id == owner).values(
                    used=users.c.used - row['size'], count=users.c.count - 1))
        except Exception as exc:
            raise HTTPException(503, 'Delete failed; quota retained; retry later') from exc


def configured_library():
    url = os.getenv('DATABASE_URL', '')
    if not url or not os.getenv('S3_BUCKET'):
        return None
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql+psycopg://', 1)
    elif url.startswith('postgresql://'):
        url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
    if not url.startswith('postgresql+psycopg://'):
        raise ValueError('Persistent library requires PostgreSQL')
    endpoint = os.getenv('S3_ENDPOINT_URL') or None
    if endpoint and not endpoint.startswith('https://'):
        raise ValueError('S3 endpoint must use HTTPS')
    storage = boto3.client('s3', endpoint_url=endpoint,
                           region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
                           config=Config(connect_timeout=5, read_timeout=20,
                                         retries={'max_attempts': 2}))
    return Library(url, storage, os.environ['S3_BUCKET'])
