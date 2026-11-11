#!/usr/bin/env python3
"""Check finished long-episode media, narration coverage and retained sources."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageOps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--delivery-dir', type=Path, help='可选：检查日期目录里的最终成片；源素材仍从工程读取')
    args = parser.parse_args()
    out = args.output_dir.resolve()
    delivery = args.delivery_dir.resolve() if args.delivery_dir else out
    checks = out / 'checks'
    checks.mkdir(exist_ok=True)
    read = lambda name: json.loads((out / name).read_text())
    han = lambda text: ''.join(re.findall(r'[\u4e00-\u9fff]', text))
    source = ''.join(p['text'] for p in read('script.snapshot.json')['narration_paragraphs'])
    plan, voice, cues = read('storyboard.json'), read('voice-timeline.json'), read('subtitles.ruby.json')
    expected = han(source)
    assert len(expected) == 742
    assert han(''.join(u['text'] for u in voice['units'])) == expected
    assert han(''.join(s['text'] for s in plan['shots'])) == expected
    assert han(''.join(c['text'] for c in cues)) == expected
    assert han(''.join(w['text'] for u in voice['units'] for w in u['word_boundaries'])) == expected
    previous = 0
    for cue in cues:
        assert previous <= cue['start_s'] < cue['end_s'] <= plan['total_duration_s']
        assert cue['layout_width_px'] <= 900
        assert ''.join(t['hanzi'] for t in cue['tokens']) == cue['text']
        assert all(t['pinyin'] for t in cue['tokens'] if han(t['hanzi']))
        previous = cue['end_s']
    assert voice['voice'] == {'voice': 'zh-CN-XiaoxiaoNeural', 'rate': '-35%', 'pitch': '-2Hz', 'volume': '+0%'}
    hashes, images = [], []
    for i, shot in enumerate(plan['shots']):
        assert shot['motion'] == 'fixed'
        assert shot['visible_duration_s'] <= 15
        if i:
            assert abs(plan['shots'][i-1]['actual_end_s'] - shot['actual_start_s']) < 1e-6
        path = out / shot['image']
        with Image.open(path) as im:
            im.verify()
        hashes.append(hashlib.sha256(path.read_bytes()).hexdigest())
        images.append(ImageOps.fit(Image.open(path).convert('RGB'), (162, 288)))
        assert path.with_suffix('.source.json').exists()
        refs = read(shot['reference_manifest'])
        assert refs
    assert len(set(hashes)) == len(plan['shots']) == 35
    root = Path(__file__).resolve().parents[1]
    old = list((root / 'episodes/ep001/v005/images').glob('*.png'))
    old += list((root / 'episodes').glob('ep00[23]/v001/images/*.png'))
    old_hashes = {hashlib.sha256(p.read_bytes()).hexdigest() for p in old}
    assert not (set(hashes) & old_hashes)
    montage = Image.new('RGB', (162*7, 314*5), '#f7f1e6')
    draw = ImageDraw.Draw(montage)
    for i, im in enumerate(images):
        x, y = i % 7 * 162, i // 7 * 314
        montage.paste(im, (x, y))
        draw.text((x+4, y+290), str(i+1), fill='black')
    montage.save(checks / 'storyboard_contact.jpg', quality=92)
    audio = {}
    for name in ('voice.wav', 'music.wav', 'ambience.wav', 'mix.wav'):
        with wave.open(str(out / name)) as f:
            assert (f.getnchannels(), f.getsampwidth(), f.getframerate()) == (1, 2, 48000)
            samples = np.frombuffer(f.readframes(f.getnframes()), dtype='<i2')
            assert abs(len(samples)/48000 - plan['total_duration_s']) < .001
        assert np.abs(samples.astype('int32')).max() < 32767
        audio[name] = {'peak': int(np.abs(samples.astype('int32')).max()), 'samples': len(samples)}
    videos = {}
    for name in ('ep004.mp4', 'ep004_clean.mp4'):
        path = delivery / name
        probe = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)], check=True, capture_output=True, text=True)
        info = json.loads(probe.stdout)
        (checks / (name + '.ffprobe.json')).write_text(probe.stdout)
        v = next(s for s in info['streams'] if s['codec_type'] == 'video')
        a = next(s for s in info['streams'] if s['codec_type'] == 'audio')
        assert (v['width'], v['height'], v['avg_frame_rate'], v['pix_fmt'], v['codec_name']) == (1080, 1920, '25/1', 'yuv420p', 'h264')
        assert int(v['nb_frames']) == 6968
        assert a['codec_name'] == 'aac' and a['sample_rate'] == '48000' and a['channels'] == 1
        assert abs(float(info['format']['duration']) - plan['total_duration_s']) <= .08
        decode = subprocess.run(['ffmpeg', '-hide_banner', '-v', 'error', '-threads', '2', '-i', str(path), '-f', 'null', '-'], capture_output=True, text=True)
        (checks / (name + '.decode.log')).write_text(decode.stderr)
        assert decode.returncode == 0 and not decode.stderr.strip()
        videos[name] = {'bytes': path.stat().st_size, 'full_decode': 'passed', 'frames': int(v['nb_frames']), 'duration_s': float(info['format']['duration'])}
    for t in (6, 45, 81, 110, 145, 185, 215, 240, 267, 278.6):
        target = checks / f'final_{t:g}.png'
        subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', str(delivery/'ep004.mp4'), '-frames:v', '1', '-y', str(target)], check=True)
        Image.open(target).resize((360, 640), Image.Resampling.LANCZOS).save(checks / f'phone_{t:g}.png')
    assert Image.open(out / 'cover.png').size == (1080, 1920)
    Image.open(out/'cover.png').resize((360,640), Image.Resampling.LANCZOS).save(checks/'cover_phone.png')
    acceptance_path = out / '用户验收记录.json'
    acceptance = json.loads(acceptance_path.read_text()) if acceptance_path.exists() else {}
    report = {'technical_checks': 'passed', 'source_hanzi': len(expected), 'narration_coverage': 1.0,
              'word_boundary_text_coverage': 1.0, 'subtitle_hanzi_coverage': 1.0, 'cues': len(cues),
              'shots': len(hashes), 'unique_active_plot_images': len(set(hashes)),
              'historical_images_compared': len(old), 'historical_plot_reuse': False,
              'current_episode_cover_base_reuse': 'shot 13; permitted by COVER_SPEC; not another plot shot',
              'max_image_visible_s': max(s['visible_duration_s'] for s in plan['shots']),
              'audio': audio, 'videos': videos, 'full_human_listen_watch': 'not_certified',
              'user_acceptance': acceptance.get('status', 'pending'), 'publication': 'not_published'}
    (checks/'technical-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
