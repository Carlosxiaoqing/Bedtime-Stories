# 目录规范

项目根目录稳定划分稿件、共用素材、工程与最终交付。新会话执行顺序见`CHANNEL_MASTER.md`和`云端接手.md`。

```text
02_100集剧本/
  用户长稿v5/结构化JSON/      # 唯一有效、可编辑的100集剧本源
  阅读与审校/                # 由v5 JSON导出的阅读视图
03_素材与参数/                # 角色参考、声音/视觉参数
episodes/epNNN/vNNN/         # 工程、音轨、字幕、提示词、来源、检查报告
Outputs/YYYY-MM-DD/epNNN-vNNN/ # 最终视频、封面、平台文案
```

旧v2/v3/v4替代剧本、根目录重复JSON/Markdown和旧导出工具已从当前工作树移除。已有媒体工程保留原脚本快照以记录来源；它们仅用于历史核验，不是当前改稿或新制作入口。

全集阅读视图由`local/export_opening_scripts.py`从v5 JSON生成，并做一致性验证。不要手工编辑导出的Markdown。媒体渲染临时文件留在本集工程，不写入Outputs。

v3封面工程文件`cover-plan.json`、无字底图`cover_base.png`、`cover.svg`、`cover-title.txt`、`cover-render.json`、提示词/参考来源和跨集差异检查留在`episodes/epNNN/vNNN/`；最终`cover.png`及三平台文案复制到单集Outputs目录。cover-plan仅配置发布包装，不替代唯一v5剧本。

所有视频文件均排除在GitHub当前文件树之外，包括主视频、无字幕母版及其他视频格式。`Outputs/`中的封面、发布文案和说明文件，以及工程、音轨、插画、字幕和检查资料按项目同步范围保留。历史提交不改写，旧提交中的视频对象不在本规则下清除。
