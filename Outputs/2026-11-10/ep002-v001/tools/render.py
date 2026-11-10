"""Build the 001 deliverables from the new -35% narration and nine original illustrations."""
import json,math,re,subprocess,wave,hashlib,shutil,os
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps,ImageDraw,ImageFont
from pypinyin import pinyin,Style
E=Path(__file__).resolve().parents[1]; CACHE=E/'cache';CACHE.mkdir(exist_ok=True)
O=E/'output';O.mkdir(exist_ok=True)
T=json.loads((E/'narration-timeline.json').read_text());D=T['duration_s'];SR=48000
ROOT=E.parents[2]
CJK=os.environ.get('CJK_FONT',str(ROOT/'local/fonts/NotoSansCJKsc-Regular.otf'));BOLD=os.environ.get('CJK_BOLD_FONT',str(ROOT/'local/fonts/NotoSansCJKsc-Bold.otf'));LATIN=os.environ.get('LATIN_FONT',str(ROOT/'local/fonts/NotoSans-Regular.ttf'))
CJK_INDEX=2 if CJK.lower().endswith('.ttc') else 0
BOLD_INDEX=2 if BOLD.lower().endswith('.ttc') else 0
hfont=ImageFont.truetype(CJK,76,index=CJK_INDEX);pfont=ImageFont.truetype(LATIN,48)
def run(args):subprocess.run(args,check=True,cwd=E)
def ff(*args):run(['ffmpeg','-hide_banner','-loglevel','error','-y',*map(str,args)])
def savewav(p,a):
 with wave.open(str(p),'wb') as f:f.setparams((1,2,SR,0,'NONE','not compressed'));f.writeframes((a*32767).clip(-32768,32767).astype('<i2').tobytes())
# Quiet original procedural music, with no sampled third-party material.
with wave.open(str(E/'audio/voice.wav'),'rb') as f:voice=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').astype(np.float64)/32768
n=len(voice);music=np.zeros(n);chords=[[130.813,164.814,195.998],[110.,130.813,164.814],[87.307,110.,130.813],[97.999,123.471,146.832]]
for k,start in enumerate(np.arange(0,D,2.7)):
 length=min(int(5.5*SR),n-int(start*SR));t=np.arange(length)/SR;freq=chords[int(start//12)%4][k%3]
 env=(1-np.exp(-t/.35))*np.exp(-t/1.5)
 note=(np.sin(2*np.pi*freq*t)+.18*np.sin(4*np.pi*freq*t))*env
 a=int(start*SR);music[a:a+length]+=note
music*=.0045/np.sqrt(np.mean(music**2))
rng=np.random.default_rng(1);noise=rng.normal(size=n)
# Low-frequency air bed by spectral filtering.
freq=np.fft.rfftfreq(n,1/SR);spec=np.fft.rfft(noise);spec*=np.exp(-(freq/350)**4);noise=np.fft.irfft(spec,n);noise*=.00065/np.sqrt(np.mean(noise**2))
t=np.arange(n)/SR;fade=np.minimum(1,t/2)*np.minimum(1,(D-t)/5);music*=fade;noise*=fade
mix=voice+music+noise
assert np.max(np.abs(mix))<1
savewav(O/'music.wav',music);savewav(O/'ambience.wav',noise);savewav(O/'mix.wav',mix)
shutil.copyfile(E/'audio/voice.wav',O/'voice.wav')
# Faithful word-context corrections to automated pinyin.
fix={'长耳朵':['cháng','ěr','duo'],'眼睛':['yǎn','jing'],'哈欠':['hā','qian'],'星星':['xīng','xing'],'安安静静地':['ān','ān','jìng','jìng','de'],'安心地':['ān','xīn','de'],'一盏':['yì','zhǎn'],'一颗':['yì','kē'],'一伏':['yì','fú'],'朋友':['péng','you'],'舒服':['shū','fu'],'姿势':['zī','shi'],'下巴':['xià','ba'],'个':['ge'],'口袋':['kǒu','dai'],'一小':['yì','xiǎo'],'一枚':['yì','méi'],'一点':['yì','diǎn'],'一松':['yì','sōng'],'会儿':['huìr','r'],'舒舒服服地':['shū','shū','fú','fú','de'],'不用':['bú','yòng'],'那只':['nà','zhī']}
def tokens(text):
 py=[x[0] for x in pinyin(text,style=Style.TONE,errors=lambda x:list(x))];assert len(py)==len(text)
 for word,values in fix.items():
  for m in re.finditer(word,text):py[m.start():m.end()]=values
 return [{'hanzi':h,'pinyin':p if '\u4e00'<=h<='\u9fff' else ''} for h,p in zip(text,py)]
def width(x):return max(96,pfont.getlength(x['pinyin'])+16) if x['pinyin'] else 24

def astime(s):
 cs=round(s*100);return f'{cs//360000}:{cs//6000%60:02}:{cs//100%60:02}.{cs%100:02}'
def srtime(s):
 ms=round(s*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
header='''[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hanzi,Noto Sans CJK SC,76,&H00DCF4FF,&H00DCF4FF,&H00322218,&HFF000000,0,0,0,0,100,100,0,0,1,2,0,8,0,0,0,1
Style: Pinyin,Noto Sans,48,&H00DCF4FF,&H00DCF4FF,&H00322218,&HFF000000,0,0,0,0,100,100,0,0,1,1,0,8,0,0,0,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
events=[];cues=[];srt=[]
# Split at spoken punctuation and anchor cue changes in actual audio silence.
cue_items=[]
for item in T['lines']:
 parts=re.findall(r'[^，。：！？]+[，。：！？]?',item['text'])
 if len(parts)==1:
  cue_items.append(item);continue
 pcm=np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(E/item['source']),'-f','f32le','-ar','48000','-ac','1','-']),dtype='<f4')
 duration=item['end_s']-item['start_s'];a0=round(item['source_trim_start_s']*48000)
 pcm=pcm[a0:a0+round(duration*48000)];window=480
 energy=np.sqrt(np.mean(pcm[:len(pcm)//window*window].reshape(-1,window)**2,axis=1))
 mask=energy<.005;delta=np.diff(np.r_[False,mask,False].astype(int));left=np.flatnonzero(delta==1);right=np.flatnonzero(delta==-1)
 gaps=[(float(a)/100,float(b)/100) for a,b in zip(left,right) if b-a>=10 and a/100>.15 and b/100<duration-.12]
 weights=[len(re.findall(r'[\u4e00-\u9fff]',part)) for part in parts]
 boundaries=[0.];used=set()
 for k in range(1,len(parts)):
  expected=duration*sum(weights[:k])/sum(weights)
  candidates=[(abs((a+b)/2-expected),i,(a+b)/2) for i,(a,b) in enumerate(gaps) if i not in used and (a+b)/2>boundaries[-1]+.25 and (a+b)/2<duration-.25*(len(parts)-k)]
  if not candidates:raise RuntimeError(f'No acoustic pause for line {item["line"]}, break {k}')
  _,idx,t=min(candidates);used.add(idx);boundaries.append(t)
 boundaries.append(duration)
 for k,text in enumerate(parts):
  cue_items.append({**item,'text':text,'start_s':item['start_s']+boundaries[k],'end_s':item['start_s']+boundaries[k+1],'alignment':'original_audio_silence_at_spoken_punctuation'})
for cue_id,item in enumerate(cue_items,1):
 tok=tokens(item['text']);total=sum(map(width,tok))
 if total<=900:rows=[tok]
 else:
  candidates=[]
  for split in range(1,len(tok)):
   a=sum(map(width,tok[:split]));b=sum(map(width,tok[split:]))
   if max(a,b)<=900:candidates.append((abs(a-b),split))
  assert candidates,(item['text'],total)
  split=min(candidates)[1];rows=[tok[:split],tok[split:]]
 start=round((item['start_s']+.04)*25)/25;end=round((item['end_s']-.04)*25)/25
 a,b=astime(start),astime(end)
 top=1480 if len(rows)==1 else 1312;bottom=1668
 plate='{\\p1\\an7\\pos(0,0)\\bord0\\shad0\\c&H322218&\\alpha&H48&}'+f'm 96 {top} l 984 {top} b 997 {top} 1008 {top+11} 1008 {top+24} l 1008 {bottom-24} b 1008 {bottom-11} 997 {bottom} 984 {bottom} l 96 {bottom} b 83 {bottom} 72 {bottom-11} 72 {bottom-24} l 72 {top+24} b 72 {top+11} 83 {top} 96 {top}'
 events.append(f'Dialogue: 0,{a},{b},Hanzi,,0,0,0,,{plate}')
 for ri,row in enumerate(rows):
  py_y=1500 if len(rows)==1 else 1332+168*ri;hz_y=py_y+66
  x=540-sum(map(width,row))/2
  for tok1 in row:
   w=width(tok1);center=x+w/2
   if tok1['pinyin']:events.append(f"Dialogue: 1,{a},{b},Pinyin,,0,0,0,,{{\\an8\\pos({center:.1f},{py_y})}}{tok1['pinyin']}")
   events.append(f"Dialogue: 1,{a},{b},Hanzi,,0,0,0,,{{\\an8\\pos({center:.1f},{hz_y})}}{tok1['hanzi']}")
   x+=w
 cues.append({**item,'cue_id':cue_id,'subtitle_start_s':start,'subtitle_end_s':end,'tokens':tok,'rows':[''.join(t['hanzi'] for t in row) for row in rows]})
 srt.append(f"{cue_id}\n{srtime(start)} --> {srtime(end)}\n{item['text']}\n")
(O/'episode.ass').write_text(header+'\n'.join(events)+'\n');(O/'episode.srt').write_text('\n'.join(srt));(O/'subtitles.ruby.json').write_text(json.dumps(cues,ensure_ascii=False,indent=2))
# Cover typography uses the fixed template, never generated text.
cover=ImageOps.fit(Image.open(E/'images/shot_03.png').convert('RGB'),(1080,1920))
card=Image.new('RGBA',(1080,1920));draw=ImageDraw.Draw(card);draw.rounded_rectangle((108,1140,972,1580),radius=48,fill=(255,244,220,240));draw.text((540,1360),'月光口袋',font=ImageFont.truetype(BOLD,112,index=BOLD_INDEX),anchor='mm',fill='#182232');cover=Image.alpha_composite(cover.convert('RGBA'),card);cover.convert('RGB').save(O/'cover.png')
(O/'cover.svg').write_text('''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920"><image href="../images/shot_03.png" width="1080" height="1920" preserveAspectRatio="xMidYMid slice"/><rect x="108" y="1140" width="864" height="440" rx="48" fill="#FFF4DC" fill-opacity="0.94"/><g font-family="Noto Sans CJK SC" fill="#182232" text-anchor="middle"><text x="540" y="1360" dominant-baseline="central" font-size="112" font-weight="bold">月光口袋</text></g></svg>''')
# Shot cuts are the midpoints of real inter-sentence pauses, snapped to frame grid.
bounds=[0.]
for sid in range(1,9):
 prev=[x for x in T['lines'] if x['shot']==sid][-1];nxt=[x for x in T['lines'] if x['shot']==sid+1][0]
 bounds.append(round((prev['end_s']+nxt['start_s'])/2*25)/25)
bounds.append(D)
shots=[]
for i in range(9):
 duration=bounds[i+1]-bounds[i];source_duration=duration+(0.48 if i in (0,8) else .96);frames=round(source_duration*25)
 path=CACHE/f'shot_{i+1:02}.mp4'
 vf="scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,format=yuv420p"
 if not path.exists():ff('-loop','1','-framerate','25','-i',E/f'images/shot_{i+1:02}.png','-vf',vf,'-frames:v',frames,'-c:v','libx264','-crf','18','-preset','veryfast','-threads','2','-an',path)
 shots.append({'shot':i+1,'start_s':bounds[i],'end_s':bounds[i+1],'duration_s':duration,'source_duration_s':source_duration,'image':f'images/shot_{i+1:02}.png','motion':'fixed'})
 print('rendered shot',i+1,flush=True)
(O/'timeline.json').write_text(json.dumps({'duration_s':D,'fps':25,'crossfade_s':.96,'shots':shots,'narration':T['lines']},ensure_ascii=False,indent=2))
inputs=[]
for i in range(9):inputs+=['-i',str(CACHE/f'shot_{i+1:02}.mp4')]
filters=[]
for i in range(9):filters.append(f'[{i}:v]fps=25[v{i}]')
last='v0'
for i in range(1,9):
 name=f'x{i}';filters.append(f'[{last}][v{i}]xfade=transition=fade:duration=0.96:offset={bounds[i]-.48:.2f}[{name}]');last=name
filters.append(f'[{last}]fade=t=out:st={D-4}:d=4:color=0x182232,format=yuv420p[final]')
clean=O/'ep002_clean.mp4'
ff(*inputs,'-i',O/'mix.wav','-filter_complex_threads','1','-filter_complex',';'.join(filters),'-map','[final]','-map','9:a','-t',D,'-r','25','-c:v','libx264','-crf','20','-preset','veryfast','-threads','2','-c:a','aac','-b:a','128k','-ar','48000','-movflags','+faststart',clean)
print('clean master ready',flush=True)
ff('-i',clean,'-vf','ass=output/episode.ass:fontsdir=../../../local/fonts','-c:v','libx264','-crf','20','-preset','veryfast','-threads','2','-c:a','copy','-movflags','+faststart',O/'ep002.mp4')
shutil.copyfile(E/'发布文案.md',O/'发布文案.md')
shutil.rmtree(CACHE)
print('FINAL_VIDEO_READY',flush=True)
