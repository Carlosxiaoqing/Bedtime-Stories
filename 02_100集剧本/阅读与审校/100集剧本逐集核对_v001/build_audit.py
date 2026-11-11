"""只读100集源稿，生成审查快照与阅读材料；不改剧本、不生成媒体。"""
from pathlib import Path
from collections import Counter
import base64
import hashlib
import html
import json
import re
import shutil
import zipfile

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
SOURCE = ROOT / '02_100集剧本'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
def table(value):
    return str(value).replace('|', '／').replace('\n', ' ')

note_lines = (OUT / '逐集编辑意见.txt').read_text().splitlines()
note_keys = note_lines[0].split('|')
notes = [dict(zip(note_keys, line.split('|'), strict=True)) for line in note_lines[1:] if line]
assert len(notes) == 100
assert [int(n['集数']) for n in notes] == list(range(1, 101))
episodes = []
checks = []
manifest = {}
snapshot = OUT / '原稿快照'
snapshot.mkdir(exist_ok=True)
files = sorted(SOURCE.rglob('*.json')) + sorted(SOURCE.rglob('*.md'))
files += [ROOT / 'CHANNEL_MASTER.md', ROOT / 'AGENTS.md', ROOT / '01_制作手册/制作总手册.md']
files += sorted((ROOT / '03_素材与参数').glob('*.json'))
files += sorted((ROOT / 'docs/production').rglob('*.md'))
for path in files:
    rel = path.relative_to(ROOT)
    dest = snapshot / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Re-runs keep the original start-of-audit snapshot intact.
    if not dest.exists():
        shutil.copy2(path, dest)
    manifest[str(rel)] = {'snapshot_sha256': sha(dest), 'current_sha256': sha(path)}

for i, path in enumerate(sorted((SOURCE / '结构化JSON').glob('ep*.json'))):
    d = json.loads(path.read_text())
    number = d['episode']
    assert number == i + 1 and len(d['shots']) == 9
    md_files = list((SOURCE / '单集Markdown').glob(f'第{number:03d}集_*.md'))
    assert len(md_files) == 1
    md = md_files[0].read_text()
    blocks = re.findall(r'\*\*口播\*\*\s*\n(.*?)(?=\*\*绘图提示词\*\*)', md, re.S)
    expected = [re.sub(r'\s', '', ''.join(s['narration_lines'])) for s in d['shots']]
    actual = [re.sub(r'\s', '', s) for s in blocks]
    assert actual == expected, number
    checks.append({'episode': number, 'shots': 9, 'json_markdown_narration_equal': True})
    body = ''.join(l for s in d['shots'] for l in s['narration_lines'])
    episodes.append({
        'episode': number, 'id': d['id'], 'title': d['title'], 'theme': d['theme'],
        'setting': d['setting'], 'guest': d['guest'], 'shots': d['shots'],
        'source_json': str(path.relative_to(ROOT)),
        'source_markdown': str(md_files[0].relative_to(ROOT)),
        'source_json_sha256': sha(path), 'source_markdown_sha256': sha(md_files[0]),
        'original_narration': body, 'editorial_review': notes[i],
        'user_review_status': '待逐集核对；建议不等于已批准改稿',
    })

patterns = {
    '口播含床枕或被褥': r'床|枕|毛毯|被窝|被子|被角',
    '口播含窗': r'窗',
    '口播含月亮月光月牙月色或弯月': r'月亮|月光|月牙|月色|弯月',
    '口播含星字': r'星',
}
stats = {}
for name, pattern in patterns.items():
    ids = [d['episode'] for d in episodes if re.search(pattern, d['original_narration'])]
    stats[name] = {'count': len(ids), 'episodes': ids, 'pattern': pattern, 'scope': '仅JSON口播，不含标题、主题、镜名、camera或提示词'}
stats['末镜相同camera'] = {'count': len(episodes), 'text': episodes[0]['shots'][-1]['camera']}
assert all(d['shots'][-1]['camera'] == stats['末镜相同camera']['text'] for d in episodes)
camera_counts = Counter(s['camera'] for d in episodes for s in d['shots'])
stats['camera模板'] = dict(camera_counts)
stats['处理建议计数'] = dict(Counter(n['建议处理'] for n in notes))
stats['逐镜提示词等于镜名加camera模板'] = sum(
    s['image_prompt'] == f"本镜画面：{s['title']}。镜位：{s['camera']}。"
    for d in episodes for s in d['shots']
)
dump(OUT / '审查统计.json', stats)
dump(OUT / '100集审查数据.json', episodes)
dump(OUT / '原稿快照SHA256.json', manifest)

header = '''# 100集原稿与逐集核对意见

日期：2026-11-11（北京时间）。范围：001–100集，100份JSON、100份Markdown、900个分镜。

下列口播、镜名、镜位和绘图提示词从JSON逐项导出；编辑意见单独列出，**没有写回源剧本，也没有批准任何改编方案**。全部900段口播与现有Markdown核对一致。原稿中的运动字段属于旧建议，执行时仍服从当前固定画面要求。

核对方式：每次确定一集的故事核心、主场景、角色目标、小事件与结尾，再决定保留、修改或换题。相近集数表示本次编辑识别的可比对象，不是机器相似度评分。所有新地点、任务和角色安排均为讨论候选，未制作配音或图片。

'''
parts = [header]
index_rows = ['| 集数 | 原标题 | 原场景 | 编辑处理建议 |', '| --- | --- | --- | --- |']
full_html = []
for d in episodes:
    n = d['editorial_review']
    number = f"{d['episode']:03d}"
    index_rows.append(f"| [{number}](100集原稿与逐集核对意见.md#第{number}集) | {table(d['title'])} | {table(d['setting'])} | {n['建议处理']} |")
    parts += [f"## 第{number}集\n", f"**原题：{d['title']}**\n", f"原主题：{d['theme']}。原场景：{d['setting']}。原客串：{d['guest']}。\n",
              f"**处理建议：{n['建议处理']}（待用户逐集核对）。**\n",
              f"问题与证据：{n['原稿问题与证据']}\n",
              f"可讨论的方向：{n['待核对的改编方向']}\n",
              f"优先对照：{n['相近集数']}。\n",
              f"来源：[JSON快照](原稿快照/{d['source_json']}) · [Markdown快照](原稿快照/{d['source_markdown']})。\n",
              '### 原稿九镜\n']
    for s in d['shots']:
        parts += [f"#### 镜{s['id']:02d}｜{s['title']}\n", '\n'.join(s['narration_lines']) + '\n',
                  f"镜位：{s['camera']}\n", f"原绘图提示词：{s['image_prompt']}\n"]
    parts += ['逐集决定：待核对。改稿版本：未建立。声音／图片／成片制作：本次未启动。\n', '---\n']
    esc = html.escape
    shots_html = ''.join(f'<section><h3>镜{s["id"]:02d} · {esc(s["title"])}</h3><p>{esc(" ".join(s["narration_lines"]))}</p><p class="meta">镜位：{esc(s["camera"])}</p><p class="meta">原提示词：{esc(s["image_prompt"])}</p></section>' for s in d['shots'])
    full_html.append(f'<details id="ep{number}"><summary>第{number}集 · {esc(d["title"])}　<span>{esc(n["建议处理"])}</span></summary><article><p>原场景：{esc(d["setting"])}｜原主题：{esc(d["theme"])}</p><p><strong>原稿问题：</strong>{esc(n["原稿问题与证据"])}</p><p><strong>讨论方向，未批准：</strong>{esc(n["待核对的改编方向"])}</p><p>相近集数：{esc(n["相近集数"])}</p>{shots_html}<p class="meta">待用户逐集核对；源JSON与原媒体未改。</p></article></details>')
(OUT / '100集原稿与逐集核对意见.md').write_text('\n'.join(parts))
(OUT / '100集核对目录.md').write_text('# 100集核对目录\n\n原稿完整保留；下表为编辑建议，尚未逐集确认。点击集数查看九镜全文。\n\n' + '\n'.join(index_rows) + '\n')

# A static reading document. Native details provide collapsing without scripts or network requests.
css = '''body{margin:0;background:#f5f3ee;color:#202b28;font:17px/1.85 system-ui,-apple-system,sans-serif}main{max-width:940px;padding:28px 20px 80px;margin:auto}h1{font-size:28px;line-height:1.5}h2{font-size:22px}h3{font-size:18px;margin-bottom:8px}a{color:#276c59}summary{padding:16px 0;cursor:pointer;font-weight:600;overflow-wrap:anywhere}summary span{font-size:14px;color:#68583a}details{border-bottom:1px solid #d7d9d2}article{padding:0 0 24px}section{border-left:3px solid #c6d2c8;padding-left:16px;margin-top:22px}p{margin:10px 0}.meta{color:#52625a;font-size:14px}nav{display:flex;flex-wrap:wrap;gap:6px}nav a{padding:3px 8px;text-decoration:none;border:1px solid #ccd3ca;border-radius:4px}img{max-width:100%;height:auto}@media(max-width:480px){main{padding:18px 14px}h1{font-size:23px}}'''
nav = ''.join(f'<a href="#ep{d["episode"]:03d}">{d["episode"]:03d}</a>' for d in episodes)
page = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>100集剧本逐集核对</title><style>{css}</style><main><h1>100集剧本逐集核对</h1><p>2026-11-11 · 原稿100集 / 分镜900个 · 待用户逐集确认</p><p>100集均出现床、枕头或被褥；100个末镜使用同一卧室安睡镜位。口播中的月亮类词出现于26集，星字出现于6集，窗出现于70集。主要问题是空间、事件和收尾模板重复。</p><p>每集展开后可看原九镜、具体问题和讨论候选。候选没有写回剧本；未开展新媒体制作。</p><p><a href="核对说明与总诊断.md">总诊断</a> · <a href="100集原稿与逐集核对意见.md">完整Markdown</a> · <a href="100集核对目录.md">核对目录</a> · <a href="100集原始剧本快照.zip">原始稿库</a></p><h2>前三集27镜对照</h2><img src="前三集27镜对照.jpg" alt="前三集各九镜，三行分别为001、002、003；大多数画面为相近的卧室床窗黄被构图"><h2>逐集目录</h2><nav aria-label="集数">{nav}</nav>{''.join(full_html)}</main></html>'''
embedded_image = 'data:image/jpeg;base64,' + base64.b64encode((OUT / '前三集27镜对照.jpg').read_bytes()).decode('ascii')
page = page.replace('src="前三集27镜对照.jpg"', f'src="{embedded_image}"')
(OUT / '100集剧本核对.html').write_text(page)

with zipfile.ZipFile(OUT / '100集原始剧本快照.zip', 'w', compression=zipfile.ZIP_DEFLATED) as z:
    for f in sorted(snapshot.rglob('*')):
        if f.is_file():
            z.write(f, str(f.relative_to(OUT)))
    z.write(OUT / '原稿快照SHA256.json', '原稿快照SHA256.json')
dump(OUT / '核对检查.json', {
    'date_beijing': '2026-11-11', 'episodes': len(episodes), 'shots': sum(len(d['shots']) for d in episodes),
    'original_json_unchanged': all(sha(ROOT / d['source_json']) == d['source_json_sha256'] == sha(snapshot / d['source_json']) for d in episodes),
    'original_markdown_unchanged': all(sha(ROOT / d['source_markdown']) == d['source_markdown_sha256'] == sha(snapshot / d['source_markdown']) for d in episodes),
    'editorial_review_count': len(notes), 'checks': checks,
    'review_scope': '100集文字与900镜设计已逐项阅读；001–003原图缩略对照已查看；未完整听看成片；无平台审核预测。',
    'user_individual_review': '待核对', 'script_revision': '未改源稿', 'media_production': '未启动',
})
print(json.dumps({'episodes': len(episodes), 'shots': 900, 'editorial_decisions': stats['处理建议计数'], 'prompt_template_matches': stats['逐镜提示词等于镜名加camera模板'], 'output': str(OUT)}, ensure_ascii=False))
