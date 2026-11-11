# 第002集来源与制作信息

- 台词来自本集结构化JSON，未改写故事；原始分句MP3、请求参数、缓存摘要在audio/source。
- 九张插画由OpenAI image_gen分别生成。001第一镜仅供角色身份/水彩笔触参考；002第一镜建立月光与睡帽小口袋的新场景锚点，其余八镜据此生成。实际提示词见image-prompts.json，原图尺寸与SHA256见image-sources.json。
- 封面使用002第03镜并按固定模板排版，框内只有“月光口袋”。不显示账号名或系列名。
- 配音为zh-CN-XiaoxiaoNeural，edge-tts 7.3.1、rate=-35%、pitch=-2Hz、volume=+0%；TLS验证开启，继承环境代理与平台CA。
- 原创音乐为本地正弦谐波琶音，环境声为本地低通噪声；生成算法与本集等长时间线保留在tools/render.py。未使用第三方歌曲或录音。
- 字体为仓库local/fonts的Noto Sans CJK SC与Noto Sans；版权文本附licenses。汉字76px/拼音48px，按字测量居中；声调与轻声按本集词语语境修订，儿化按系列字幕规范记录。
- 图像固定，不推拉、平移、缩放或形变。转场与字幕时间来自实测音频；完整自动检查通过，用户完整听看待审。
