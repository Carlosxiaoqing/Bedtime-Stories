# 第002集制作脚本

在项目根目录使用Python3.12及requirements.txt中的依赖，FFmpeg需libx264/AAC/libass/xfade；字体从仓库local/fonts读取。

本集音频和九张专属原图已提供。synthesize.py读取ep002.json，仅对变化的台词或参数请求TTS；render.py复用本集音轨与原图重新生成视频、字幕、封面和混音；check.py执行完整解码、字幕/参数与静态画面检查。

正常调用：python Outputs/2026-11-10/ep002-v001/tools/render.py，然后用同目录check.py检查。本次任务输出均在此目录下；源码按自身路径定位项目，ASS与字体路径通过工作目录解析。中间cache可重建，成功渲染后自动清理。旧版本与来源媒体保留；不同日期新任务请按Outputs/北京时间日期/独立任务目录保存。
