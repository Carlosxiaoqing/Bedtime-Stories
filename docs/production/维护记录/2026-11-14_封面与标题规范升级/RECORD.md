# 封面与标题规范升级记录

日期：2026-11-14（北京时间）。用户在本次会话确认“我们就按照这个方式去优化一下”，要求把规则写入项目，使下一期制作能正确应用。

## 已确认规则

- 皮皮正脸清楚出镜，身份、柔和水彩风和标题卡版式统一；按真实剧情逐集区分场景、伙伴、关键道具和主色，避免同一姿势/困倦脸套用全系列。
- 标题6–10个汉字，采用“皮皮＋本集真实的一件事”；封面与发布标题完全一致。三个发布平台共用标题，各自写正文及标签。
- 标题按词义排为两行，每行3–5字，保留112px字体；无法自然换行时重写标题。
- 保留现有v5 p000开场与既定结尾，不加结尾预告钩子。口播故事原名、正文、声线、字幕及镜头节奏不因本次包装规则改变。
- 从后续新制作、尚未交付的封面及用户指定的重制执行；不自动返工既有交付。

## 落地位置

1. 规范：`docs/production/COVER_SPEC.md`升级bedtime-cover-v3；`PUBLISH_COPY_SPEC.md`升级1.1，统一标题来源、正文格式及校验命令。
2. 执行入口：同步`AGENTS.md`、`CHANNEL_MASTER.md`、`01_制作手册/制作总手册.md`、`云端接手.md`、`README.md`、`HANDOFF.md`、`本地开始.md`及`docs/production/README.md`。
3. 流程/记录：同步`EPISODE_WORKFLOW.md`、`DIRECTORY_SPEC.md`、`EPISODE_STATUS.md`的新任务说明和`templates/EPISODE_RECORD.md`，增加封面正脸、剧情准确性、最近3–5集差异和手机网格检查；未执行不标通过。
4. 配置：同步`03_素材与参数/封面与字幕参数.json`及`PROJECT_STATE.json`的visual/packaging_policy，移除当前机器状态中的四字优先字段；字幕/转场配置保持一致。
5. 单集方案：新增`templates/cover-plan.template.json`。每集复制到工程内的`cover-plan.json`并填写title、title_lines、场景主色、动作/表情、关键物件、实际参考图路径、v5正文段落依据和跨集检查。此为发布包装配置，不作为剧本源，不修改100集稿源；旧分镜cover_title不再覆盖新方案。
6. 排版工具：新增`local/cover_assets.py`，读取共享配置与单集方案；检查6–10字/皮皮前缀、语义换行字段、有效参考图/正文段落ID、三平台标题一致；生成cover.png、cover.svg、cover-title.txt与cover-render.json，按文件摘要检查复用并阻止覆盖不同版本成品。
7. 渲染与检查：`render_long_episode.py`、`check_long_episode.py`默认使用v3方案；正式渲染前核对三平台标题。历史4–6字工程复现/核验需显式`--legacy-cover`。看图检查与技术排版检查分别记录。

## 检查证据

- `.venv/bin/python -m unittest discover -s local -p 'test_cover_assets.py' -v`：4项通过，覆盖6/7/8/9/10字不裁切、拒绝旧短标题和错误换行、拒绝平台标题不一致/缺失、已有封面不覆盖、输入变更检测以及仅补检查说明不改变排版。
- `.venv/bin/python -m unittest discover -s local -p 'test_cloud_handoff.py' -v`：临时可搬移副本中的离线预检、历史2秒复现与v3默认1秒渲染集成通过；测试使用历史媒体作为解码/排版夹具，没有生成正式新集或写入Outputs。
- `python3 local/export_opening_scripts.py --validate-only`：100集v5 JSON检查通过；稿源JSON未修改。
- Python AST、JSON解析、SVG XML解析通过；字幕及转场配置与变更前相同；`git diff --check`通过。
- [排版技术接触表](排版验证_6至10字.jpg)已查看，6–10字两行均能放入标题卡；[数据记录](排版验证.json)。纯色占位图仅用于排版检查，不冒充正式封面，不代表皮皮正脸、剧情或跨集差异已验收。

## 范围与状态

本次完成的是制作规则、配置、排版工具和交接说明升级。已有第016集制作中的工作树改动予以保留，未修改其单集工程、未自动启动下一集，未修改或覆盖历史交付。未制作正式新封面、未发布平台、未同步GitHub；流量与转粉效果尚未验证。
