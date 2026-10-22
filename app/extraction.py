"""Bounded extraction; never execute Office code or follow external relationships."""
from io import BytesIO
from pathlib import PurePosixPath
import re
import zipfile

import fitz
from defusedxml import ElementTree

MAX_PAGES = 2000
MAX_CHARS = 2_000_000
MAX_EXPANDED = 128 * 1024 * 1024


def extract(data: bytes, extension: str) -> dict:
    sections = []
    count = 0

    def add(text):
        nonlocal count
        count += len(text)
        if count > MAX_CHARS or len(sections) >= MAX_PAGES:
            raise ValueError('Extracted text or page limit exceeded')
        sections.append({'page': len(sections) + 1, 'text': text})

    if extension == 'pdf':
        if not data.startswith(b'%PDF-'):
            raise ValueError('Not a PDF file')
        with fitz.open(stream=data, filetype='pdf') as doc:
            if doc.needs_pass or doc.page_count > MAX_PAGES:
                raise ValueError('Encrypted PDF or page limit exceeded')
            for page in doc:
                add(page.get_text())
    elif extension in {'txt', 'md'}:
        text = data.decode('utf-8-sig')
        if '\x00' in text:
            raise ValueError('Binary text file')
        add(text)
    elif extension in {'docx', 'pptx'}:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            infos = archive.infolist()
            if len(infos) > 5000 or sum(i.file_size for i in infos) > MAX_EXPANDED:
                raise ValueError('Office archive exceeds expansion limit')
            names = [i.filename for i in infos]
            if len(names) != len(set(names)):
                raise ValueError('Duplicate archive entries')
            for info in infos:
                path = PurePosixPath(info.filename)
                if path.is_absolute() or '..' in path.parts or info.flag_bits & 1:
                    raise ValueError('Unsafe archive')
                if info.file_size > 16 * 1024 * 1024:
                    raise ValueError('Office part too large')
            if '[Content_Types].xml' not in names:
                raise ValueError('Not an Office document')
            if extension == 'docx':
                parts = ['word/document.xml']
            else:
                parts = sorted((n for n in names if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)),
                               key=lambda n: int(re.search(r'slide(\d+)', n).group(1)))
            if not parts or len(parts) > MAX_PAGES:
                raise ValueError('Missing document parts or slide limit exceeded')
            for part in parts:
                root = ElementTree.fromstring(archive.read(part))
                paragraphs = []
                for node in root.iter():
                    if node.tag.endswith('}p'):
                        paragraphs.append(''.join(n.text or '' for n in node.iter() if n.tag.endswith('}t')))
                add('\n'.join(paragraphs))
    else:
        raise ValueError('Unsupported file format')
    if not any(s['text'].strip() for s in sections):
        raise ValueError('No extractable text; scanned PDFs need OCR (not supported)')
    return {'sections': sections, 'page_count': len(sections), 'characters': count}
