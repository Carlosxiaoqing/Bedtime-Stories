"""Verify all files after extracting the migration ZIP (standard library only)."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
manifest=ROOT/'PACKAGE-MANIFEST.json'
if not manifest.exists():
    raise SystemExit('Run this check in the extracted ZIP, which contains PACKAGE-MANIFEST.json.')
items=json.loads(manifest.read_text(encoding='utf-8'))
for item in items:
    path=ROOT/item['file']
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
        raise SystemExit('FAILED: '+item['file'])
print(f'Package verified: {len(items)} files.')
