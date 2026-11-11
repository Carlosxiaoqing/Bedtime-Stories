#!/usr/bin/env python3
"""Validate a video-free checkout without TTS, image generation or rendering."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys

from PIL import Image, ImageFont

ROOT = Path(__file__).resolve().parents[1]
VIDEO = {'.mp4', '.mov', '.mkv', '.webm', '.avi', '.m4v', '.gif'}


def inspect():
    state = json.loads((ROOT/'PROJECT_STATE.json').read_text())
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError('当前验证的依赖为Python 3.12，请在环境里选择3.12。')
    for line in (ROOT/'local/requirements-lock.txt').read_text().splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        name, version = line.split('==')
        assert importlib.metadata.version(name) == version, f'依赖版本不同：{name}'
    for name in ('ffmpeg', 'ffprobe'):
        assert shutil.which(name), f'缺少{name}'
    for option, needed in (('-filters', (' ass ', ' xfade ')), ('-encoders', ('libx264', ' aac '))):
        result = subprocess.run(['ffmpeg', '-hide_banner', option], check=True, capture_output=True, text=True)
        text = result.stdout + result.stderr
        assert all(n in text for n in needed), option
    for name in ('NotoSansCJKsc-Regular.otf', 'NotoSansCJKsc-Bold.otf', 'NotoSans-Regular.ttf'):
        ImageFont.truetype(str(ROOT/'local/fonts'/name), 48)
    from export_long_scripts import load_episodes
    episodes = load_episodes()
    from character_references import read_registry, resolve
    registry = read_registry()
    all_cast = registry['characters'] + registry['supporting_roles']
    cast = [c for c in all_cast if c.get('identity_reference', {}).get('status') == 'ready_assistant_reviewed']
    references = set()
    for c in cast:
        references.update(resolve([c['id']])['referenced_image_paths'])
        for outfit in c.get('wardrobe', {}).get('variants', []):
            references.update(resolve([c['id']], {c['id']: outfit['id']})['referenced_image_paths'])
    for path in references:
        with Image.open(path) as im:
            im.verify()
    registered = set()
    def verify_registered(value):
        if isinstance(value, dict):
            if 'path' in value and 'sha256' in value:
                path = (ROOT/value['path']).resolve()
                assert path.is_relative_to(ROOT) and path.is_file(), value['path']
                assert hashlib.sha256(path.read_bytes()).hexdigest() == value['sha256'], value['path']
                registered.add(str(path))
            for child in value.values():
                verify_registered(child)
        elif isinstance(value, list):
            for child in value:
                verify_registered(child)
    verify_registered(registry)
    work = ROOT/'episodes/ep004/v001'
    plan = json.loads((work/'storyboard.json').read_text())
    hashes = []
    for shot in plan['shots']:
        p = work/shot['image']
        with Image.open(p) as im:
            im.verify()
        hashes.append(hashlib.sha256(p.read_bytes()).hexdigest())
    assert len(hashes) == len(set(hashes)) == 35
    for name in ('audio/voice.wav', 'mix.wav', 'episode.ass', 'subtitles.ruby.json', '用户验收记录.json'):
        assert (work/name).is_file(), name
    assert json.loads((work/'用户验收记录.json').read_text())['status'] == 'accepted'
    return {'offline_preflight': 'passed', 'script_count': len(episodes),
            'adopted_version': state['adopted_script_version'],
            'latest_accepted': state['latest_accepted_episode']['id']+'-'+state['latest_accepted_episode']['version'],
            'next_candidate': state['next_candidate']['id'],
            'next_candidate_authorized': state['next_candidate']['authorized'],
            'reference_material_episode': 'ep004-v001',
            'cast_identities': len(cast), 'verified_identity_and_wardrobe_files': len(references),
            'verified_registered_reference_files': len(registered),
            'planned_roles_without_images': [c['id'] for c in all_cast if c not in cast],
            'ep004_unique_plot_images': len(hashes), 'video_required_for_preflight': False,
            'tts_network': 'not_tested_no_text_sent', 'image_generation_tool': 'must_check_in_target_chat',
            'cloud_runtime_execution': 'not_certified_by_local_preflight'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-no-videos', action='store_true', help='另核对Git当前索引不包含视频或压缩包')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = inspect()
    if args.require_no_videos:
        paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
        blocked = [p for p in paths if Path(p).suffix.lower() in VIDEO | {'.zip', '.7z', '.rar', '.tar', '.tgz', '.gz'}]
        assert not blocked, f'索引仍含视频/归档：{blocked}'
        result['git_index_excludes_videos_and_archives'] = True
    rendered = json.dumps(result, ensure_ascii=False, indent=2)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end='')


if __name__ == '__main__':
    main()
