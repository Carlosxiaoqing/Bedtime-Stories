# 本地工具

- `setup.py`：Python 3.12 创建项目内 .venv，并安装 requirements-lock.txt 中16项固定依赖；不修改系统 Python。重复运行复用虚拟环境。
- `run.py doctor`：检查固定依赖版本、FFmpeg编码器/滤镜、包内字体、v005的已附来源文件SHA256（完整仓库73项，ZIP省略可再生成的无字幕母版后72项）。
- `run.py render`：通过本地适配的 render_ep001.py 重新制作001。中间文件与日志写episodes/ep001/本地复现，最终视频/封面/正文另交Outputs/北京时间日期/单集目录；成功后完整解码并检查规格、37条字幕、配音与混音哈希，保存 local-validation.json，删除本次中间镜头缓存。失败保留日志、缓存与 FAILED.txt，不记作成功。
- `run.py export-reference`：复制已有 v005 交付到当天目录，适合直接取得相同的参考视频。
- `render_ep001.py`：从 v005 原制作程序适配，只增加可移植的路径、输出、缓存与字体加载；保持原画面、声音、字幕、封面算法。通过 run.py 调用，不直接运行。
- `fonts/`：Noto Sans CJK Regular/Bold 独立SC OTF（从官方TTC的SC索引2提取，字形未裁剪，Pillow索引0）和Noto Sans Regular，附原许可证。FFmpeg直接加载包内字体，无需安装到操作系统。
- `package.py`：重建下载ZIP，排除历史和缓存，写入逐文件完整性清单；不是制作视频的必要命令。

已有 episodes/ep001/v005/tools 中的脚本作为原始工程保留，不通过它们直接复现本地交付（会写回原episode目录）；原 synthesize.py 会覆盖已确认录音与时间线，不可为环境检查调用。

无需常驻Web服务、云环境变量、API密钥或GitHub凭据即可用现有素材渲染。Python依赖首次安装需要访问PyPI；FFmpeg必须另行安装。在线新配音是独立能力，不是本包复现第一集的前置条件。

`export_story_scripts.py --version v3 --output-dir <02_100集剧本/阅读与审校下的独立目录>` 从多场景版v3 JSON导出100集单集Markdown、阅读页、目录和版本校验。需要重导v2时使用 `--version v2`。历史第一集成片继续用 `run.py` 复现。

2026-11-11新增用户长稿v4：004–100完整口播、不设五分钟上限，001–003仅保留原短稿参考。`export_long_scripts.py --output-dir <02_100集剧本/阅读与审校下的独立目录>`从v4 JSON导出完整合集、单集Markdown并验证口播一致；`--validate-only`只读检查。v4正文在`narration_paragraphs`，004正式35镜已完成，其余长稿分镜尚未制作；旧v2/v3导出入口与001渲染器不能直接生成新长版视频。角色图需先建立并逐镜实际引用，换衣服不改身份。执行前看主控与新分镜／角色图库规范。

首批角色图库已完成：`character_references.py --validate-all`校验10位角色与已登记服装；`--characters pipi lili tuantuan goat_teacher --outfits pipi=day_v001`返回第四集前置角色的5张真实参考路径，需在后续图像调用时实际传入。超过5张、未建配角或摘要不符会报错，不会静默丢图。`transition_preview.py --output-dir <03_素材与参数下的独立评估目录>`生成12秒静态图片A/B对比，不是第四集视频；本次评估保留原0.96秒线性叠化。旧doctor因可变的001 RECORD.md与历史摘要不同报错，另72项来源文件实际一致，详见本次初始化记录；不改旧清单使其假通过。

默认输出时区固定为北京时间UTC+8，不随电脑时区变化。当前已在Linux/Python3.12/FFmpeg7.1.5验证；Windows/macOS提供启动方式，未实际运行验证。

打包大小控制：包内保留完整的带字幕参考成片；未附可重新生成的参考无字幕母版 `episodes/ep001/v005/output/ep001_clean.mp4`。运行 `render` 会重新输出无字幕母版与带字幕版；`export-reference` 只复制包内已有文件。原始SHA256清单仍保留，doctor只允许这一项母版缺省，其余文件逐项校验。

2026-11-11长稿004已完成：`synthesize_long_episode.py`（须有当集文本外传授权）→`lock_long_storyboard.py`→`prepare_story_image.py`及内置图像工具实际加载参考出图→`build_long_subtitles.py`→`render_long_episode.py`→`check_long_episode.py`。仅004已实际验证，不能当作后96集现成素材。完整工程在`episodes/ep004/v001/`。用已有工程离线复现只需渲染器和检查器，不重做TTS、不重锁镜头覆盖已选用图。当前Noto字体libass字号114/66经解码校准对应目标76/48，见工程font-calibration.json。

2026-11-12目录更新：以`docs/production/DIRECTORY_SPEC.md`为准。长稿渲染`--output-dir`指定episodes工程，新增`--delivery-dir`指定仅含最终文件的Outputs目录；检查器同样支持两目录分开。当前004用户已认可，片长278.72秒、35镜、完整口播与拼音样式继续沿用，封面优先四字。

2026-11-12云端同步：`setup_cloud.sh`安装依赖后使用`cloud_preflight.py --require-no-videos`，不依赖不进Git的MP4；旧001 doctor清单不作为新云端素材检查入口。长稿渲染器/字幕/分镜和检查器已从本集JSON读取集号、字数、镜数和时长；新故事仍须完整策划分镜与校对拼音。`prepare_story_image.py`对新集只用显式environment_reference，不根据第N镜强套004卧室和动作。见根目录云端接手.md。
