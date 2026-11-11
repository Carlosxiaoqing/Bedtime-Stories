#!/usr/bin/env python3
"""Export the user's v4 narration JSON without imposing a shot count or duration."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / '02_100集剧本/用户长稿v4/结构化JSON'


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def load_episodes():
    paths = sorted(LIBRARY.glob('ep*.json'))
    if [p.stem for p in paths] != [f'ep{n:03}' for n in range(1, 101)]:
        raise ValueError('v4须有001–100完整JSON；001–003仅作原短稿参考')
    episodes = []
    for n, path in enumerate(paths, 1):
        e = json.loads(path.read_text(encoding='utf-8'))
        if (e['id'], e['episode'], e['script_version']) != (path.stem, n, 'v4'):
            raise ValueError(f'集号或版本不一致：{path}')
        paragraphs = e['narration_paragraphs']
        if not paragraphs or [p['id'] for p in paragraphs] != [f'p{i:03}' for i in range(1, len(paragraphs) + 1)]:
            raise ValueError(f'段落编号不完整：{path}')
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
        if e['actual_duration_s'] is not None and e['actual_duration_s'] <= 0:
            raise ValueError(f'实测时长必须为正或留空：{path}')
        if e['storyboard']['status'] == 'not_started' and e['storyboard']['shots']:
            raise ValueError(f'分镜未开始却有镜头数据：{path}')
        if e['production_scope'] != ('reference_only' if n <= 3 else 'adopted_user_long_script'):
            raise ValueError(f'制作范围不一致：{path}')
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
    book_path = output / '100集睡前故事合集_校订版v4.md'
    if book_path.exists() or any(single.iterdir()):
        raise FileExistsError('阅读导出已存在，请使用新的独立任务目录')
    book = [
        '# 100集睡前故事合集｜用户长稿校订版 v4', '',
        '2026-11-11（北京时间）。从用户长稿v4 JSON导出，JSON为唯一改稿源。', '',
        '001–003原短稿仅作阅读参考；004–100采用用户新正文，保留完整情节和段落，只有校订记录列出的最小修正。', '',
        '口播使用晓晓rate=-35%／pitch=-2Hz／volume=+0%；完整读完，不设五分钟上限。标题、主题、目录及制作说明不读入口播，不增加具体年龄说明。', '',
        '阅读稿不能作为媒体完成记录；配音、角色参考图、正式分镜及视频状态以对应版本记录为准。', '',
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
        # Recover the rendered body, rather than comparing two copies in memory.
        rendered = path.read_text(encoding='utf-8').split('\n\n', 2)[2].rstrip('\n')
        if rendered != body:
            raise ValueError(f'Markdown口播与JSON不同：{path}')
        evidence.append({'episode': e['id'], 'paragraph_count': len(e['narration_paragraphs']),
                         'cn_characters': e['cn_characters'], 'narration_sha256': digest(body),
                         'json_markdown_equal': True})
    book_path.write_text('\n'.join(book) + '\n', encoding='utf-8')
    parts = re.split(r'^## 第(\d{3})集[：:](.*)\n', book_path.read_text(encoding='utf-8'), flags=re.M)
    if len(parts) != 301:
        raise ValueError('合集集数错误')
    for i, e in enumerate(episodes):
        j = 1 + i * 3
        body = parts[j + 2].split('\n\n', 1)[1]
        body = re.split(r'\n\n---\n', body, maxsplit=1)[0].rstrip('\n')
        if body != '\n\n'.join(p['text'] for p in e['narration_paragraphs']):
            raise ValueError(f'合集口播与JSON不同：{e["id"]}')
    validation = {'script_version': 'v4', 'episode_count': 100, 'adopted_long_episode_count': 97,
                  'checks': {'json_single_markdown_equal': True, 'json_collection_equal': True},
                  'actual_audio_measured': any(e['actual_duration_s'] is not None for e in episodes[3:]),
                  'storyboards_created': any(e['storyboard']['shots'] for e in episodes[3:]), 'episodes': evidence}
    (output / '脚本一致性校验.json').write_text(json.dumps(validation, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return validation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, help='项目02_100集剧本/阅读与审校/下的独立导出目录')
    parser.add_argument('--validate-only', action='store_true', help='只读检查JSON，不导出')
    args = parser.parse_args()
    if args.validate_only:
        print(f'v4 JSON检查通过：{len(load_episodes())}集；未生成媒体。')
    elif args.output_dir:
        result = export(args.output_dir)
        print(f"已导出并核验{result['episode_count']}集；004–100为新长稿，001–003仅作原短稿参考。")
    else:
        parser.error('请给出--output-dir或--validate-only')


if __name__ == '__main__':
    main()
