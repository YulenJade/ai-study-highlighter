import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

from fastapi import HTTPException

SLOTS = threading.BoundedSemaphore(1)


def process(data: bytes, extension: str, action='extract', notes=''):
    if not SLOTS.acquire(blocking=False):
        raise HTTPException(429, 'Parser busy; retry later')
    try:
        with tempfile.TemporaryDirectory(prefix='study-') as directory:
            root = Path(directory)
            (root / 'input').write_bytes(data)
            (root / 'notes').write_text(notes)
            # A fresh interpreter without DB, account or object-storage secrets.
            env = {k: v for k, v in os.environ.items() if k in {'PATH', 'SYSTEMROOT', 'LANG'}}
            env['PYTHONPATH'] = str(Path(__file__).resolve().parent.parent)
            try:
                result = subprocess.run(
                    [sys.executable, '-m', 'app.worker', str(root / 'input'), extension,
                     action, str(root / 'notes'), str(root / 'result')],
                    cwd=directory, env=env, timeout=45, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, check=False)
            except subprocess.TimeoutExpired as exc:
                raise HTTPException(422, 'Processing time limit exceeded') from exc
            if result.returncode != 0 or not (root / 'result').exists():
                raise HTTPException(422, 'Invalid, unsupported or over-limit document')
            summary = json.loads((root / 'result').read_text())
            output = (root / 'result.pdf').read_bytes() if action == 'highlight' else None
            return summary, output
    finally:
        SLOTS.release()
