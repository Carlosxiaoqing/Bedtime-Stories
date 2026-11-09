"""Generate episode 001 narration with Edge TTS 7.3.1 and managed proxy trust."""
import asyncio, hashlib, json, math, os, subprocess
from pathlib import Path
import numpy as np
import edge_tts
import edge_tts.communicate as communicate

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[2]
CONFIG = {'voice':'zh-CN-XiaoxiaoNeural','rate':'-35%','pitch':'-2Hz','volume':'+0%','edge_tts':'7.3.1'}

def ffmpeg(*args):
    return subprocess.check_output(['ffmpeg','-hide_banner','-loglevel','error',*args])

async def main():
    # Keep certificate verification enabled and add the environment-provided CA.
    if os.environ.get('SSL_CERT_FILE'):
        communicate._SSL_CTX.load_verify_locations(cafile=os.environ['SSL_CERT_FILE'])
    proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    script = json.loads((ROOT/'02_100集剧本/结构化JSON/ep001.json').read_text())
    source = EP/'audio/source'
    source.mkdir(parents=True,exist_ok=True)
    timeline=[]
    chunks=[np.zeros(48000,dtype=np.float32)]
    cursor=1.0
    line_no=0
    for shot in script['shots']:
        for text,pause in zip(shot['narration_lines'],shot['pause_after_s']):
            line_no+=1
            mp3=source/f'line_{line_no:02}.mp3'
            meta=mp3.with_suffix('.json')
            fingerprint=hashlib.sha256(json.dumps({'text':text,**CONFIG},ensure_ascii=False,sort_keys=True).encode()).hexdigest()
            if not (mp3.exists() and mp3.stat().st_size and meta.exists() and json.loads(meta.read_text()).get('fingerprint')==fingerprint):
                boundaries=[]
                tmp=mp3.with_suffix('.partial')
                with tmp.open('wb') as output:
                    async for msg in edge_tts.Communicate(text,proxy=proxy,**{k:CONFIG[k] for k in ['voice','rate','pitch','volume']}).stream():
                        if msg['type']=='audio': output.write(msg['data'])
                        else: boundaries.append(msg)
                if not tmp.stat().st_size: raise RuntimeError('empty audio')
                tmp.replace(mp3)
                meta.write_text(json.dumps({'text':text,**CONFIG,'fingerprint':fingerprint,'boundaries':boundaries},ensure_ascii=False,indent=2))
            wave=np.frombuffer(ffmpeg('-i',str(mp3),'-ac','1','-ar','48000','-f','f32le','-'),dtype='<f4').copy()
            peak=float(np.max(np.abs(wave)))
            audible=np.flatnonzero(np.abs(wave)>max(.0025,peak*.008))
            if not audible.size: raise RuntimeError(f'silent line {line_no}')
            start=max(0,int(audible[0])-5280)
            end=min(wave.size,int(audible[-1])+7680)
            wave=wave[start:end]
            active=wave[np.abs(wave)>np.max(np.abs(wave))*.03]
            rms=float(np.sqrt(np.mean(active**2)))
            wave*=min(.105/rms,.72/float(np.max(np.abs(wave))))
            duration=wave.size/48000
            timeline.append({'line':line_no,'shot':shot['id'],'text':text,'start_s':cursor,'end_s':cursor+duration,'pause_after_s':pause,'source':str(mp3.relative_to(EP)),'source_trim_start_s':start/48000})
            chunks.extend([wave,np.zeros(round(pause*48000),dtype=np.float32)])
            cursor+=duration+pause
            print(f'line {line_no}: {duration:.2f}s',flush=True)
    total=math.ceil(cursor*25)/25
    chunks.append(np.zeros(max(0,round((total-cursor)*48000)),dtype=np.float32))
    raw=EP/'audio/voice_raw.f32'
    np.concatenate(chunks).astype('<f4').tofile(raw)
    ffmpeg('-y','-f','f32le','-ar','48000','-ac','1','-i',str(raw),'-af','highpass=f=65,equalizer=f=3200:t=q:w=0.8:g=-2','-c:a','pcm_s16le',str(EP/'audio/voice.wav'))
    raw.unlink()
    (EP/'narration-timeline.json').write_text(json.dumps({'duration_s':total,'fps':25,'lines':timeline},ensure_ascii=False,indent=2))
    print(f'COMPLETE {len(timeline)} lines; {total:.2f}s',flush=True)

if __name__=='__main__':asyncio.run(main())
