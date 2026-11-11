"""One-time authorized directory migration; preserve pre-edit text evidence."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'docs/production/维护记录/2026-11-12_目录整理'
MOVES = {
    'Outputs/2026-11-11/100集剧本多场景版_v2': '02_100集剧本/阅读与审校/100集剧本多场景版_v2',
    'Outputs/2026-11-11/100集剧本约两分钟_v3': '02_100集剧本/阅读与审校/100集剧本约两分钟_v3',
    'Outputs/2026-11-11/100集剧本逐集核对_v001': '02_100集剧本/阅读与审校/100集剧本逐集核对_v001',
    'Outputs/2026-11-11/新版合集阅读对比_讨论稿_v001': '02_100集剧本/阅读与审校/新版合集阅读对比_讨论稿_v001',
    'Outputs/2026-11-11/用户长稿v4校订与制作规范_v001': '02_100集剧本/阅读与审校/用户长稿v4校订与制作规范_v001',
    'Outputs/2026-11-11/角色图库初始化与转场评估_v001': '03_素材与参数/角色参考图库/v4/初始化与转场评估_v001',
    'Outputs/2026-11-11/ep004-v001': 'episodes/ep004/v001',
    'Outputs/2026-11-10/ep002-v001': 'episodes/ep002/v001',
    'Outputs/2026-11-10/ep003-v001': 'episodes/ep003/v001',
    'Outputs/2026-11-10/ep001_v005_render_211038_16405e': 'episodes/ep001/本地复现/2026-11-10_211038_16405e',
}


def remap(path):
    for old, new in MOVES.items():
        try:
            suffix = path.relative_to(ROOT / old)
            return ROOT / new / suffix
        except ValueError:
            pass
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not args.apply:
        print(json.dumps(MOVES, ensure_ascii=False, indent=2))
        return
    assert not (AUDIT / 'migration.json').exists(), 'Migration already recorded; do not repeat.'
    for old, new in MOVES.items():
        assert (ROOT / old).is_dir(), old
        assert not (ROOT / new).exists(), new
    AUDIT.mkdir(parents=True, exist_ok=True)
    # Capture file inventory and editable paths before moving. Never alter binaries.
    inventory = []
    for old, new in MOVES.items():
        for p in (ROOT / old).rglob('*'):
            if p.is_file():
                inventory.append({'old': str(p.relative_to(ROOT)), 'new': str(remap(p).relative_to(ROOT)),
                                  'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
    text_files = []
    for p in ROOT.rglob('*'):
        rel = p.relative_to(ROOT)
        if p == Path(__file__).resolve():
            continue
        if any(x in rel.parts for x in ('.git', '.venv', '__pycache__', 'downloads', '维护记录')):
            continue
        if str(rel).startswith('episodes/ep001/'):
            continue  # Frozen historical reference and checksum manifest.
        if p.suffix.lower() not in ('.md', '.json', '.html', '.py', '.txt', '.svg') or not p.is_file():
            continue
        if '原件快照' in rel.parts or '原稿快照' in rel.parts or p.name in ('SOURCE_SHA256SUMS.txt', 'SHA256.json'):
            continue
        try:
            text_files.append((p, p.read_text(encoding='utf-8')))
        except UnicodeDecodeError:
            pass
    for old, new in MOVES.items():
        (ROOT / new).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(ROOT / old), ROOT / new)
    # Relative links in moved Markdown/HTML must be resolved against the OLD document.
    def rewrite_link(value, old_file, new_file):
        wrapped = value.startswith('<') and value.endswith('>')
        value = value.strip('<>') if wrapped else value
        if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', value) or value.startswith('#'):
            return ('<' + value + '>') if wrapped else value
        path, sep, fragment = value.partition('#')
        target = (old_file.parent / path).resolve()
        new_target = remap(target)
        if new_target != target or old_file != new_file:
            if new_target.exists():
                value = (str(new_target) if path.startswith('/') else os.path.relpath(new_target, new_file.parent)) + (sep + fragment if sep else '')
        return ('<' + value + '>') if wrapped else value
    edits = []
    with zipfile.ZipFile(AUDIT / '迁移前文本.zip', 'w', zipfile.ZIP_DEFLATED) as backup:
        for old_file, original in text_files:
            new_file = remap(old_file)
            text = original
            if old_file.suffix == '.md':
                text = re.sub(r'(!?\[[^\]\n]*\]\()([^\n)]+)(\))', lambda m: m[1] + rewrite_link(m[2], old_file, new_file) + m[3], text)
            if old_file.suffix == '.html':
                text = re.sub(r'((?:href|src)=[\"\'])([^\"\']+)([\"\'])', lambda m: m[1] + rewrite_link(m[2], old_file, new_file) + m[3], text)
            for old, new in MOVES.items():
                text = text.replace(old, new)
            if text != original:
                backup.writestr(str(old_file.relative_to(ROOT)), original)
                new_file.write_text(text, encoding='utf-8')
                edits.append(str(new_file.relative_to(ROOT)))
    # Date folders contain only per-episode deliverables. Engineering stays in episodes/.
    deliveries = []
    for old, new in MOVES.items():
        if '/ep00' not in old:
            continue
        work = ROOT / new
        media = work / 'output' if (work / 'output').is_dir() else work
        delivery = ROOT / old
        delivery.mkdir(parents=True)
        names = [p for p in media.iterdir() if p.name in ('ep001.mp4', 'ep001_clean.mp4', 'ep002.mp4', 'ep002_clean.mp4', 'ep003.mp4', 'ep003_clean.mp4', 'ep004.mp4', 'ep004_clean.mp4', 'cover.png', '发布文案.md')]
        for source in names:
            shutil.copy2(source, delivery / source.name)
        (delivery / 'README.md').write_text('# 单集交付文件\n\n这里只保存成片、独立封面和三平台发布文案。\n\n完整制作工程与来源：[工程目录](' + os.path.relpath(work, delivery) + '/README.md)。\n', encoding='utf-8')
        # Some historical engineering folders used output/README.md only.
        if not (work / 'README.md').exists():
            (work / 'README.md').write_text('# 单集制作工程\n\n交付文件见[日期目录](' + os.path.relpath(delivery, work) + '/README.md)。\n\n音轨、原图、参数与来源记录保存在本工程。\n')
        deliveries.append({'directory': old, 'engineering': new, 'files': sorted(p.name for p in delivery.iterdir())})
    for p in (ROOT / 'Outputs').rglob('.DS_Store'):
        p.unlink()
    # Content validation: migrated binaries and all untouched text retain exact bytes.
    changed = set(edits)
    for item in inventory:
        p = ROOT / item['new']
        assert p.exists(), item['new']
        if item['new'] not in changed:
            assert hashlib.sha256(p.read_bytes()).hexdigest() == item['sha256'], item['new']
    result = {'date': '2026-11-12', 'moves': MOVES, 'inventory': inventory,
              'updated_text_files': edits, 'deliveries': deliveries,
              'untouched_content_hash_check': 'passed', 'scope': 'directory arrangement only; no video, narration or artwork regeneration'}
    (AUDIT / 'migration.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'moved_directories': len(MOVES), 'migrated_files': len(inventory), 'updated_text_files': len(edits), 'deliveries': deliveries, 'content_check': 'passed'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
