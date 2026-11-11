#!/usr/bin/env python3
"""Lock full-text shot coverage to measured TTS word boundaries."""
import argparse
import html
import json
from pathlib import Path
import re


def hanzi(text):
    return ''.join(re.findall(r'[\u3400-\u9fff]', text))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    out = args.output_dir
    audio = json.loads((out / 'voice-timeline.json').read_text())
    plan = json.loads((out / 'storyboard.draft.json').read_text())
    unit_maps = {}
    for u in audio['units']:
        assert hanzi(u['text']) == hanzi(''.join(html.unescape(w['text']) for w in u['word_boundaries'])), u['id']
        positions = [i for i, ch in enumerate(u['text']) if hanzi(ch)]
        aligned = {}
        cursor = 0
        atoms = []
        for w in u['word_boundaries']:
            text = hanzi(html.unescape(w['text']))
            if not text:
                continue
            assert w['end_s'] >= w['start_s']
            for k in range(len(text)):
                pos = positions[cursor + k]
                a = w['start_s'] + (w['end_s'] - w['start_s']) * k / len(text)
                b = w['start_s'] + (w['end_s'] - w['start_s']) * (k + 1) / len(text)
                aligned[pos] = {'start_s': a, 'end_s': b, 'word': w['text'], 'method': 'tts_word_boundary_within_word_interpolation'}
            atoms.append({'start_char': positions[cursor], 'last_hanzi_char': positions[cursor + len(text) - 1],
                          'start_s': w['start_s'], 'end_s': w['end_s'], 'hanzi': len(text)})
            cursor += len(text)
        for i, atom in enumerate(atoms):
            atom['start_char'] = 0 if i == 0 else atoms[i - 1]['last_hanzi_char'] + 1
            atom['end_char'] = atom['last_hanzi_char'] + 1
            # Attach following punctuation to the word that was just spoken.
            while atom['end_char'] < len(u['text']) and not hanzi(u['text'][atom['end_char']]):
                atom['end_char'] += 1
            atom['start_char'] = 0 if i == 0 else atoms[i - 1]['end_char']
            atom['text'] = u['text'][atom['start_char']:atom['end_char']]
        assert ''.join(a['text'] for a in atoms) == u['text']
        unit_maps[u['id']] = {'text': u['text'], 'characters': aligned, 'word_atoms': atoms,
                              'start_s': u['start_s'], 'end_s': u['end_s']}
    # Cuts are midpoint pauses around the exact source ranges, never a global
    # words-per-second estimate. Every original character remains in order.
    for s in plan['shots']:
        ranges = s['source_ranges']
        first, last = ranges[0], ranges[-1]
        a = unit_maps[first['unit_id']]
        b = unit_maps[last['unit_id']]
        starts = [v['start_s'] for i, v in a['characters'].items() if first['start_char'] <= i < first['end_char']]
        ends = [v['end_s'] for i, v in b['characters'].items() if last['start_char'] <= i < last['end_char']]
        s['speech_start_s'], s['speech_end_s'] = min(starts), max(ends)
    cuts = [0.0]
    for a, b in zip(plan['shots'], plan['shots'][1:]):
        cuts.append(round((a['speech_end_s'] + b['speech_start_s']) / 2 * 25) / 25)
    cuts.append(audio['duration_s'])
    for i, s in enumerate(plan['shots']):
        start, end = cuts[i], cuts[i + 1]
        visible_start = start - (.48 if i else 0)
        visible_end = end + (.48 if i < len(plan['shots']) - 1 else 0)
        s.update(actual_start_s=start, actual_end_s=end,
                 visible_start_s=visible_start, visible_end_s=visible_end,
                 visible_duration_s=round(visible_end - visible_start, 2))
        assert s['visible_duration_s'] <= 15, (s['id'], s['visible_duration_s'])
        assert end > start
    assert ''.join(s['text'] for s in plan['shots']) == ''.join(u['text'] for u in audio['units'])
    plan.update(status='audio_locked_ready_for_images', total_duration_s=audio['duration_s'],
                actual_audio_measured=True, max_visible_duration_s=max(s['visible_duration_s'] for s in plan['shots']))
    (out / 'character-alignment.json').write_text(json.dumps(unit_maps, ensure_ascii=False, indent=2) + '\n')
    (out / 'storyboard.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n')
    lines = [f'# 第{plan["episode"][2:]}集正式分镜与实测时间', '',
             f"完整口播；成片计划{audio['duration_s']:.2f}秒（按真实录音），{len(plan['shots'])}幅新剧情插画。", '',
             '时间为名义切点；可见时长包含前后叠化，最长不超过15秒。图片尚须逐镜制作，不能以时间轴锁定代替素材完成。', '',
             '| 镜号 | 时间（秒） | 含叠化可见时长 | 画面 | 完整对应口播 |', '| --- | --- | --- | --- | --- |']
    for s in plan['shots']:
        lines.append(f"| {s['id']:02} | {s['actual_start_s']:.2f}–{s['actual_end_s']:.2f} | {s['visible_duration_s']:.2f}秒 | {s['title']} | {s['text']} |")
    (out / '正式分镜.md').write_text('\n'.join(lines) + '\n')
    print(f"LOCKED {len(plan['shots'])} shots, duration={audio['duration_s']:.2f}s, max visible={plan['max_visible_duration_s']:.2f}s")


if __name__ == '__main__':
    main()
