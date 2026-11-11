#!/usr/bin/env python3
"""Build short phrase ruby subtitles using actual TTS word times."""
import argparse
import json
from pathlib import Path
import re
import unicodedata

from PIL import ImageFont
from pypinyin import Style, pinyin

ROOT = Path(__file__).resolve().parents[1]
FIX = {
    '长耳朵': ['cháng', 'ěr', 'duo'], '长满': ['zhǎng', 'mǎn'],
    '背着': ['bēi', 'zhe'], '挨着': ['āi', 'zhe'], '得最快': ['de', 'zuì', 'kuài'],
    '懂得': ['dǒng', 'de'], '燕麦': ['yàn', 'mài'], '爪子': ['zhuǎ', 'zi'],
    '兔子': ['tù', 'zi'], '尾巴': ['wěi', 'ba'], '胡萝卜': ['hú', 'luó', 'bo'],
    '舒服': ['shū', 'fu'], '朋友': ['péng', 'you'], '孩子': ['hái', 'zi'],
    '漂亮': ['piào', 'liang'], '地方': ['dì', 'fang'],
    '一会儿': ['yí', 'huìr', 'r'], '这儿': ['zhèr', 'r'],
    '哪儿': ['nǎr', 'r'], '点儿': ['diǎnr', 'r'], '歇一歇': ['xiē', 'yi', 'xiē'],
    '第一次': ['dì', 'yī', 'cì'], '皮皮': ['pí', 'pí'],
    '栗栗': ['lì', 'lì'], '团团': ['tuán', 'tuán'],
    '铺在': ['pū', 'zài'], '散发': ['sàn', 'fā'], '落了下去': ['luò', 'le', 'xià', 'qù'],
    '认真地': ['rèn', 'zhēn', 'de'], '一闪一闪地': ['yì', 'shǎn', 'yì', 'shǎn', 'de'],
    '温柔地': ['wēn', 'róu', 'de'], '深深地': ['shēn', 'shēn', 'de'],
    '轻轻地': ['qīng', 'qīng', 'de'], '刺猬': ['cì', 'wei'], '个': ['ge'],
}


def is_hanzi(ch):
    return bool(re.fullmatch(r'[\u3400-\u9fff]', ch))


def context_tokens(text, reviews):
    values = [v[0] for v in pinyin(text, style=Style.TONE, errors=lambda s: list(s))]
    numbers = [v[0] for v in pinyin(text, style=Style.TONE3, errors=lambda s: list(s))]
    assert len(values) == len(numbers) == len(text)
    for i, ch in enumerate(text):
        if ch == '一' and (i == 0 or text[i - 1] != '第'):
            next_tone = numbers[i + 1][-1:] if i + 1 < len(text) else ''
            values[i] = 'yí' if next_tone == '4' else 'yì'
        elif ch == '不':
            values[i] = 'bú' if i + 1 < len(text) and numbers[i + 1].endswith('4') else 'bù'
    for word, reading in FIX.items():
        for match in re.finditer(re.escape(word), text):
            values[match.start():match.end()] = reading
            reviews.append({'phrase': word, 'pinyin': reading, 'context': text, 'review': 'context_checked_not_audio_listen_certification'})
    tokens = []
    for i, (ch, reading) in enumerate(zip(text, values)):
        token = {'hanzi': ch, 'pinyin': unicodedata.normalize('NFC', reading) if is_hanzi(ch) else '',
                 'review': 'context_checked' if is_hanzi(ch) else 'punctuation'}
        if ch == '儿' and reading == 'r':
            token.update(erhua=True, link_to_previous_character=i - 1)
        tokens.append(token)
    return tokens


def ass_time(seconds):
    n = round(seconds * 100)
    return f'{n//360000}:{n//6000%60:02}:{n//100%60:02}.{n%100:02}'


def srt_time(seconds):
    n = round(seconds * 1000)
    return f'{n//3600000:02}:{n//60000%60:02}:{n//1000%60:02},{n%1000:03}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    out = args.output_dir
    timing = json.loads((out / 'character-alignment.json').read_text())
    voice = json.loads((out / 'voice-timeline.json').read_text())
    font = ImageFont.truetype(str(ROOT / 'local/fonts/NotoSans-Regular.ttf'), 48)
    width = lambda token: max(96, font.getlength(token['pinyin']) + 16) if token['pinyin'] else 24
    cues, reviews = [], []
    for unit in voice['units']:
        aligned = timing[unit['id']]
        tokens = context_tokens(unit['text'], reviews)
        group = []

        def flush():
            if not group:
                return
            first, last = group[0], group[-1]
            subset = tokens[first['start_char']:last['end_char']]
            cues.append({'cue_id': len(cues) + 1, 'unit_id': unit['id'], 'paragraph_id': unit['paragraph_id'],
                         'text': ''.join(t['hanzi'] for t in subset), 'tokens': subset,
                         'start_s': first['start_s'], 'end_s': last['end_s'],
                         'alignment': 'actual_tts_word_boundaries_phrase_groups',
                         'layout_width_px': sum(width(t) for t in subset), 'rows': 1})
            group.clear()

        for atom in aligned['word_atoms']:
            count = sum(a['hanzi'] for a in group)
            prospective = tokens[(group[0]['start_char'] if group else atom['start_char']):atom['end_char']]
            if group and (count + atom['hanzi'] > 7 or sum(width(t) for t in prospective) > 900):
                flush()
            group.append(atom)
            count = sum(a['hanzi'] for a in group)
            if re.search(r'[。！？：；]', atom['text']) or (re.search(r'[，]', atom['text']) and count >= 3) or count >= 7:
                flush()
        flush()
    # Avoid a one- or two-character flash when the preceding phrase can still
    # fit at full size. This preserves real timing and never covers next speech.
    merged = []
    for cue in cues:
        count = sum(is_hanzi(t['hanzi']) for t in cue['tokens'])
        if merged and count <= 2 and merged[-1]['unit_id'] == cue['unit_id']:
            previous = merged[-1]
            combined = previous['tokens'] + cue['tokens']
            combined_width = sum(width(t) for t in combined)
            if combined_width <= 900:
                previous.update(text=previous['text'] + cue['text'], tokens=combined,
                                end_s=cue['end_s'], layout_width_px=combined_width)
                continue
        merged.append(cue)
    cues = merged
    for i, cue in enumerate(cues, 1):
        cue['cue_id'] = i
    assert ''.join(c['text'] for c in cues) == ''.join(u['text'] for u in voice['units'])
    for i, cue in enumerate(cues):
        cue['start_s'] = round(cue['start_s'] * 25) / 25
        last_end = voice['units'][-1]['end_s']
        next_start = cues[i + 1]['start_s'] if i + 1 < len(cues) else last_end
        cue['end_s'] = min(round((cue['end_s'] + .08) * 25) / 25, round(next_start * 25) / 25)
        if i == len(cues) - 1:
            cue['end_s'] = min(cue['end_s'], round(last_end * 25) / 25)
        assert cue['end_s'] > cue['start_s'], cue
        assert cue['layout_width_px'] <= 900
        assert all(t['pinyin'] for t in cue['tokens'] if is_hanzi(t['hanzi']))
    header = '''[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hanzi,Noto Sans CJK SC,114,&H00DCF4FF,&H00DCF4FF,&H00322218,&HFF000000,0,0,0,0,100,100,0,0,1,2,0,8,0,0,0,1
Style: Pinyin,Noto Sans,66,&H00DCF4FF,&H00DCF4FF,&H00322218,&HFF000000,0,0,0,0,100,100,0,0,1,1,0,8,0,0,0,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    events, srt = [], []
    for cue in cues:
        a, b = ass_time(cue['start_s']), ass_time(cue['end_s'])
        plate = r'{\p1\an7\pos(0,0)\bord0\shad0\c&H322218&\alpha&H48&}m 96 1480 l 984 1480 b 997 1480 1008 1491 1008 1504 l 1008 1644 b 1008 1657 997 1668 984 1668 l 96 1668 b 83 1668 72 1657 72 1644 l 72 1504 b 72 1491 83 1480 96 1480'
        events.append(f'Dialogue: 0,{a},{b},Hanzi,,0,0,0,,{plate}')
        x = 540 - cue['layout_width_px'] / 2
        for token in cue['tokens']:
            cell = width(token)
            center = x + cell / 2
            token.update(cell_center_x=round(center, 2), cell_width_px=round(cell, 2))
            if token['pinyin']:
                events.append(f"Dialogue: 1,{a},{b},Pinyin,,0,0,0,,{{\\an8\\pos({center:.1f},1500)}}{token['pinyin']}")
            events.append(f"Dialogue: 1,{a},{b},Hanzi,,0,0,0,,{{\\an8\\pos({center:.1f},1566)}}{token['hanzi']}")
            x += cell
        srt.append(f"{cue['cue_id']}\n{srt_time(cue['start_s'])} --> {srt_time(cue['end_s'])}\n{cue['text']}\n")
    (out / 'episode.ass').write_text(header + '\n'.join(events) + '\n')
    (out / 'episode.srt').write_text('\n'.join(srt))
    (out / 'subtitles.ruby.json').write_text(json.dumps(cues, ensure_ascii=False, indent=2) + '\n')
    report = {'hanzi': sum(is_hanzi(t['hanzi']) for c in cues for t in c['tokens']), 'cues': len(cues),
              'pinyin_coverage': 1.0, 'context_review': 'completed_against_episode_text',
              'target_font_px': {'hanzi': 76, 'pinyin': 48},
              'libass_fontsize_calibration': {'hanzi': 114, 'pinyin': 66,
                  'reason': 'match actual rasterized glyph scale to bundled-font 76px/48px reference; libass normalizes font metrics'},
              'audio_pronunciation_listen_review': 'not_certified', 'overrides': reviews}
    (out / 'pinyin-review.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    lines = ['# 第004集逐句拼音核对', '', '词语读音、轻声、变调及儿化按正文上下文核对；不以文字核对冒充完整音频听审。', '', '| 时间 | 汉字 | 拼音 |', '| --- | --- | --- |']
    for cue in cues:
        lines.append(f"| {cue['start_s']:.2f}–{cue['end_s']:.2f} | {cue['text']} | {' '.join(t['pinyin'] for t in cue['tokens'] if t['pinyin'])} |")
    (out / '拼音核对表.md').write_text('\n'.join(lines) + '\n')
    print(f"RUBY_READY {len(cues)} short cues, {report['hanzi']} hanzi, coverage=100%")


if __name__ == '__main__':
    main()
