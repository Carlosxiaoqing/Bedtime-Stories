# 第003集本地制作脚本

使用项目根目录 .venv 中的 Python 3.12、local/requirements-lock.txt 及 FFmpeg 9 ffmpeg-full。需要从项目根目录运行：

```sh
source ~/.zprofile
.venv/bin/python episodes/ep003/v001/tools/synthesize.py
.venv/bin/python episodes/ep003/v001/tools/render.py
.venv/bin/python episodes/ep003/v001/tools/check.py
```

脚本读取 02_100集剧本/结构化JSON/ep003.json，逐句保存 Edge TTS 源MP3及请求元数据；九张本集插画、编辑源和所有导出保存在本集任务目录。视频不覆盖其他集数或旧版。

