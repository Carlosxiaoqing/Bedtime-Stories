"""Build a reproducible-content migration archive, excluding historical caches."""
import hashlib
import json
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'downloads/Bedtime-Stories-local.zip'

def include(p):
    rel=p.relative_to(ROOT)
    allowed={'01_制作手册','02_100集剧本','03_素材与参数','docs','episodes','local','AGENTS.md','README.md','HANDOFF.md','CHANNEL_MASTER.md','本地开始.md','.gitignore'}
    if rel.parts[0] not in allowed: return False
    if p.name.startswith('.env') or p.name=='.DS_Store': return False
    if rel.parts[0] in {'.git','.venv','Outputs','downloads'}: return False
    if rel.as_posix()=='episodes/ep001/v005/output/ep001_clean.mp4': return False
    if '__pycache__' in rel.parts or p.suffix=='.pyc': return False
    if len(rel.parts)>=3 and rel.parts[:2]==('episodes','ep001') and rel.parts[2] in {'v003','v004'}: return False
    if rel.parts[:2]==('03_素材与参数','离线依赖_windows_python310'): return False
    return p.is_file()

def main():
    files=sorted(p for p in ROOT.rglob('*') if include(p))
    manifest=[]
    DEST.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(DEST,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:
            relative=p.relative_to(ROOT).as_posix()
            z.write(p,'Bedtime-Stories-local/'+relative)
            manifest.append({'file':relative,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
        z.writestr('Bedtime-Stories-local/PACKAGE-MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    if DEST.stat().st_size>=100*1024*1024:
        raise RuntimeError('ZIP exceeds GitHub regular-file limit.')
    digest=hashlib.sha256(DEST.read_bytes()).hexdigest()
    DEST.with_suffix('.zip.sha256').write_text(digest+'  '+DEST.name+'\n')
    print(f'{DEST}: {DEST.stat().st_size/1024/1024:.1f} MiB, {len(files)} files; SHA256 {digest}')
if __name__=='__main__': main()
