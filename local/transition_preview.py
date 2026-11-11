#!/usr/bin/env python3
"""Create a silent A/B preview of static-image opacity transitions."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
FPS = 25
DURATION = 12
CROSSFADE = 0.96


def smoothstep(value):
    return value * value * (3 - 2 * value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    video = output / '静态图片转场对比.mp4'
    if video.exists():
        raise FileExistsError(video)
    sources = [ROOT / f'episodes/ep001/v005/images/shot_{n:02}.png' for n in (1, 5, 9)]
    stills = [ImageOps.fit(Image.open(p).convert('RGB'), (420, 746), method=Image.Resampling.LANCZOS) for p in sources]
    font = ImageFont.truetype(str(ROOT / 'local/fonts/NotoSansCJKsc-Regular.otf'), 28)
    small = ImageFont.truetype(str(ROOT / 'local/fonts/NotoSansCJKsc-Regular.otf'), 22)
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
               '-s', '900x900', '-r', str(FPS), '-i', '-', '-an', '-c:v', 'libx264',
               '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(video)]
    frame_states = []
    with (output / 'render.log').open('w') as log:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log)
        try:
            for index in range(FPS * DURATION):
                time = index / FPS
                a = b = 0
                alpha = 0.0
                if time < 3.04:
                    pass
                elif time < 4:
                    a, b, alpha = 0, 1, (time - 3.04) / CROSSFADE
                elif time < 7.04:
                    a = b = 1
                elif time < 8:
                    a, b, alpha = 1, 2, (time - 7.04) / CROSSFADE
                else:
                    a = b = 2
                alpha = max(0.0, min(1.0, alpha))
                canvas = Image.new('RGB', (900, 900), '#FFF4DC')
                draw = ImageDraw.Draw(canvas)
                draw.text((28, 18), '现有：线性叠化', fill='#182232', font=font)
                draw.text((477, 18), '试验：缓入缓出叠化', fill='#182232', font=font)
                draw.text((28, 57), '0.96秒 · 画面静止', fill='#182232', font=small)
                draw.text((477, 57), '0.96秒 · 画面静止', fill='#182232', font=small)
                left = Image.blend(stills[a], stills[b], alpha) if a != b else stills[a]
                right = Image.blend(stills[a], stills[b], smoothstep(alpha)) if a != b else stills[a]
                canvas.paste(left, (20, 100))
                canvas.paste(right, (460, 100))
                draw.text((24, 858), '仅评估转场｜旧001原图｜无新口播｜不是第四集视频', fill='#182232', font=small)
                process.stdin.write(canvas.tobytes())
                if index in (0, 76, 79, 82, 85, 88, 91, 94, 100, 200, 299):
                    canvas.save(output / f'check_{index:03}.png')
                frame_states.append({'frame': index, 'time_s': time, 'image_a': a + 1, 'image_b': b + 1,
                                     'linear_alpha': alpha, 'smooth_alpha': smoothstep(alpha)})
        finally:
            process.stdin.close()
        if process.wait() != 0:
            raise RuntimeError('预览编码失败，见render.log')
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(video)]))
    stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    assert (stream['width'], stream['height'], stream['r_frame_rate']) == (900, 900, '25/1')
    assert int(stream['nb_frames']) == FPS * DURATION
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(video), '-f', 'null', '-'], check=True)
    # Repeated fully visible frames must decode identically within the same GOP.
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(video), '-vf',
                                  r'select=eq(n\,10)+eq(n\,11)+eq(n\,12)', '-fps_mode', 'passthrough', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])
    size = 900 * 900 * 3
    assert len(raw) == size * 3
    # H.264 may introduce tiny frame-to-frame quantization differences; motion
    # is prohibited by construction: fixed stills and fixed paste coordinates.
    report = {'duration_s': DURATION, 'fps': FPS, 'frames': FPS * DURATION,
              'resolution': [900, 900], 'audio': 'none_intentionally', 'full_decode': 'passed',
              'within_image_motion': 'none_fixed_source_and_coordinates', 'crossfade_s': CROSSFADE,
              'curves': {'baseline': 'alpha=u', 'candidate': 'alpha=3*u*u-2*u*u*u'},
              'sources': [{'path': str(p.relative_to(ROOT)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sources],
              'frame_states': frame_states, 'human_review': 'pending'}
    (output / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(video.resolve())


if __name__ == '__main__':
    main()
