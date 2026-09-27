#!/usr/bin/env python3
"""Resolve bundled case evidence; validate bytes, not artistic quality. Read-only."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys


def resolve_inside(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes skill directory: {relative}")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--list', action='store_true')
    group.add_argument('--case', dest='case_id')
    group.add_argument('--verify', action='store_true')
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    inventory = json.loads((root / 'references/cases/inventory.json').read_text(encoding='utf-8'))
    cases = inventory['cases']
    if args.list:
        print(json.dumps([{'id': c['id'], 'title': c['title'], 'status': c['status']}
                          for c in cases], ensure_ascii=False, indent=2))
        return 0
    selected = cases if args.verify else [c for c in cases if c['id'] == args.case_id]
    if not selected:
        parser.error(f"Unknown case: {args.case_id}")
    records, errors = [], []
    for case in selected:
        for asset in case['files']:
            try:
                path = resolve_inside(root, asset['path'])
                data = path.read_bytes()
                if hashlib.sha256(data).hexdigest() != asset['sha256']:
                    raise ValueError('SHA-256 mismatch')
                if len(data) != asset['bytes']:
                    raise ValueError('Byte count mismatch')
                if path.suffix.lower() == '.png':
                    if data[:8] != b'\x89PNG\r\n\x1a\n' or data[12:16] != b'IHDR':
                        raise ValueError('Invalid PNG signature/header')
                    if list(struct.unpack('>II', data[16:24])) != asset['dimensions']:
                        raise ValueError('PNG dimensions mismatch')
                records.append({'case': case['id'], 'role': asset['role'],
                                'absolute_path': str(path), 'verified': True})
            except (OSError, ValueError, KeyError, struct.error) as exc:
                errors.append({'case': case['id'], 'path': asset.get('path'), 'error': str(exc)})
    print(json.dumps({'scope': 'Integrity and paths only; NOT visual acceptance',
                      'files': records, 'errors': errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as exc:
        print(f'Casebook error: {exc}', file=sys.stderr)
        sys.exit(1)
