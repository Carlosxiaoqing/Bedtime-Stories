"""Build the 001 deliverables from the approved narration and nine original illustrations."""
import json,math,re,subprocess,wave,hashlib,shutil,os
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps,ImageDraw,ImageFont
from pypinyin import pinyin,Style
E=Path(__file__).resolve().parents[1]; CACHE=Path('/tmp/ep001-render');CACHE.mkdir(exist_ok=True)
O=E/'output';O.mkdir(exist_ok=True)
T=json.loads((E/'narration-timeline.json').read_text());D=T['duration_s'];SR=48000
CJK=os.environ.get('CJK_FONT','/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc');BOLD=os.environ.get('CJK_BOLD_FONT','/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc');LATIN=os.environ.get('LATIN_FONT','/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf')
hfont=ImageFont.truetype(CJK,64,index=2);pfont=ImageFont.truetype(LATIN,30)
def run(args):subprocess.run(args,check=True)
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
fix={'长耳朵':['cháng','ěr','duo'],'眼睛':['yǎn','jing'],'哈欠':['hā','qian'],'星星':['xīng','xing'],'安安静静地':['ān','ān','jìng','jìng','de'],'安心地':['ān','xīn','de'],'一盏':['yì','zhǎn'],'一颗':['yì','kē'],'一伏':['yì','fú'],'朋友':['péng','you'],'舒服':['shū','fu'],'姿势':['zī','shi'],'下巴':['xià','ba'],'个':['ge']}
def tokens(text):
 py=[x[0] for x in pinyin(text,style=Style.TONE,errors=lambda x:list(x))];assert len(py)==len(text)
 for word,values in fix.items():
  for m in re.finditer(word,text):py[m.start():m.end()]=values
 return [{'hanzi':h,'pinyin':p if '\u4e00'<=h<='\u9fff' else ''} for h,p in zip(text,py)]
def width(x):return max(88,pfont.getlength(x['pinyin'])+16) if x['pinyin'] else 24

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
Style: Hanzi,Noto Sans CJK SC,64,&H00DCF4FF,&H00DCF4FF,&H00322218,&HFF000000,0,0,0,0,100,100,0,0,1,2,0,8,0,0,0,1
Style: Pinyin,Noto Sans,30,&H00DCF4FF,&H00DCF4FF,&H00322218,&HFF000000,0,0,0,0,100,100,0,0,1,1,0,8,0,0,0,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
events=[];cues=[];srt=[]
for item in T['lines']:
 tok=tokens(item['text']);total=sum(map(width,tok))
 if total<=840:rows=[tok]
 else:
  candidates=[]
  for split in range(1,len(tok)):
   a=sum(map(width,tok[:split]));b=sum(map(width,tok[split:]));
   if max(a,b)<=840:
    cost=abs(a-b)-(1000 if tok[split-1]['hanzi'] in '，。：' else 0)
    candidates.append((cost,split))
  assert candidates,(item['text'],total)
  split=min(candidates)[1];rows=[tok[:split],tok[split:]]
 start=round((item['start_s']+.04)*25)/25;end=round((item['end_s']-.04)*25)/25
 a,b=astime(start),astime(end)
 top=1490 if len(rows)==1 else 1378;bottom=1642
 plate='{\\p1\\an7\\pos(0,0)\\bord0\\shad0\\c&H322218&\\alpha&H48&}'+f'm 120 {top} l 960 {top} b 973 {top} 984 {top+11} 984 {top+24} l 984 {bottom-24} b 984 {bottom-11} 973 {bottom} 960 {bottom} l 120 {bottom} b 107 {bottom} 96 {bottom-11} 96 {bottom-24} l 96 {top+24} b 96 {top+11} 107 {top} 120 {top}'
 events.append(f'Dialogue: 0,{a},{b},Hanzi,,0,0,0,,{plate}')
 for ri,row in enumerate(rows):
  py_y=1510 if len(rows)==1 else 1398+112*ri;hz_y=py_y+44
  x=540-sum(map(width,row))/2
  for tok1 in row:
   w=width(tok1);center=x+w/2
   if tok1['pinyin']:events.append(f"Dialogue: 1,{a},{b},Pinyin,,0,0,0,,{{\\an8\\pos({center:.1f},{py_y})}}{tok1['pinyin']}")
   events.append(f"Dialogue: 1,{a},{b},Hanzi,,0,0,0,,{{\\an8\\pos({center:.1f},{hz_y})}}{tok1['hanzi']}")
   x+=w
 cues.append({**item,'subtitle_start_s':start,'subtitle_end_s':end,'tokens':tok,'rows':[''.join(t['hanzi'] for t in row) for row in rows]})
 srt.append(f"{item['line']}\n{srtime(start)} --> {srtime(end)}\n{item['text']}\n")
(O/'episode.ass').write_text(header+'\n'.join(events)+'\n');(O/'episode.srt').write_text('\n'.join(srt));(O/'subtitles.ruby.json').write_text(json.dumps(cues,ensure_ascii=False,indent=2))
# Cover typography uses the fixed template, never generated text.
cover=ImageOps.fit(Image.open(E/'images/shot_01.png').convert('RGB'),(1080,1920))
card=Image.new('RGBA',(1080,1920));draw=ImageDraw.Draw(card);draw.rounded_rectangle((108,1140,972,1580),radius=48,fill=(255,244,220,240));draw.text((540,1180),'晚安绘本馆',font=ImageFont.truetype(CJK,36,index=2),anchor='mt',fill='#182232');draw.text((540,1320),'晚安星光',font=ImageFont.truetype(BOLD,112,index=2),anchor='mt',fill='#182232');cover=Image.alpha_composite(cover.convert('RGBA'),card);cover.convert('RGB').save(O/'cover.png')
(O/'cover.svg').write_text('''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920"><image href="../images/shot_01.png" width="1080" height="1920" preserveAspectRatio="xMidYMid slice"/><rect x="108" y="1140" width="864" height="440" rx="48" fill="#FFF4DC" fill-opacity="0.94"/><g font-family="Noto Sans CJK SC" fill="#182232" text-anchor="middle"><text x="540" y="1180" dominant-baseline="text-before-edge" font-size="36">晚安绘本馆</text><text x="540" y="1320" dominant-baseline="text-before-edge" font-size="112" font-weight="bold">晚安星光</text></g></svg>''')
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
 z=f'1+0.03*on/{frames-1}' if i%2==0 else f'1.03-0.03*on/{frames-1}'
 vf=f"scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,zoompan=z='{z}':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':d=1:s=1080x1920:fps=25,setsar=1,format=yuv420p"
 if not path.exists():ff('-loop','1','-framerate','25','-i',E/f'images/shot_{i+1:02}.png','-vf',vf,'-frames:v',frames,'-c:v','libx264','-crf','18','-preset','veryfast','-threads','2','-an',path)
 shots.append({'shot':i+1,'start_s':bounds[i],'end_s':bounds[i+1],'duration_s':duration,'source_duration_s':source_duration,'image':f'images/shot_{i+1:02}.png'})
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
clean=O/'ep001_clean.mp4'
ff(*inputs,'-i',O/'mix.wav','-filter_complex_threads','1','-filter_complex',';'.join(filters),'-map','[final]','-map','9:a','-t',D,'-r','25','-c:v','libx264','-crf','20','-preset','veryfast','-threads','2','-c:a','aac','-b:a','128k','-ar','48000','-movflags','+faststart',clean)
print('clean master ready',flush=True)
ff('-i',clean,'-vf',f'ass={O}/episode.ass','-c:v','libx264','-crf','20','-preset','veryfast','-threads','2','-c:a','copy','-movflags','+faststart',O/'ep001.mp4')
shutil.copyfile(E/'发布文案.md',O/'发布文案.md')
print('FINAL_VIDEO_READY',flush=True)
