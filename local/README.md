# 当前制作工具入口

新集剧本统一采用v5，唯一JSON源在`02_100集剧本/用户长稿v5/结构化JSON/`。旧版剧本导出器已从当前工具集移除。

- `export_opening_scripts.py --validate-only`：校验100集v5 JSON、开场标记、逐集摘要和片头独立配图要求。
- `export_opening_scripts.py --output-dir <02_100集剧本/阅读与审校下的v5目录>`：从唯一JSON源导出合集、片头清单、100份单集Markdown和一致性报告。
- `cover_assets.py --output-dir episodes/epNNN/vNNN --validate-only`：检查v3封面方案（6–10字“皮皮＋一件事”、显式语义换行、剧情依据/参考路径）；加`--check-copy`核对三平台标题，去掉`--validate-only`用cover_base.png生成封面与排版记录。方案模板在`docs/production/templates/cover-plan.template.json`。
- `render_long_episode.py`：新制作默认使用cover-plan.json和v3封面；正式渲染前核对三个发布标题。`--legacy-cover`仅供历史4–6字封面复现，不用于新制作；保留历史交付。
- `check_long_episode.py`：新制作默认检查v3方案与工程/交付文案标题；仅检查历史工程时显式使用`--legacy-cover`。封面正脸、剧情与跨集差异仍须看图并单独记录。
- `cloud_preflight.py`：检查云端制作依赖、v5稿源、角色参考素材及004基准工程；不调用TTS或图片生成，不渲染视频。
- `setup_cloud.sh`：准备云端Python和系统依赖。

视频制作按`CHANNEL_MASTER.md`、`云端接手.md`及`docs/production/EPISODE_WORKFLOW.md`执行。历史单集目录中的工具快照仅用于解释对应版本，不覆盖`local/`当前工具。
