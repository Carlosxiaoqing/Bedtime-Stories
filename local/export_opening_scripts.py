#!/usr/bin/env python3
"""Validate and export the v5 scripts with episode-specific spoken openings."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / '02_100集剧本/用户长稿v5/结构化JSON'


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def load_episodes():
    paths = sorted(LIBRARY.glob('ep*.json'))
    if [p.stem for p in paths] != [f'ep{n:03}' for n in range(1, 101)]:
        raise ValueError('v5须有001–100完整JSON')
    episodes = []
    for n, path in enumerate(paths, 1):
        e = json.loads(path.read_text(encoding='utf-8'))
        if (e['id'], e['episode'], e['script_version']) != (path.stem, n, 'v5'):
            raise ValueError(f'集号或版本不一致：{path}')
        paragraphs = e['narration_paragraphs']
        expected_ids = ['p000'] + [f'p{i:03}' for i in range(1, len(paragraphs))]
        if [p['id'] for p in paragraphs] != expected_ids:
            raise ValueError(f'段落编号不完整：{path}')
        opening = paragraphs[0]
        if opening.get('kind') != 'opening_introduction' or opening.get('illustration_requirement') != 'standalone':
            raise ValueError(f'片头缺少独立配图标记：{path}')
        if f'《{e["title"]}》' not in opening['text']:
            raise ValueError(f'片头未提及本集标题：{path}')
        text = '\n\n'.join(p['text'] for p in paragraphs)
        if any(not p['text'].strip() for p in paragraphs):
            raise ValueError(f'存在空段：{path}')
        if digest(text) != e['narration_sha256']:
            raise ValueError(f'口播摘要不一致：{path}')
        if len(re.findall(r'[\u3400-\u9fff]', text)) != e['cn_characters']:
            raise ValueError(f'汉字数不一致：{path}')
        if re.search(r'[A-Za-zぁ-ゖァ-ヺ]', text):
            raise ValueError(f'仍有混入语言：{path}')
        if re.search(r'[零一二三四五六七八九十百\d]+岁', text):
            raise ValueError(f'出现具体年龄：{path}')
        if e['duration_policy']['limit_s'] is not None:
            raise ValueError(f'不得设置固定片长上限：{path}')
        if e['actual_duration_s'] is not None:
            raise ValueError(f'新口播版不能沿用旧版时长：{path}')
        body = '\n\n'.join(p['text'] for p in paragraphs[1:])
        if digest(body) != e.get('v5_body_sha256'):
            raise ValueError(f'正文摘要不一致：{path}')
        episodes.append(e)
    return episodes


def export(output):
    output = output.resolve()
    if output.is_relative_to(ROOT / 'Outputs'):
        raise ValueError('全集剧本属于共用资料，请导出到02_100集剧本/阅读与审校/，不要放入Outputs。')
    episodes = load_episodes()
    output.mkdir(parents=True, exist_ok=True)
    single = output / '单集Markdown'
    single.mkdir(exist_ok=True)
    book_path = output / '100集睡前故事合集_用户长稿v5.md'
    opening_path = output / '100集片头文案.md'
    if book_path.exists() or opening_path.exists() or any(single.iterdir()):
        raise FileExistsError('阅读导出已存在，请使用新的独立任务目录')
    book = [
        '# 100集睡前故事合集｜用户长稿 v5（新增逐集开场）', '',
        '2026-11-12。由用户长稿v5 JSON导出，JSON为唯一改稿源。', '',
        '每集新增专属口播开场并保留原正文；开场必须有独立剧情插画，不得复用第一张故事图。001–003仍为原短稿参考，004–100沿用用户长稿正文。', '',
        '配音使用晓晓rate=-35%／pitch=-2Hz／volume=+0%；完整读完，不设五分钟上限。标题、主题、制作说明不入口播，不增加具体年龄说明。', '',
        '阅读稿不能作为媒体完成记录；配音、分镜、片头插画及视频状态以对应制作版本记录为准。', '',
        '## 目录', '',
    ]
    for e in episodes:
        book.append(f"- [{e['episode']:03}《{e['title']}》](#ep{e['episode']:03})")
    evidence = []
    for e in episodes:
        body = '\n\n'.join(p['text'] for p in e['narration_paragraphs'])
        heading = f"## 第{e['episode']:03}集：{e['title']}"
        book += ['', '---', '', f"<a id=\"ep{e['episode']:03}\"></a>", '', heading, '', f"主题：{e['theme']}", '', body]
        path = single / f"第{e['episode']:03}集_{e['title']}.md"
        path.write_text(f"# 第{e['episode']:03}集：{e['title']}\n\n主题：{e['theme']}\n\n{body}\n", encoding='utf-8')
        rendered = path.read_text(encoding='utf-8').split('\n\n', 2)[2].rstrip('\n')
        if rendered != body:
            raise ValueError(f'Markdown口播与JSON不同：{path}')
        evidence.append({'episode': e['id'], 'paragraph_count': len(e['narration_paragraphs']),
                         'cn_characters': e['cn_characters'], 'narration_sha256': digest(body),
                         'json_markdown_equal': True,
                         'standalone_opening_illustration_required': True})
    book_path.write_text('\n'.join(book) + '\n', encoding='utf-8')
    opening_catalog = ['# 100集片头文案｜用户长稿v5', '',
                       '所有片头均需单独规划镜头并制作专属插画，不复用封面或第一张剧情图。', '']
    for e in episodes:
        opening_catalog += [f"## 第{e['episode']:03}集：{e['title']}", '',
                            e['narration_paragraphs'][0]['text'], '']
    opening_path.write_text('\n'.join(opening_catalog).rstrip() + '\n', encoding='utf-8')
    validation = {'script_version': 'v5', 'episode_count': 100,
                  'checks': {'json_markdown_equal': True, 'v5_body_sha256_valid': True,
                             'single_active_script_version': 'v5',
                             'opening_illustration_marked_for_all_episodes': True},
                  'episodes': evidence}
    (output / '脚本一致性校验.json').write_text(json.dumps(validation, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return validation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, help='项目02_100集剧本/阅读与审校/下的新导出目录')
    parser.add_argument('--validate-only', action='store_true', help='只读检查v5 JSON，不导出')
    args = parser.parse_args()
    if args.validate_only:
        print(f'v5 JSON检查通过：{len(load_episodes())}集；逐集片头均要求独立配图。')
    elif args.output_dir:
        result = export(args.output_dir)
        print(f"已导出并核验{result['episode_count']}集v5剧本及独立配图标记。")
    else:
        parser.error('请给出--output-dir或--validate-only')


if __name__ == '__main__':
    main()
