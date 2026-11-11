# 当前入口：云端继续制作

第四集v001已于2026-11-12获用户认可。下一候选005尚未授权制作。请先读[云端接手](云端接手.md)、[制作主控](CHANNEL_MASTER.md)和[项目状态](PROJECT_STATE.json)。

仓库同步完整剧本、角色参考图、插画、配音、字幕、参数、工具及许可证；不跟踪视频和可能含视频的压缩包。云端环境可用`bash local/setup_cloud.sh`准备，随后运行`local/cloud_preflight.py`，无需先找到MP4。新集在线配音和插画仍需目标环境具备对应能力。

---

# 晚安绘本馆

儿童中文睡前绘本系列。后续制作采用统一封面、温柔晓晓配音、水彩插画，以及**每个汉字上方带拼音的可见字幕**。每集同时交付抖音、小红书、微信视频号各自的标题、正文与正文内标签。最新交付为[002《皮皮的月光小口袋》](episodes/ep002/v001/output/README.md)。

后续所有集数统一遵循[制作主控中的最新要求](CHANNEL_MASTER.md)：固定图片、汉字76px/拼音48px、封面只放当集短主题；每集交付视频、封面及三平台标题和含标签正文。最新规范同步日期：2026-11-10（北京时间）。

## 从这里开始

1. [制作主控与当前进度](CHANNEL_MASTER.md)：固定标准、当前状态、下一步。
2. [100集剧本索引](02_100集剧本/00_总目录.md)：选定集数后读取对应JSON与Markdown；JSON是唯一改稿源。
3. [接手约定](AGENTS.md) · [交接与缺失材料](HANDOFF.md)
4. [声音与语速](docs/production/VOICE_PROFILE.md) · [视频要求](docs/production/VIDEO_SPEC.md)
5. [统一封面](docs/production/COVER_SPEC.md) · [逐字拼音字幕](docs/production/SUBTITLE_SPEC.md)
6. [三平台文案规范](docs/production/PUBLISH_COPY_SPEC.md)
7. [单集流程](docs/production/EPISODE_WORKFLOW.md) · [单集记录模板](docs/production/templates/EPISODE_RECORD.md)

## 当前可用范围

已导入100集结构化剧本、阅读视图、声音/角色/画风参数与原交付包手册。第001集第二版是历史已验收基准，但首集媒体、`04_生产工程/` 和 `05_验收与校验/` 尚未导入本仓库。002初版已交付；第003–100集仅有剧本与制作方案，专属媒体尚未制作。

[001集v005完整初版](episodes/ep001/v005/output/README.md)已生成：99.88秒视频、九张水彩原图、统一封面、逐字拼音字幕与三平台文案。-35%语速参数已确认，新版实际音频与完整成片待审；该集的可编辑制作脚本在`episodes/ep001/v005/tools/`，后续指定集数再按本集规范适配。

## 迁移到本地 Codex

下载 [本地制作ZIP](downloads/Bedtime-Stories-local.zip)，解压后在 Codex 打开项目根目录，先读[本地开始](本地开始.md)。包含第一集v005原图、现有 -35% 音频、参考成片、100集剧本、制作规范、字体和本地运行入口。新输出统一为 `Outputs/北京时间日期/本次任务/`。

后续制作的新交付统一放在`Outputs/北京时间日期/独立任务目录/`，以主控与单集台账的实际状态为准。

2026-11-12：004 v001已获用户认可。Outputs只放单集成片、封面与交付文本；共用剧本在02_100集剧本、角色图在03_素材与参数、制作源在episodes，均为根目录下的同级目录。入口见[目录规范](docs/production/DIRECTORY_SPEC.md)。封面默认四字，必要时五或六字，具体易懂且有吸引力。
