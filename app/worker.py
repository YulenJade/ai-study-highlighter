"""Disposable parser process. Input/output only; no application credentials."""
import json
from pathlib import Path
import sys


def main():
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (35, 35))
    resource.setrlimit(resource.RLIMIT_FSIZE, (256 * 1024 * 1024,) * 2)
    if sys.platform == 'linux':
        resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024,) * 2)
    from .extraction import extract
    from .highlighter import analyze_pdf
    source, extension, action, notes, output = sys.argv[1:]
    try:
        data = Path(source).read_bytes()
        if action == 'extract':
            result = extract(data, extension)
        else:
            result, annotated = analyze_pdf(data, Path(notes).read_text(), action == 'highlight')
            if annotated is not None:
                Path(output + '.pdf').write_bytes(annotated)
        Path(output).write_text(json.dumps(result))
    except Exception:
        Path(output).write_text(json.dumps({'error': 'Invalid, unsupported or over-limit document'}))
        sys.exit(2)


if __name__ == '__main__':
    main()
