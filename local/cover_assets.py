#!/usr/bin/env python3
"""Validate and render the v3 cover from an episode's cover-plan.json."""
import argparse
import hashlib
from html import escape
import json
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / '03_素材与参数/封面与字幕参数.json'


def load_cover_plan(out):
    path = out / 'cover-plan.json'
    if not path.is_file():
        raise ValueError('缺少cover-plan.json；按docs/production/COVER_SPEC.md确定6–10字“皮皮＋一件事”标题及封面方案。')
    plan = json.loads(path.read_text(encoding='utf-8'))
    config = json.loads(CONFIG.read_text(encoding='utf-8'))['cover']
    if plan.get('template') != config['template']:
        raise ValueError('cover-plan.json须使用当前封面模板：' + config['template'])
    title = plan.get('title', '')
    low, high = config['title_hanzi_allowed']
    if (not isinstance(title, str) or not re.fullmatch(r'[\u3400-\u9fff]+', title)
            or not low <= len(title) <= high or not title.startswith(config['title_prefix'])):
        raise ValueError('封面/发布标题须为6–10个汉字，以“皮皮”开头，描述本集真实事件。')
    lines = plan.get('title_lines')
    if (not isinstance(lines, list) or len(lines) != 2
            or any(not isinstance(line, str) or not 3 <= len(line) <= config['max_hanzi_per_line'] for line in lines)
            or ''.join(lines) != title):
        raise ValueError('title_lines须按词义分成两行，每行3–5字；拼接后与title完全相同。')
    for key in ('scene', 'dominant_color', 'pipi_pose', 'pipi_expression', 'event_description'):
        if not isinstance(plan.get(key), str) or not plan[key].strip():
            raise ValueError('封面方案缺少：' + key)
    if plan.get('pipi_front_facing') is not True:
        raise ValueError('封面须规划皮皮正脸清楚出镜。')
    if not isinstance(plan.get('key_props'), list) or not plan['key_props']:
        raise ValueError('封面方案须记录本集关键道具。')
    references = plan.get('reference_inputs')
    if not isinstance(references, list) or not references:
        raise ValueError('封面方案须记录实际使用的皮皮身份参考及相关道具参考路径。')
    for reference in references:
        if not isinstance(reference, str):
            raise ValueError('参考路径须为字符串。')
        path = Path(reference)
        if not (path if path.is_absolute() else ROOT / path).is_file():
            raise ValueError('封面参考不存在：' + reference)
        with Image.open(path if path.is_absolute() else ROOT / path) as reference_image:
            reference_image.verify()
    snapshot = json.loads((out / 'script.snapshot.json').read_text(encoding='utf-8'))
    if snapshot.get('script_version') != 'v5' or plan.get('episode') != snapshot['id']:
        raise ValueError('封面方案须对应本集v5剧本快照。')
    source_ids = plan.get('source_paragraph_ids')
    valid_ids = {p['id'] for p in snapshot['narration_paragraphs'] if p['id'] != 'p000'}
    if not isinstance(source_ids, list) or not source_ids or any(p not in valid_ids for p in source_ids):
        raise ValueError('须用有效正文段落ID记录封面事件依据；不能只引用片头。')
    return plan, config


def validate_publish_titles(path, title):
    text = path.read_text(encoding='utf-8')
    sections = re.split(r'^##\s+(抖音|小红书|微信视频号)\s*$', text, flags=re.M)
    found = {}
    for platform, body in zip(sections[1::2], sections[2::2]):
        titles = re.findall(r'^\*\*标题[：:]\*\*\s*(.*?)\s*$', body, flags=re.M)
        if platform in found or titles != [title]:
            raise ValueError(f'{platform}标题须与封面title完全一致：{title}')
        found[platform] = title
    if set(found) != {'抖音', '小红书', '微信视频号'}:
        raise ValueError('发布文案须有## 抖音、## 小红书、## 微信视频号，及各自的**标题：**。')
    return found


def cover_fingerprint(out, plan, config):
    # Review notes may be completed after rendering without changing any pixels.
    rendering_plan = {key: plan[key] for key in ('template', 'episode', 'title', 'title_lines')}
    return hashlib.sha256(json.dumps({'plan': rendering_plan, 'config': config,
        'base_sha256': hashlib.sha256((out / 'cover_base.png').read_bytes()).hexdigest(),
        'font_sha256': hashlib.sha256((ROOT / 'local/fonts/NotoSansCJKsc-Bold.otf').read_bytes()).hexdigest()
    }, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()


def validate_cover_outputs(out):
    plan, config = load_cover_plan(out)
    report = json.loads((out / 'cover-render.json').read_text(encoding='utf-8'))
    hashes = {name: hashlib.sha256((out / name).read_bytes()).hexdigest()
              for name in ('cover.png', 'cover.svg', 'cover-title.txt')}
    if report.get('fingerprint') != cover_fingerprint(out, plan, config) or report.get('output_sha256') != hashes:
        raise ValueError('封面成品/标题排版/底图/字体与排版记录不一致；请核对工程版本。')
    return report


def render_cover(out):
    plan, config = load_cover_plan(out)
    base = out / 'cover_base.png'
    fingerprint = cover_fingerprint(out, plan, config)
    report_path = out / 'cover-render.json'
    targets = [out / name for name in ('cover.png', 'cover.svg', 'cover-title.txt')]
    if any(path.exists() for path in targets):
        previous = json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else {}
        if previous.get('fingerprint') == fingerprint and all(path.is_file() for path in targets):
            current_hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in targets}
            if current_hashes == previous.get('output_sha256'):
                return previous
        raise FileExistsError('封面已存在且与当前方案不一致；保留历史版本，在新工程版本内制作。')
    with Image.open(base) as source_image:
        image = ImageOps.fit(source_image.convert('RGB'), (1080, 1920), method=Image.Resampling.LANCZOS)
    layer = Image.new('RGBA', image.size)
    draw = ImageDraw.Draw(layer)
    card = config['card']
    box = (card['x'], card['y'], card['x'] + card['width'], card['y'] + card['height'])
    fill = tuple(bytes.fromhex(card['fill'].lstrip('#'))) + (round(card['opacity'] * 255),)
    draw.rounded_rectangle(box, radius=card['radius'], fill=fill)
    font = ImageFont.truetype(str(ROOT / 'local/fonts/NotoSansCJKsc-Bold.otf'), config['size_px'])
    svg_text = []
    for line, y in zip(plan['title_lines'], config['title_line_center_y']):
        bounds = draw.textbbox((config['title_center_x'], y), line, font=font, anchor='mm')
        if not (box[0] + 48 <= bounds[0] and bounds[2] <= box[2] - 48
                and box[1] + 24 <= bounds[1] and bounds[3] <= box[3] - 24):
            raise ValueError('标题超出卡片安全范围，请调整语义换行，不缩小字体强塞。')
        draw.text((config['title_center_x'], y), line, font=font, anchor='mm', fill=config['text_color'])
        svg_text.append(f'<text x="{config["title_center_x"]}" y="{y}" dominant-baseline="central" text-anchor="middle" font-family="Noto Sans CJK SC" font-size="{config["size_px"]}" font-weight="700" fill="{config["text_color"]}">{escape(line)}</text>')
    Image.alpha_composite(image.convert('RGBA'), layer).convert('RGB').save(out / 'cover.png')
    (out / 'cover.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920"><image href="cover_base.png" width="1080" height="1920" preserveAspectRatio="xMidYMid slice"/>'
        + f'<rect x="{card["x"]}" y="{card["y"]}" width="{card["width"]}" height="{card["height"]}" rx="{card["radius"]}" fill="{card["fill"]}" fill-opacity="{card["opacity"]}"/>'
        + ''.join(svg_text) + '</svg>\n', encoding='utf-8')
    (out / 'cover-title.txt').write_text(plan['title'] + '\n', encoding='utf-8')
    report = {'template': config['template'], 'title': plan['title'], 'title_lines': plan['title_lines'],
              'fingerprint': fingerprint, 'output_sha256': {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in targets},
              'layout_bounds': 'passed', 'visual_event_accuracy_review': 'pending',
              'pipi_front_face_review': 'pending', 'cross_episode_differentiation_review': 'pending'}
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--validate-only', action='store_true', help='只读校验方案，不出图或写文件')
    parser.add_argument('--check-copy', action='store_true', help='同时核对三平台标题与封面完全一致')
    args = parser.parse_args()
    out = args.output_dir.resolve()
    plan, _ = load_cover_plan(out)
    if args.check_copy:
        validate_publish_titles(out / '发布文案.md', plan['title'])
    print(json.dumps({'cover_plan': 'passed', 'title': plan['title'],
                      'publish_titles': 'passed' if args.check_copy else 'not_checked'}
                     if args.validate_only else render_cover(out), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
