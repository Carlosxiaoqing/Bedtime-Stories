#!/usr/bin/env python3
"""Resolve and verify real character-reference files before image generation."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / '03_素材与参数/用户长稿v4角色图库.json'


def read_registry():
    return json.loads(REGISTRY.read_text(encoding='utf-8'))


def verified_file(item):
    path = (ROOT / item['path']).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ValueError(f'角色图不存在或不在项目中：{item["path"]}')
    if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
        raise ValueError(f'角色图与登记摘要不同：{item["path"]}')
    return str(path)


def resolve(character_ids, outfits=None):
    registry = read_registry()
    cast = {c['id']: c for c in registry['characters'] + registry['supporting_roles']}
    paths, roles = [], []
    outfits = outfits or {}
    if len(set(character_ids)) != len(character_ids):
        raise ValueError('入镜角色ID重复')
    if set(outfits) - set(character_ids):
        raise ValueError('服装角色必须在本镜入镜角色中')
    for cid in character_ids:
        if cid not in cast:
            raise ValueError(f'未知角色：{cid}')
        character = cast[cid]
        ref = character.get('identity_reference', {})
        if ref.get('status') != 'ready_assistant_reviewed' or not ref.get('files'):
            raise ValueError(f'{cid}没有已核对的真实身份图，先建立参考图再出镜')
        identity_paths = [verified_file(item) for item in ref['files']]
        outfit_id = outfits.get(cid)
        outfit = None
        if outfit_id:
            outfit = next((v for v in character.get('wardrobe', {}).get('variants', []) if v['id'] == outfit_id), None)
            if outfit is None:
                raise ValueError(f'{cid}没有服装版本：{outfit_id}')
        extra = [verified_file(item) for item in outfit.get('files', [])] if outfit else []
        for path in identity_paths + extra:
            if path not in paths:
                paths.append(path)
        roles.append({'id': cid, 'name': character.get('name', character.get('label')),
                      'identity_version': ref['version'], 'identity_paths': identity_paths,
                      'identity_anchors': character.get('identity_anchors'), 'outfit': outfit})
    if len(paths) > 5:
        raise ValueError('所需参考图超过当前工具单次5张上限；先制作明确覆盖本镜角色的组合参考，不可静默丢图')
    return {'registry': str(REGISTRY), 'referenced_image_paths': paths, 'characters': roles,
            'instructions': '将referenced_image_paths原样传入图像工具；引用图只作身份或服装依据。只画本镜入镜角色，勿复制参考表里的多个人物或背景。',
            'user_visual_acceptance': registry.get('user_visual_acceptance', 'not_recorded')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--characters', nargs='+', help='本镜实际入镜角色ID')
    parser.add_argument('--outfits', nargs='*', default=[], metavar='ID=OUTFIT', help='服装ID，例如pipi=day_v001')
    parser.add_argument('--validate-all', action='store_true')
    parser.add_argument('--output', type=Path, help='可选，保存本次加载清单')
    args = parser.parse_args()
    if args.validate_all:
        registry = read_registry()
        ready = [c for c in registry['characters'] + registry['supporting_roles']
                 if c.get('identity_reference', {}).get('status') == 'ready_assistant_reviewed']
        for c in ready:
            resolve([c['id']])
            for v in c.get('wardrobe', {}).get('variants', []):
                resolve([c['id']], {c['id']: v['id']})
        result = {'ready_characters': len(ready), 'core_characters': len(registry['characters']),
                  'all_registered_files_match': True, 'user_visual_acceptance': registry.get('user_visual_acceptance', 'not_recorded')}
    elif args.characters:
        result = resolve(args.characters, dict(v.split('=', 1) for v in args.outfits))
    else:
        parser.error('请提供--characters或--validate-all')
    if args.output:
        if args.output.exists():
            raise FileExistsError(args.output)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
