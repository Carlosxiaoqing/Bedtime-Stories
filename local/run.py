"""Local entry point. All new deliverables go into Outputs/YYYY-MM-DD/run/."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT/'episodes/ep001/v005'
FONTS = ROOT/'local/fonts'
CST = timezone(timedelta(hours=8))

def doctor():
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError('Use Python 3.12 for the tested dependency set.')
    for line in (ROOT/'local/requirements-lock.txt').read_text().splitlines():
        if not line.strip() or line.startswith('#'): continue
        name, version = line.split('==')
        if importlib.metadata.version(name) != version:
            raise RuntimeError(f'Dependency mismatch: {name}; run local/setup.py')
    for tool in ('ffmpeg', 'ffprobe'):
        if not shutil.which(tool): raise RuntimeError(f'Install {tool} and add its bin directory to PATH.')
    for option, required in (('-filters', (' ass ', ' xfade ')), ('-encoders', ('libx264', ' aac '))):
        result = subprocess.run(['ffmpeg','-hide_banner', option], capture_output=True, text=True, check=True)
        info = result.stdout + result.stderr
        for item in required:
            if item not in info: raise RuntimeError(f'FFmpeg is missing {item.strip()}.')
    from PIL import Image, ImageFont
    for name, index in (('NotoSansCJKsc-Regular.otf',0), ('NotoSansCJKsc-Bold.otf',0), ('NotoSans-Regular.ttf',0)):
        ImageFont.truetype(str(FONTS/name), 48, index=index)
    verified=0
    for item in json.loads((EPISODE/'SHA256.json').read_text(encoding='utf-8')):
        p=EPISODE/item['file']
        # The large clean reference master is regenerable and omitted from the ZIP.
        if not p.exists() and item['file']=='output/ep001_clean.mp4': continue
        if hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:
            raise RuntimeError(f'Reference source changed: {p.relative_to(ROOT)}')
        verified+=1
    for p in (EPISODE/'images').glob('*.png'):
        with Image.open(p) as im: im.verify()
    print(f'READY: Python dependencies, FFmpeg encoders/filters, bundled fonts and {verified} reference files.', flush=True)

def inspect_video(path):
    data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))
    video=next(s for s in data['streams'] if s['codec_type']=='video')
    audio=next(s for s in data['streams'] if s['codec_type']=='audio')
    assert (video['width'],video['height'],video['r_frame_rate'],video['codec_name'])==(1080,1920,'25/1','h264')
    assert (audio['sample_rate'],audio['codec_name'])==('48000','aac')
    assert abs(float(data['format']['duration'])-99.88)<0.08
    subprocess.run(['ffmpeg','-v','error','-threads','2','-i',str(path),'-f','null','-'],check=True)
    return {'resolution':[1080,1920], 'fps':25, 'duration_s':float(data['format']['duration']), 'full_decode':'passed'}

def new_output_dir(now, command):
    day=ROOT/'Outputs'/now.astimezone(CST).strftime('%Y-%m-%d')
    day.mkdir(parents=True,exist_ok=True)
    output=day/f"ep001_v005_{command}_{now.astimezone(CST):%H%M%S}_{uuid.uuid4().hex[:6]}"
    output.mkdir()
    return output

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['doctor','render','export-reference'])
    args=parser.parse_args()
    doctor()
    if args.command=='doctor': return
    now=datetime.now(CST)
    output=new_output_dir(now,args.command)
    try:
        if args.command=='export-reference':
            shutil.copytree(EPISODE/'output',output,dirs_exist_ok=True)
        else:
            env=os.environ.copy()
            env.update(PYTHONUTF8="1", BEDTIME_OUTPUT_DIR=str(output), BEDTIME_FONT_DIR=str(FONTS),
                       CJK_FONT=str(FONTS/'NotoSansCJKsc-Regular.otf'),
                       CJK_BOLD_FONT=str(FONTS/'NotoSansCJKsc-Bold.otf'),
                       LATIN_FONT=str(FONTS/'NotoSans-Regular.ttf'))
            with (output/'render.log').open('w',encoding='utf-8') as log:
                result=subprocess.run([sys.executable,str(ROOT/'local/render_ep001.py')],env=env,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            if result.returncode:
                raise RuntimeError(f'Render failed. Read {output / "render.log"}')
        report=inspect_video(output/'ep001.mp4')
        if args.command=='render':
            for name in ('voice.wav','mix.wav'):
                assert hashlib.sha256((output/name).read_bytes()).digest()==hashlib.sha256((EPISODE/'output'/name).read_bytes()).digest(),name
            shutil.rmtree(output/'.render-cache')
        cues=json.loads((output/'subtitles.ruby.json').read_text(encoding='utf-8'))
        assert len(cues)==37
        report.update(command=args.command, generated_at=now.isoformat(), subtitles=37, human_review='pending', source='ep001/v005', output=str(output.relative_to(ROOT)))
        (output/'local-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(f'COMPLETE: {output}',flush=True)
    except Exception as exc:
        (output/'FAILED.txt').write_text(str(exc),encoding='utf-8')
        raise

if __name__=='__main__': main()
