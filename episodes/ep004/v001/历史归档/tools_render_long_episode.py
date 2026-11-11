#!/usr/bin/env python3
"""Render a locked variable-shot episode with fixed images and ruby subtitles."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SR = 48000


def write_wave(path, data):
    with wave.open(str(path), 'wb') as f:
        f.setparams((1, 2, SR, 0, 'NONE', 'not compressed'))
        f.writeframes((data * 32767).clip(-32768, 32767).astype('<i2').tobytes())


def prepare_assets(out, duration):
    for name in ('NotoSansCJKsc-Regular.otf', 'NotoSansCJKsc-Bold.otf', 'NotoSans-Regular.ttf',
                 'Noto-CJK-copyright.txt', 'Noto-Sans-copyright.txt'):
        target = out / 'fonts' / name
        if not target.exists():
            shutil.copy2(ROOT / 'local/fonts' / name, target)
    if not (out / 'mix.wav').exists():
        with wave.open(str(out / 'audio/voice.wav'), 'rb') as f:
            assert (f.getnchannels(), f.getsampwidth(), f.getframerate()) == (1, 2, SR)
            voice = np.frombuffer(f.readframes(f.getnframes()), dtype='<i2').astype(np.float32) / 32768
        n = len(voice)
        music = np.zeros(n, dtype=np.float32)
        chords = [[130.813, 164.814, 195.998], [110., 130.813, 164.814],
                  [87.307, 110., 130.813], [97.999, 123.471, 146.832]]
        for k, start in enumerate(np.arange(0, duration, 2.7)):
            a = round(start * SR)
            length = min(round(5.5 * SR), n - a)
            t = np.arange(length, dtype=np.float32) / SR
            frequency = chords[int(start // 12) % 4][k % 3]
            envelope = (1 - np.exp(-t / .35)) * np.exp(-t / 1.5)
            note = (np.sin(2 * np.pi * frequency * t) + .18 * np.sin(4 * np.pi * frequency * t)) * envelope
            music[a:a + length] += note
        music *= .0045 / np.sqrt(np.mean(music ** 2))
        noise = np.random.default_rng(1).standard_normal(n, dtype=np.float32)
        spectrum = np.fft.rfft(noise)
        frequency = np.fft.rfftfreq(n, 1 / SR)
        spectrum *= np.exp(-(frequency / 350) ** 4)
        noise = np.fft.irfft(spectrum, n).astype(np.float32)
        del spectrum, frequency
        noise *= .00065 / np.sqrt(np.mean(noise ** 2))
        t = np.arange(n, dtype=np.float32) / SR
        fade = np.minimum(1, t / 2) * np.minimum(1, (duration - t) / 5)
        music *= fade
        noise *= fade
        mix = voice + music + noise
        assert float(np.max(np.abs(mix))) < 1
        write_wave(out / 'music.wav', music)
        write_wave(out / 'ambience.wav', noise)
        write_wave(out / 'mix.wav', mix)
        shutil.copy2(out / 'audio/voice.wav', out / 'voice.wav')
        report = {'source': 'original procedural synthesis; no third-party samples', 'seed': 1,
                  'music_rms_before_fade': .0045, 'ambience_rms_before_fade': .00065,
                  'voice_peak': float(np.max(np.abs(voice))), 'mix_peak': float(np.max(np.abs(mix))),
                  'voice_sha256': hashlib.sha256((out / 'voice.wav').read_bytes()).hexdigest(),
                  'duration_s': n / SR, 'sample_rate': SR, 'voice_filter_reapplied': False}
        (out / 'audio-mix-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    if not (out / 'cover.png').exists():
        image = ImageOps.fit(Image.open(out / 'cover_base.png').convert('RGB'), (1080, 1920), method=Image.Resampling.LANCZOS)
        layer = Image.new('RGBA', (1080, 1920))
        draw = ImageDraw.Draw(layer)
        draw.rounded_rectangle((108, 1140, 972, 1580), radius=48, fill=(255, 244, 220, 240))
        font = ImageFont.truetype(str(out / 'fonts/NotoSansCJKsc-Bold.otf'), 112)
        draw.text((540, 1360), '半坡歇歇', font=font, anchor='mm', fill='#182232')
        Image.alpha_composite(image.convert('RGBA'), layer).convert('RGB').save(out / 'cover.png')
        (out / 'cover.svg').write_text('''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920"><image href="cover_base.png" width="1080" height="1920" preserveAspectRatio="xMidYMid slice"/><rect x="108" y="1140" width="864" height="440" rx="48" fill="#FFF4DC" fill-opacity="0.94"/><text x="540" y="1360" dominant-baseline="central" text-anchor="middle" font-family="Noto Sans CJK SC" font-size="112" font-weight="bold" fill="#182232">半坡歇歇</text></svg>''')
        (out / 'cover-title.txt').write_text('半坡歇歇\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--preview-seconds', type=float)
    parser.add_argument('--assets-only', action='store_true')
    args = parser.parse_args()
    out = args.output_dir.resolve()
    plan = json.loads((out / 'storyboard.json').read_text())
    assert plan.get('actual_audio_measured') and plan['max_visible_duration_s'] <= 15
    prepare_assets(out, plan['total_duration_s'])
    if args.assets_only:
        print('AUDIO_BEDS_COVER_FONTS_READY', flush=True)
        return
    duration = args.preview_seconds or plan['total_duration_s']
    frames = round(duration * 25)
    selected = [s for s in plan['shots'] if s['visible_start_s'] < duration]
    images, fixed_bytes = {}, {}
    for s in selected:
        path = out / s['image']
        if not path.exists():
            raise FileNotFoundError(f"缺少本镜真实原图：{s['id']} {path}")
        with Image.open(path) as original:
            original.verify()
        image = ImageOps.fit(Image.open(path).convert('RGB'), (1080, 1920), method=Image.Resampling.LANCZOS)
        images[s['id']] = image
        fixed_bytes[s['id']] = image.tobytes()
    suffix = f'_preview{duration:g}' if args.preview_seconds else ''
    clean = out / f'ep004{suffix}_clean.mp4'
    publish = out / f'ep004{suffix}.mp4'
    if clean.exists() or publish.exists():
        raise FileExistsError('导出文件已存在；先保留版本或使用新的任务目录')
    base = 'setsar=1'
    if not args.preview_seconds:
        base += f',fade=t=out:st={duration-4:.2f}:d=4:color=0x182232'
    graph = f'[0:v]{base},split=2[clean][ruby];[ruby]ass=filename=episode.ass:fontsdir=fonts[publish]'
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'warning', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
               '-s', '1080x1920', '-r', '25', '-i', '-', '-i', 'mix.wav',
               '-filter_complex_threads', '1', '-filter_complex', graph]
    for video_label, path in (('[clean]', clean), ('[publish]', publish)):
        command += ['-map', video_label, '-map', '1:a', '-frames:v', str(frames), '-t', str(duration),
                    '-r', '25', '-c:v', 'libx264', '-crf', '20', '-preset', 'veryfast', '-threads', '2',
                    '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-ar', str(SR),
                    '-movflags', '+faststart', str(path)]
    stem = 'render' + suffix
    with (out / f'{stem}.log').open('w') as log:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log, cwd=out)
        current = 0
        try:
            for frame in range(frames):
                t = frame / 25
                while current + 1 < len(plan['shots']) and t >= plan['shots'][current + 1]['actual_start_s'] + .48:
                    current += 1
                shot = plan['shots'][current]
                if current + 1 < len(plan['shots']):
                    nxt = plan['shots'][current + 1]
                    start = nxt['actual_start_s'] - .48
                    if start <= t < start + .96:
                        alpha = (t - start) / .96
                        data = Image.blend(images[shot['id']], images[nxt['id']], alpha).tobytes()
                    else:
                        data = fixed_bytes[shot['id']]
                else:
                    data = fixed_bytes[shot['id']]
                process.stdin.write(data)
                if frame % 250 == 0:
                    print(f'frame {frame}/{frames}, t={t:.2f}s, shot={shot["id"]}', flush=True)
        finally:
            process.stdin.close()
        if process.wait() != 0:
            raise RuntimeError(f'渲染失败，见{stem}.log')
    metadata = {'episode': 'ep004', 'duration_s': duration, 'fps': 25, 'frames': frames,
                'preview': bool(args.preview_seconds), 'resolution': [1080, 1920],
                'shot_count': len(plan['shots']), 'crossfade_s': .96, 'curve': 'linear',
                'within_shot_motion': 'none', 'subtitles_after_picture_transitions': True,
                'clean': clean.name, 'publish': publish.name, 'shots': selected,
                'audio': 'mix.wav', 'subtitles': 'episode.ass', 'character_registry': 'references/',
                'fonts': [{'path': str(p.relative_to(out)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in (out / 'fonts').glob('*')]}
    (out / ('project' + suffix + '.json')).write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
    if not args.preview_seconds:
        (out / 'timeline.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n')
    print(f'RENDER_COMPLETE {publish}', flush=True)


if __name__ == '__main__':
    main()
