#!/usr/bin/env python3
"""Synthesize adopted long narration, preserving every sentence and word boundary."""
import argparse
import asyncio
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess

import edge_tts
import edge_tts.communicate as communicate
import numpy as np

CONFIG = {'voice': 'zh-CN-XiaoxiaoNeural', 'rate': '-35%', 'pitch': '-2Hz', 'volume': '+0%'}
SR = 48000


def ff(*args):
    return subprocess.check_output(['ffmpeg', '-hide_banner', '-loglevel', 'error', *map(str, args)])


async def main_async(args):
    output = args.output_dir.resolve()
    units = json.loads((output / 'narration-units.json').read_text())
    if args.sample_only:
        units = units[:1]
    source = output / 'audio/source'
    source.mkdir(parents=True, exist_ok=True)
    if os.environ.get('SSL_CERT_FILE'):
        communicate._SSL_CTX.load_verify_locations(cafile=os.environ['SSL_CERT_FILE'])
    proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    chunks = [np.zeros(SR, dtype=np.float32)]
    timeline, cursor = [], 1.0
    for unit in units:
        mp3 = source / f"{unit['id']}.mp3"
        meta = mp3.with_suffix('.json')
        fingerprint = hashlib.sha256(json.dumps({'text': unit['text'], **CONFIG, 'boundary': 'WordBoundary'}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        cached = mp3.exists() and mp3.stat().st_size and meta.exists() and json.loads(meta.read_text()).get('fingerprint') == fingerprint
        if not cached:
            for attempt in range(3):
                temporary = mp3.with_suffix('.partial')
                try:
                    boundaries = []
                    with temporary.open('wb') as f:
                        speech = edge_tts.Communicate(unit['text'], **CONFIG, proxy=proxy, boundary='WordBoundary', connect_timeout=10, receive_timeout=45)
                        async for message in speech.stream():
                            if message['type'] == 'audio':
                                f.write(message['data'])
                            else:
                                boundaries.append(message)
                    if temporary.stat().st_size == 0:
                        raise RuntimeError('empty TTS response')
                    temporary.replace(mp3)
                    meta.write_text(json.dumps({'text': unit['text'], **CONFIG, 'boundary': 'WordBoundary', 'fingerprint': fingerprint, 'boundaries': boundaries}, ensure_ascii=False, indent=2) + '\n')
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    await asyncio.sleep(attempt + 1)
        metadata = json.loads(meta.read_text())
        raw = np.frombuffer(ff('-i', mp3, '-ac', 1, '-ar', SR, '-f', 'f32le', '-'), dtype='<f4').copy()
        peak = float(np.max(np.abs(raw)))
        audible = np.flatnonzero(np.abs(raw) > max(.0025, peak * .008))
        if not audible.size:
            raise RuntimeError(f"silent unit {unit['id']}")
        start = max(0, int(audible[0]) - 5280)
        end = min(raw.size, int(audible[-1]) + 7680)
        samples = raw[start:end]
        active = samples[np.abs(samples) > np.max(np.abs(samples)) * .03]
        rms = float(np.sqrt(np.mean(active ** 2)))
        samples *= min(.105 / rms, .72 / float(np.max(np.abs(samples))))
        duration = samples.size / SR
        words = []
        for boundary in metadata['boundaries']:
            if boundary['type'] != 'WordBoundary':
                continue
            a = boundary['offset'] / 1e7 - start / SR
            b = a + boundary['duration'] / 1e7
            words.append({'text': boundary['text'], 'start_s': max(cursor, cursor + a), 'end_s': min(cursor + duration, cursor + b)})
        timeline.append({**unit, 'start_s': cursor, 'end_s': cursor + duration,
                         'source': str(mp3.relative_to(output)), 'source_trim_start_s': start / SR,
                         'word_boundaries': words, 'source_peak': peak, 'normalized_active_rms': .105})
        pause = unit['pause_after_s']
        chunks.extend([samples, np.zeros(round(pause * SR), dtype=np.float32)])
        cursor += duration + pause
        print(f"{unit['id']}: {duration:.2f}s; {len(words)} word boundaries; cached={bool(cached)}", flush=True)
    total = math.ceil(cursor * 25) / 25
    chunks.append(np.zeros(max(0, round((total - cursor) * SR)), dtype=np.float32))
    raw_path = output / 'audio/voice_raw.f32'
    np.concatenate(chunks).astype('<f4').tofile(raw_path)
    name = 'sample' if args.sample_only else 'voice'
    ff('-y', '-f', 'f32le', '-ar', SR, '-ac', 1, '-i', raw_path,
       '-af', 'highpass=f=65,equalizer=f=3200:t=q:w=0.8:g=-2', '-c:a', 'pcm_s16le', output / f'audio/{name}.wav')
    raw_path.unlink()
    (output / f'{name}-timeline.json').write_text(json.dumps({'duration_s': total, 'fps': 25, 'sample_rate': SR, 'voice': CONFIG, 'units': timeline, 'is_sample': args.sample_only}, ensure_ascii=False, indent=2) + '\n')
    print(f'COMPLETE {len(timeline)} units, {total:.2f}s', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--sample-only', action='store_true')
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == '__main__':
    main()
