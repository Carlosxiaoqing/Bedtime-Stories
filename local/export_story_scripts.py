"""Export the selected multi-setting episode JSON files for script review."""

import argparse
from collections import Counter
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re
import shutil
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "02_100集剧本"
ASSETS = ROOT / "03_素材与参数"
CAST_FILE = "多场景版角色设定.json"
STYLE_FILE = "多场景版画风与提示词.json"
CATEGORIES = ("学校", "社区", "自然", "出行", "家庭", "想象")
PLACE_GUIDE = {
    "学校": "榆树学校有门厅、教室、操场、读书角和菜园。双人桌有靠书架的内侧与过道外侧，两种位置在前后故事中一致。",
    "社区": "长耳街连着老榆图书馆、集市、画廊、修伞铺、面包房和工艺室。街心长桌有石阶入口、宽门与小树旁的路。",
    "自然": "榛子坡有果园、花圃和开阔草场。蒲草塘、芦苇河有带栏的观察点。松岭的树荫、观鸟棚和山路各有不同视野。",
    "出行": "雾谷小火车通向青坡与林边站。青石港可坐短渡船。白湾有雪地、海岸、盐田、展馆和沿岸小巴。",
    "家庭": "故事在厨房、饭桌、共用起居间、前廊、手工桌或门前树荫里发生。朋友相处由具体的家务、约定和生活变化推动。",
    "想象": "纸花镇、云坡、颜色博物馆、影子车站和泡泡河有各自的规则。人物会亲自走进这些地方并完成当集事件。",
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path, value):
    path.write_text(value, encoding="utf-8")


def hanzi(text):
    return len(re.findall(r"[\u3400-\u9fff]", text))


def story_files(version):
    files = sorted((LIBRARY / f"多场景版{version}/结构化JSON").glob("ep*.json"))
    if [p.stem for p in files] != [f"ep{n:03d}" for n in range(1, 101)]:
        raise ValueError("稿源须包含001–100各一份JSON")
    return files


def validate_episode(episode, path, cast, version):
    assert episode["id"] == path.stem and episode["episode"] == int(path.stem[2:]), path
    assert episode["script_version"] == version and episode["category"] in CATEGORIES, path
    assert 2 <= hanzi(episode["cover_title"]) <= 8, path
    assert episode["viewpoint_character"] in episode["character_names"], path
    assert [s["id"] for s in episode["shots"]] == list(range(1, 10)), path
    names = set()
    locations = set()
    spoken = []
    for shot in episode["shots"]:
        characters = shot["character_names"]
        assert set(characters) <= cast.keys() and len(characters) == len(set(characters)), path
        names.update(characters)
        locations.add(shot["location"])
        lines = shot["narration_lines"]
        assert lines and all(lines) and len(lines) == len(shot["pause_after_s"]), path
        assert shot["motion"] == "fixed" and shot["image"] == f"images/shot_{shot['id']:02d}.png", path
        assert shot["location"] in shot["image_prompt"] and shot["title"] in shot["image_prompt"], path
        assert all(character in shot["image_prompt"] for character in characters), path
        spoken.extend(lines)
    assert names == set(episode["character_names"]), path
    assert locations == set(episode["setting"].split("、")), path
    assert sum(map(hanzi, spoken)) == episode["cn_characters"], path
    assert episode["shots"][-1]["pause_after_s"][-1] == 8.0, path
    assert episode["actual_duration_s"] is None, path
    if "duration_plan" in episode:
        plan = episode["duration_plan"]
        assert plan["estimated_s"] == episode["initial_duration_budget_s"], path
        low, high = plan["planning_range_s"]
        assert low <= plan["estimated_s"] <= high, path


def episode_markdown(episode):
    number = f"{episode['episode']:03d}"
    content = [
        f"# 第{number}集 {episode['title']}\n",
        f"- 主视角：{episode['viewpoint_character']}\n- 入镜角色：{'、'.join(episode['character_names'])}",
        f"- 类型：{episode['category']}\n- 地点：{episode['setting']}",
        f"- 主题：{episode['theme']}\n- 封面短标题：{episode['cover_title']}",
        f"- 口播：{episode['cn_characters']}个汉字，九镜。实际时长以配音为准。\n",
    ]
    if "duration_plan" in episode:
        content.append(f"- 成片目标约120秒，本稿估算{episode['initial_duration_budget_s']:.1f}秒。\n")
    for shot in episode["shots"]:
        content.extend([
            f"## 镜{shot['id']:02d} {shot['title']}\n",
            "**口播**\n",
            "\n".join(shot["narration_lines"]) + "\n",
            "**绘图提示词**\n",
            shot["image_prompt"] + "\n",
            f"句后停顿参考（秒）：{'、'.join(str(p) for p in shot['pause_after_s'])}。镜内画面固定。\n",
        ])
        if "duration_plan" in episode:
            content.append(f"本镜预估{shot['initial_budget_s']:.1f}秒（含相应停顿或尾声）。\n")
    content.extend([
        "## 本版记录\n",
        f"{episode['script_version']} · {episode['revision_record']['date']}。剧本与九镜已编写。配音、插画、封面、拼音校对、渲染、技术检查、人工听看及用户验收待进行。\n",
        f"[剧本JSON快照](../结构化JSON快照/{episode['id']}.json) · [角色与场景](../角色与场景.md)\n",
    ])
    return "\n".join(content)


def reading_card(episode):
    number = f"{episode['episode']:03d}"
    title = escape(episode["title"])
    focus = escape(episode["viewpoint_character"])
    category = escape(episode["category"])
    cast = escape("、".join(episode["character_names"]))
    places = escape(episode["setting"])
    shots = []
    for shot in episode["shots"]:
        dialogue = "".join(escape(line) for line in shot["narration_lines"])
        seconds = f" · 预估 {shot['initial_budget_s']:.1f} 秒" if "duration_plan" in episode else ""
        shots.append(
            f'<section class="shot"><h3>镜{shot["id"]:02d}　{escape(shot["location"])}{seconds}</h3>'
            f'<p class="speech">{dialogue}</p><p class="direction">{escape(shot["image_prompt"])}</p></section>'
        )
    search = escape(f"{number} {title} {places} {cast} {episode['theme']}", quote=True)
    expanded = " open" if number == "001" else ""
    timing = f" · 预估 {episode['initial_duration_budget_s']:.1f} 秒" if "duration_plan" in episode else ""
    return (
        f'<details id="ep{number}" class="episode" data-category="{category}" data-focus="{focus}" data-search="{search}"{expanded}>'
        f'<summary><span class="index">{number}</span> <strong>{title}</strong>'
        f'<span class="secondary">{category} · {focus}{timing}</span></summary>'
        f'<div class="episode-content"><p class="secondary">{places} · {cast}</p>'
        f'<p>主题　{escape(episode["theme"])}<br>封面短标题　{escape(episode["cover_title"])}</p>'
        + "\n".join(shots)
        + "</div></details>"
    )


def reading_page(episodes, cast):
    version = episodes[0]["script_version"]
    subtitle = "100集完整口播、900个分镜、17位具名角色。展开任意一集查看口播和画面。"
    if version == "v3":
        subtitle = "每集约两分钟，九镜。展开任意一集查看口播、画面和估算时长。最终时长以实际配音为准。"
    category_options = "".join(f"<option>{category}</option>" for category in CATEGORIES)
    focus_options = "".join(f"<option>{name}</option>" for name in cast)
    return """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>皮皮和朋友们 · 100集多场景剧本</title>
<style>
:root{color-scheme:light;--paper:#f6f3ec;--ink:#25342f;--muted:#4c655d;--line:#d6ddd4;--leaf:#315849}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.75 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}
main{max-width:1060px;margin:auto;padding:40px 24px 64px}header{padding-bottom:20px;border-bottom:1px solid var(--line)}
h1{font-size:clamp(26px,5vw,39px);line-height:1.3;margin:4px 0 10px;letter-spacing:.02em}p{margin:8px 0 14px}
.secondary,.direction,.index{color:var(--muted)}.secondary,.direction{font-size:14px}
.controls{display:grid;grid-template-columns:2fr 1fr 1fr;gap:12px;margin:20px 0 8px}
label{display:grid;gap:4px;font-size:14px;color:var(--leaf)}input,select{min-width:0;width:100%;padding:8px;border:1px solid #aabbb0;border-radius:6px;background:#fffcf7;color:var(--ink);font:inherit;font-size:16px}
summary{display:flex;gap:12px;align-items:baseline;cursor:pointer;padding:14px 12px;flex-wrap:wrap}
summary::before{content:'▸';color:var(--leaf)}details[open]>summary::before{content:'▾'}
summary .secondary{margin-left:auto}.index{font-variant-numeric:tabular-nums}.episode{border-bottom:1px solid var(--line)}
.episode-content{padding:2px 18px 18px 34px}.shot{padding:12px 0;border-top:1px solid var(--line)}
.shot h3{font-size:15px;margin:0;color:var(--leaf)}.speech{font-size:17px;margin:7px 0 4px}
a{color:var(--leaf)}[hidden]{display:none!important}#status{min-height:1.75em;margin:4px 0;color:var(--muted)}
@media(max-width:600px){main{padding:24px 14px 42px}.controls{grid-template-columns:1fr 1fr}.controls label:first-child{grid-column:1/-1}.episode-content{padding-left:14px;padding-right:10px}summary{gap:8px}summary .secondary{margin-left:0}}
</style></head><body><main>
<header><p class="secondary">多场景版 """ + version + """ · 2026-11-11</p><h1>皮皮和朋友们的100集故事</h1>
<p>""" + subtitle + """</p></header>
<div class="controls"><label>搜索集数、角色或地点<input id="search" type="search" placeholder="例如 003、朵朵、学校"></label>
<label>故事场景<select id="category"><option value="">全部场景</option>""" + category_options + """</select></label>
<label>主视角<select id="focus"><option value="">全部角色</option>""" + focus_options + """</select></label></div>
<p id="status" aria-live="polite">显示100集</p><div id="episodes">
""" + "\n".join(reading_card(e) for e in episodes) + """
</div></main><script>
const search = document.getElementById('search');
const category = document.getElementById('category');
const focus = document.getElementById('focus');
const status = document.getElementById('status');
const episodes = [...document.querySelectorAll('.episode')];
function applyFilters() {
  const words = search.value.trim().toLowerCase().split(/\\s+/u).filter(Boolean);
  let count = 0;
  for (const episode of episodes) {
    const match = (!category.value || episode.dataset.category === category.value)
      && (!focus.value || episode.dataset.focus === focus.value)
      && words.every(word => episode.dataset.search.toLowerCase().includes(word));
    episode.hidden = !match;
    if (match) count += 1;
  }
  status.textContent = count ? '显示' + count + '集' : '没有符合条件的剧本';
}
search.addEventListener('input', applyFilters);
category.addEventListener('change', applyFilters);
focus.addEventListener('change', applyFilters);
const selected = document.getElementById(location.hash.slice(1));
if (selected?.classList.contains('episode')) selected.open = true;
</script></body></html>
"""


def export(output, version):
    output = output.resolve()
    if output.is_relative_to(ROOT / 'Outputs'):
        raise ValueError('全集剧本属于共用资料，请导出到02_100集剧本/阅读与审校/，不要放入Outputs。')
    paths = story_files(version)
    previous = "v1" if version == "v2" else "v2"
    previous_dir = LIBRARY / ("结构化JSON" if previous == "v1" else "多场景版v2/结构化JSON")
    cast = read_json(ASSETS / CAST_FILE)
    episodes = [read_json(path) for path in paths]
    for path, episode in zip(paths, episodes, strict=True):
        validate_episode(episode, path, cast, version)
    if len({e["title"] for e in episodes}) != len(episodes):
        raise ValueError("出现重复标题")

    script_copy = output / "结构化JSON快照"
    markdown_dir = output / "单集Markdown"
    asset_dir = output / ASSETS.name
    for directory in (script_copy, markdown_dir, asset_dir):
        directory.mkdir(parents=True, exist_ok=True)
    for name in (CAST_FILE, STYLE_FILE, "配音与声音参数.json"):
        shutil.copy2(ASSETS / name, asset_dir / name)
    categories = Counter(e["category"] for e in episodes)
    first_appearance = {}
    catalog = [
        "# 100集多场景版剧本目录\n",
        f"2026-11-11 · {version}。正稿由项目稿库内的{version} JSON维护，这份目录和逐集阅读稿由JSON导出。\n",
        "| 集数 | 故事 | 类型 | 主视角 | 地点 |",
        "| --- | --- | --- | --- | --- |",
    ]
    version_hashes = {}
    generated_markdown = []
    for path, episode in zip(paths, episodes, strict=True):
        number = f"{episode['episode']:03d}"
        title = episode["title"]
        md_name = f"第{number}集_{title}.md"
        dest = markdown_dir / md_name
        shutil.copyfile(path, script_copy / path.name)
        write_text(dest, episode_markdown(episode))
        generated_markdown.append(dest)
        source_lines = [shot["narration_lines"] for shot in episode["shots"]]
        sections = re.findall(r"\*\*口播\*\*\s*\n(.*?)(?=\*\*绘图提示词\*\*)", dest.read_text(encoding="utf-8"), re.S)
        assert [s.strip().splitlines() for s in sections] == source_lines, path
        assert (script_copy / path.name).read_bytes() == path.read_bytes(), path
        for name in episode["character_names"]:
            first_appearance.setdefault(name, number)
        catalog.append(f"| {number} | [{title}](单集Markdown/{md_name}) | {episode['category']} | {episode['viewpoint_character']} | {episode['setting']} |")
        version_hashes[path.stem] = {
            previous: sha256((previous_dir / path.name).read_bytes()).hexdigest(),
            version: sha256(path.read_bytes()).hexdigest(),
        }
    role_guide = [
        "# 皮皮和朋友们\n",
        "皮皮是串起全系列的小灰兔。朋友们轮流推动故事，也有自己的性格、愿望、住处与相处方式。\n",
        "## 人物\n",
    ]
    for name, profile in cast.items():
        role_guide.extend([
            f"### {profile['物种']}{name}\n",
            f"第{first_appearance[name]}集登场。{profile['性格与行动']}\n",
            f"{profile['关系']}\n",
            f"画面锚点　{profile['画面锚点']}\n",
        ])
    role_guide.append("## 场景\n")
    for category in CATEGORIES:
        role_guide.append(f"- **{category}（{categories[category]}集）**　{PLACE_GUIDE[category]}")
    role_guide.append("\n## 前后呼应\n")
    role_guide.extend([
        "- 第001、094、097、100集的半叶书签和座位，串起皮皮与斑斑的同桌关系。",
        "- 第014集画出双河岛，第050集把两条纸河做成大家能走的草地小岛。",
        "- 第015集雪团想闻树荫下的草香，第075集约好见面地点，第080集来到榛子坡，第100集认出同样的风。",
        "- 第077集梨梨离开旧柿树，第095集在新家认出自己的第一片树影。",
    ])
    write_text(output / "角色与场景.md", "\n".join(role_guide) + "\n")
    write_text(output / "100集故事目录.md", "\n".join(catalog) + "\n")
    write_text(output / "100集新版剧本.html", reading_page(episodes, cast))
    report = {
        "episodes": len(episodes),
        "shots": sum(len(e["shots"]) for e in episodes),
        "spoken_lines": sum(len(s["narration_lines"]) for e in episodes for s in e["shots"]),
        "named_characters": len(first_appearance),
        "category_counts": dict(categories),
        "setting_labels": len({s["location"] for e in episodes for s in e["shots"]}),
        "pipi_appears_in": sum("皮皮" in e["character_names"] for e in episodes),
        "viewpoint_counts": dict(Counter(e["viewpoint_character"] for e in episodes)),
        "hanzi_min": min(e["cn_characters"] for e in episodes),
        "hanzi_max": max(e["cn_characters"] for e in episodes),
        "closing_framing_counts": dict(Counter(e["shots"][-1]["camera"] for e in episodes)),
        "json_markdown_narration_equal": True,
        "source_sha256": version_hashes,
    }
    write_text(output / "版本与校验.json", json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    included = [
        *generated_markdown,
        *(script_copy / p.name for p in paths),
        *(p for p in asset_dir.iterdir() if p.is_file()),
        *(output / name for name in ("角色与场景.md", "100集故事目录.md", "100集新版剧本.html", "版本与校验.json", "时长核算.json", "RECORD.md")),
    ]
    with ZipFile(output / "100集新版剧本.zip", "w", ZIP_DEFLATED) as archive:
        for file in included:
            if file.is_file():
                archive.write(file, file.relative_to(output))
    with ZipFile(output / "100集新版剧本.zip") as archive:
        assert archive.testzip() is None
    print(json.dumps({k: v for k, v in report.items() if k != "source_sha256"}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path, help="项目02_100集剧本/阅读与审校/下的独立导出目录")
    parser.add_argument("--version", choices=("v2", "v3"), default="v2", help="选择剧本稿源版号")
    args = parser.parse_args()
    export(args.output_dir.resolve(), args.version)
