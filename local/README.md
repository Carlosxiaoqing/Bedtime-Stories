# 本地工具

- `setup.py`：Python 3.12 创建项目内 .venv，并安装 requirements-lock.txt 中16项固定依赖；不修改系统 Python。重复运行复用虚拟环境。
- `run.py doctor`：检查固定依赖版本、FFmpeg编码器/滤镜、包内字体、v005的已附来源文件SHA256（完整仓库73项，ZIP省略可再生成的无字幕母版后72项）。
- `run.py render`：通过本地适配的 render_ep001.py 重新制作001。日志及输出只写 Outputs/北京时间日期/唯一任务目录；成功后完整解码并检查规格、37条字幕、配音与混音哈希，保存 local-validation.json，删除本次中间镜头缓存。失败保留日志、缓存与 FAILED.txt，不记作成功。
- `run.py export-reference`：复制已有 v005 交付到当天目录，适合直接取得相同的参考视频。
- `render_ep001.py`：从 v005 原制作程序适配，只增加可移植的路径、输出、缓存与字体加载；保持原画面、声音、字幕、封面算法。通过 run.py 调用，不直接运行。
- `fonts/`：Noto Sans CJK Regular/Bold 独立SC OTF（从官方TTC的SC索引2提取，字形未裁剪，Pillow索引0）和Noto Sans Regular，附原许可证。FFmpeg直接加载包内字体，无需安装到操作系统。
- `package.py`：重建下载ZIP，排除历史和缓存，写入逐文件完整性清单；不是制作视频的必要命令。

已有 episodes/ep001/v005/tools 中的脚本作为原始工程保留，不通过它们直接复现本地交付（会写回原episode目录）；原 synthesize.py 会覆盖已确认录音与时间线，不可为环境检查调用。

无需常驻Web服务、云环境变量、API密钥或GitHub凭据即可用现有素材渲染。Python依赖首次安装需要访问PyPI；FFmpeg必须另行安装。在线新配音是独立能力，不是本包复现第一集的前置条件。

默认输出时区固定为北京时间UTC+8，不随电脑时区变化。当前已在Linux/Python3.12/FFmpeg7.1.5验证；Windows/macOS提供启动方式，未实际运行验证。

打包大小控制：包内保留完整的带字幕参考成片；未附可重新生成的参考无字幕母版 `episodes/ep001/v005/output/ep001_clean.mp4`。运行 `render` 会重新输出无字幕母版与带字幕版；`export-reference` 只复制包内已有文件。原始SHA256清单仍保留，doctor只允许这一项母版缺省，其余文件逐项校验。
