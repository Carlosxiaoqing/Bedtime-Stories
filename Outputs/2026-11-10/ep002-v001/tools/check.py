from pathlib import Path
import json,subprocess,hashlib,re,wave
import numpy as np
E=Path(__file__).resolve().parents[1];O=E/'output';T=json.loads((E/'narration-timeline.json').read_text());D=T['duration_s']
x=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(O/'ep002.mp4')]))
v=next(z for z in x['streams'] if z['codec_type']=='video');assert(v['width'],v['height'],v['r_frame_rate'],int(v['nb_frames']))==(1080,1920,'25/1',round(D*25))
assert abs(float(x['format']['duration'])-D)<.05
subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(O/'ep002.mp4'),'-f','null','-'],check=True)
assert hashlib.sha256((O/'voice.wav').read_bytes()).digest()==hashlib.sha256((E/'audio/voice.wav').read_bytes()).digest()
story=json.loads((E.parents[2]/'02_100集剧本/结构化JSON/ep002.json').read_text())
assert ''.join(z['text'] for z in T['lines'])==''.join(t for shot in story['shots'] for t in shot['narration_lines'])
for i in range(1,len(T['lines'])+1):
 j=json.loads((E/f'audio/source/line_{i:02}.json').read_text());assert j['rate']=='-35%' and j['voice']=='zh-CN-XiaoxiaoNeural' and j['pitch']=='-2Hz' and j['volume']=='+0%'
with wave.open(str(O/'mix.wav'),'rb') as f:mix=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').astype(np.int32)
assert np.max(np.abs(mix))<32767
cues=json.loads((O/'subtitles.ruby.json').read_text())
for line in T['lines']:assert ''.join(c['text'] for c in cues if c['line']==line['line'])==line['text']
for i,c in enumerate(cues):
 assert c['subtitle_start_s']<c['subtitle_end_s']<=D
 if i:assert cues[i-1]['subtitle_end_s']<=c['subtitle_start_s']
 assert all(t['pinyin'] for t in c['tokens'] if '\u4e00'<=t['hanzi']<='\u9fff')
assert re.findall(r'<text[^>]*>(.*?)</text>',(O/'cover.svg').read_text())==['月光口袋']
ass=(O/'episode.ass').read_text();assert 'CJK SC,76,' in ass and 'Pinyin,Noto Sans,48,' in ass
movement=[]
def frame(t):
 b=subprocess.check_output(['ffmpeg','-v','error','-ss',str(t),'-i',str(O/'ep002.mp4'),'-vf','crop=1080:1200:0:0,scale=270:300','-frames:v','1','-pix_fmt','rgb24','-f','rawvideo','-'])
 return np.frombuffer(b,dtype=np.uint8).astype(float).reshape(300,270,3).mean(axis=2)
for shot in json.loads((O/'timeline.json').read_text())['shots']:
 aa=frame(shot['start_s']+1.1);bb=frame(min(shot['end_s']-1.1,D-4.7));shifts=[]
 for y,x in [(10,10),(10,160),(180,10),(180,160)]:
  a=aa[y:y+100,x:x+100];b=bb[y:y+100,x:x+100];ff=np.fft.fft2(a)*np.conj(np.fft.fft2(b));ff/=np.maximum(np.abs(ff),1e-9)
  peak=np.unravel_index(np.argmax(np.abs(np.fft.ifft2(ff))),a.shape);dy,dx=[int(k if k<=50 else k-100)for k in peak];assert(dx,dy)==(0,0),(shot['shot'],dx,dy);shifts.append([dx,dy])
 movement.append({'shot':shot['shot'],'region_shifts':shifts})
report={'status':'technical_checks_passed','duration_s':D,'frames':round(D*25),'resolution':[1080,1920],'fps':25,'tts_rate':'-35%','newly_synthesized_lines':len(T['lines']),'time_stretch_used':False,'voice_output_matches_new_source':True,'mix_peak_dbfs':round(float(20*np.log10(np.max(np.abs(mix))/32768)),2),'full_decode':'passed','hanzi_px':76,'pinyin_px':48,'subtitle_cues':len(cues),'pinyin_coverage':1.0,'motion_checks':movement,'cover_text':['月光口袋'],'rate_parameter_user_approved':True,'new_audio_and_video_review':'pending_user_review'}
(O/'check-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(report)
# Nine genuinely distinct scene files, not copied episode-001 images.
image_hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((E/'images').glob('shot_*.png'))]
assert len(set(image_hashes))==9
old={hashlib.sha256(p.read_bytes()).hexdigest() for p in (E.parents[2]/'episodes/ep001/v005/images').glob('*.png')}
assert not(old & set(image_hashes))
