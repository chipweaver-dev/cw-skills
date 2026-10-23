# 工程管线与数据契约

本文是"怎么实现"的参考：工具链、脚本职责、JSON schema、音频主导时间轴算法、播放页架构、混音与验证。

## 目录

1. 工具链
2. Toolbox 组织方式
3. 脚本清单（按职责）
4. 数据契约
5. 旁白与时间轴管线
6. 播放页架构
7. 音乐与终混
8. 验证方法
9. 交付编码
10. 凭证与隐私

---

## 1. 工具链

| 类别 | 推荐 | 用途 |
|---|---|---|
| 图像 | Python 3.8+、Pillow、numpy、scipy、OpenCV（可选） | 裁切、抠图、合成、预览、音乐合成 |
| 视频/音频 | FFmpeg 7.x + ffprobe | 解码、拼接、响度、编码、探针 |
| TTS | 豆包 Speech 2.0 / 同类 HTTP 接口 | 整片旁白 + sentence frame |
| 页面 | Node 20+、Vite 7、React 19、TypeScript 5.8 | 1080×1920 舞台、时钟、录屏 |
| 评审 | Chrome + CDP（9222） | 定帧截图、量框、资源检查 |
| 输入 | PDF/图片/录屏/厂商资料 | research、素材、录屏 |

环境约定：

- Windows 本机用 Git Bash；入口用 `run.bat`。Linux 用 `Makefile`。
- FFmpeg 与项目 venv 的绝对路径属于本机配置：放 `run.bat`、PATH 或环境变量，不写进交付产物。
- Python 3.8 下避免 `list[str]`、`X | Y` 类型语法与 `match`；需要新语法时先确认解释器版本。
- 中文路径在 Windows 上用 Pillow 读写，不用 `cv2.imread`（见 `pitfalls.md`）。

## 2. Toolbox 组织方式

```text
toolbox/
├── Readme.md                 # 每个脚本的用途/输入/输出/示例
├── s1_spec.json              # 每段一个 spec，坐标与文案的唯一来源
├── s2a_spec.json
├── ...
├── timeline_source.json      # 段/拍/旁白/关键词/舞台绑定
├── reading_text.json         # 读音层
├── make_*_layers.py          # 生成透明图层
├── compose_*.py              # 合成预览静帧（评审用）
├── make_contact_sheet.py     # 拼 contact sheet
├── make_film_narration.py    # 整片 TTS + 归一化 + 时间轴 + 字幕
├── make_music_bed.py         # 合成音乐铺底
└── mix_film_music.py         # ducking + 终混 + 响度
```

规则：

- 一个脚本只做一件事，读 spec、写固定路径、参数用 `--root` / `--spec` / `--id`。
- 脚本必须幂等：重复运行覆盖自己的输出，不依赖上一次的中间状态。
- 缓存产物（TTS、归一化）要显式给 `--force` 才重跑；默认命中缓存直接返回。
- 任何脚本的失败信息必须带文件与字段，不能只打印 `KeyError`。
- 预览与交付分开：`compose_*.py --id` 出 `preview/stills/`；`--plate` 出不含页面覆盖层的底板。
- `run.bat` 按依赖顺序调用，任一失败 `goto :err`，不吞错误。

## 3. 脚本清单（按职责）

### 3.1 采集与真实素材

| 脚本 | 职责 | 关键点 |
|---|---|---|
| `upscale_capture.py` | 低分辨率截图/录屏放大到目标画布 | 保持原始宽高比；放大后锐化；不要拉伸 |
| `make_laptop.py` | 生成/合成整机示意图或屏幕内容 | 屏幕内容与边框分层；蓝框坐标用原图像素 |
| `b22_screen.py` | 特定屏幕/界面素材处理 | 同上的坐标与分层约定 |
| `make_cutout.py` | 抠图/去背 | 输出透明 PNG；保留原始边缘；记录源 URL |
| `compose_still.py` | 把素材合成为 1080×1920 静帧 | `--plate` 输出去掉面包屑/覆盖层的底板 |
| `compose_video.py` | 录屏裁切/叠加/编码 | 保留原始帧率；必要时重采样到 30 fps |

### 3.2 示意图与图层

| 脚本 | 职责 | 关键点 |
|---|---|---|
| `make_s2a_diagram.py` | 绘制章节主示意图 | 3× 超采样；标注与图形分层 |
| `export_s2a_layers.py` | 把示意图导出为透明图层 | 每层一个 PNG；坐标写回 spec |
| `make_s2b_layers.py` … `make_s2f_layers.py` | 每段图层生成 | 同一段共用一套坐标/字号常量 |
| `compose_s2b.py` … `compose_s2f.py` | 合成预览静帧 | 仅评审；必须与页面一致 |
| `make_contact_sheet.py` | 多图拼一张 | 固定列数/缩略图宽度；带文件名 |

### 3.3 时间轴、旁白、音乐

| 脚本 | 职责 | 关键点 |
|---|---|---|
| `make_timeline.py` | 从 `timeline_source.json` 生成**编稿时钟** | 只用于审稿，不是播出时钟 |
| `make_film_narration.py` | 整片 TTS → 归一化 → 章节卡静音 → 拍边界 → `timeline.json` + `subtitles.json` | 播出时钟的唯一来源 |
| `make_music_bed.py` | 按 `timeline.json` 合成音乐铺底 | 长度精确到采样；片尾终止和弦 |
| `mix_film_music.py` | 音乐 EQ/ducking/终混/归一化 | 输出 `film_full_scored.mp3` |

> **关键顺序**：改完 `timeline_source.json` 后必须重跑 `make_film_narration.py`。只跑 `make_timeline.py` 会把页面时钟退回编稿时长（例如 330 s），而音轨仍是实际旁白时长。

## 4. 数据契约

### 4.1 `timeline_source.json`（编稿，非播出）

```json
{
  "meta": {
    "title": "标题",
    "version": "v0.2",
    "built": "2026-10-17",
    "source": "pre-production/v0.2/pre-production.md",
    "source_note": "beat times and narration text transcribed from the script",
    "canvas": [1080, 1920],
    "fps": 30,
    "safe_x": 120,
    "duration": 330.0,
    "output": "post-production/timeline.json",
    "crumb_nodes": ["整机", "Channel", "DIMM", "Rank", "Chip", "Bank Group", "Bank", "MAT", "Cell"],
    "clock_note": "authored time; make_film_narration.py replaces it with TTS time"
  },
  "keywords": {
    "Channel": {"term": "Channel", "gloss": "一条独立的内存通道"}
  },
  "segments": [
    {
      "id": "S2a",
      "title": "从整机到内存条",
      "scene": "B",
      "pack": "S2a",
      "pack_status": "built",
      "budget": 36.0,
      "beats": [
        {
          "id": "s2ab1",
          "authored": [0.0, 8.0],
          "vo": "旁白原文。",
          "crumb": 1,
          "keywords": [{"key": "Channel", "at": 2.0}],
          "stage": [{"pack": "S2a", "beat": "b1_laptop", "at": 0.0}]
        }
      ]
    }
  ],
  "gates": [
    {"id": "G1", "type": "drill", "at": 30.0, "from": "S1", "to": "S2a", "target": "laptop screen", "sfx": "whoosh"}
  ]
}
```

字段规则：

- `authored` 是审稿秒数，不是播出秒数；`budget` 与 `authored` 的段和可以不一致，最终由 TTS 决定。
- `vo` 是 canonical 原文；读音层不写在这里。
- `crumb_nodes` 是**精炼关键词**（`flit`、`router`、`路由`），不是章节标题；单独建表维护（如 `toolbox/crumbs.json`：段 ID → 短词），不从章节卡标题批量填。
- `crumb` 是 `crumb_nodes` 的 **0-based 下标**，一节一项；`crumb_all: true` 表示整条点亮。生成端校验 `0 <= crumb < len(crumb_nodes)`。
- `keywords[].at` 是相对拍首的秒数；`stage[].at` 同理。
- `stage` 可以多条，表示同一拍内切换舞台；`kind`/`reuse`/`credits` 按项目扩展。
- `gates[].at` 在播出时会重定位到 `to` 段的第一拍。

### 4.2 spec JSON（坐标与文案的唯一来源）

每段一个，结构按项目定，但必须满足：

- 画布尺寸、安全边距、字号、颜色集中定义，不在脚本里散落。
- 每个元素有 `id`、`src`、`x/y/w/h`、`z`；坐标单位明确写"原图像素"或"舞台坐标"。
- 文本内容、字号、颜色、对齐方式写 spec，不写死在合成脚本。
- 蓝框/红标坐标用原始素材像素，导出时再缩放。
- 同一段的预览脚本与图层脚本读同一个 spec，避免两套坐标。

### 4.3 `elements.json`（页面绑定）

```json
{
  "chapter": "S2c",
  "canvas": [1080, 1920],
  "background": "canvas",
  "notes": "coordinates are stage pixels unless marked",
  "beats": [
    {
      "id": "b3_divide",
      "stage": "bank",
      "preview": "preview/stills/S2c_b3_divide_1080x1920.png",
      "images": [
        {"id": "chip", "src": "assets/layers/chip.png", "x": 180, "y": 700, "w": 720, "h": 420, "z": 10}
      ],
      "text": [
        {"id": "t1", "text": "Bank", "x": 540, "y": 1180, "size": 44, "color": "#E7E9EC", "anchor": "middle"}
      ],
      "vector": [
        {"id": "mark", "kind": "ring", "x": 300, "y": 760, "w": 120, "h": 120, "color": "#E14A2B"}
      ]
    }
  ]
}
```

规则：

- `src` 相对素材包目录；页面用 `import.meta.glob` 建 URL 索引，不拼字符串路径。
- `preview` 只给评审，不参与页面渲染。
- 文本与矢量由页面绘制；`images` 只放透明 PNG。
- 坐标约定写进 `notes`；`stage_label`/`ruler_label` 这类局部坐标要在消费端加舞台原点。
- 同一字段在不同段必须是同一类型（数组就是数组，对象就是对象）；页面消费端仍要防御性判断。

### 4.4 `timeline.json`（唯一播出时钟）

```json
{
  "meta": {
    "title": "标题",
    "version": "v0.2",
    "built": "2026-10-17",
    "source": "pre-production/v0.2/pre-production.md",
    "source_note": "...; beat times derived from one film-wide TTS render",
    "canvas": [1080, 1920],
    "fps": 30,
    "safe_x": 120,
    "duration": 284.75,
    "end_card": {"t0": 281.35, "t1": 284.75},
    "crumb_nodes": ["..."],
    "keywords": {"Channel": {"term": "Channel", "gloss": "..."}},
    "clock": {
      "mode": "audio",
      "note": "beat boundaries sit in the silence between spoken spans",
      "title_lead": 1.6,
      "track": "film_full_titled.mp3"
    },
    "counts": {"segments": 8, "beats": 68, "keywords_used": 9},
    "char_stats": [{"segment": "S1", "duration": 25.48, "cjk": 105, "full": 130, "cap": 107}],
    "unbuilt_packs": []
  },
  "segments": [
    {
      "id": "S1",
      "title": "从任务管理器开始",
      "scene": "A",
      "pack": "S1",
      "pack_status": "built",
      "t0": 0.0,
      "t1": 25.48,
      "card": null,
      "budget": 25.48,
      "authored_span": 30.0,
      "scale": 0.849,
      "align": "audio",
      "beats": [
        {
          "id": "s1b1",
          "segment": "S1",
          "t0": 0.0,
          "t1": 6.2,
          "dur": 6.2,
          "authored": [0.0, 7.0],
          "vo": "旁白原文。",
          "crumb": 0,
          "keywords": [{"key": "CPU-Z", "term": "CPU-Z", "gloss": "...", "at": 2.1, "t": 2.1}],
          "stage": [{"pack": "S1", "beat": "S1-03", "at": 0.0, "t": 0.0}]
        }
      ]
    }
  ],
  "gates": [{"id": "G1", "type": "drill", "from": "S1", "to": "S2a", "target": "...", "sfx": "whoosh", "at": 25.48}]
}
```

不变量（`check_film.py` 会检查）：

- `segments` 连续：`seg[i].t1 == seg[i+1].t0`（±0.02）。
- `beats` 在段内、按 `t0` 递增、互不重叠；`beat.id` 全局唯一。
- `card` 若存在，在段内且 `t0 == segment.t0`；`card.t1 == 第一条 beat.t0`。
- `end_card` 在 `duration` 内，且在最后一条 beat 之后。
- `keywords[].t == beat.t0 + at`；`stage[].t` 同理（生成端保证，校验端可抽查）。
- `beat.crumb` 落在 `[0, len(meta.crumb_nodes))`；越界是 ERROR（索引基写错的典型症状）。
- 最后一拍的 `t1` 可以超过音轨（片尾卡），但 `end_card.t0` 不应早于音轨结束。

### 4.5 `subtitles.json`

```json
{
  "version": 1,
  "source": "TTS sentence frames from one film-wide render",
  "clock": "absolute seconds from film start",
  "cues": [
    {"segment": "S1", "beat": "s1b1", "t0": 0.42, "t1": 2.10, "text": "字幕原文。"}
  ]
}
```

规则：

- 一条 cue = 一个 sentence frame；不要按字数切。
- `text` 用 canonical 原文（读音层反向还原）。
- cue 排序、互不重叠；`t1` 不越段末。
- 上屏最多两行；断行由 CSS `text-wrap: balance` + 宽度控制，不在 JSON 里插换行。

### 4.6 `reading_text.json`

```json
{
  "version": "1.0",
  "purpose": "朗读替身只作用于引擎文本，上屏使用 canonical 原文。",
  "substitutions": [
    {
      "id": "p-01",
      "canonical": "DRAM",
      "reading": "D ram",
      "expect_occurrences": 3,
      "issue": "引擎把全大写缩写逐字母读。",
      "why_this_reading": "小写 ram 作为英文实词读，前面的 D 按字母读。",
      "note": "上屏仍是 DRAM。"
    }
  ]
}
```

- 合成前校验整片 `canonical` 出现次数 == `expect_occurrences`，不符直接退出，不发起网络请求。
- 字幕生成时按 `reading → canonical` 反向替换；替换顺序与正向相反，避免嵌套替换。
- 替换会改变字符数，所以 frame→beat 映射先用字符位置精确匹配，失败后退到按字符质量比例分配。

## 5. 旁白与时间轴管线

`make_film_narration.py` 的推荐顺序（每一步缓存，显式 `--force-*` 才重跑）：

```text
1. text       校验读音层；写 .tmp/narration/film/film_canonical.txt 与 film_reading.txt
2. synth      整片一次 TTS → film_full.mp3 + film_full.mp3.json（sentence frames）
3. normalize  EBU R128 两遍 → film_full_norm.mp3 + .loudnorm.json
4. cards      在段界静音处拼入 TITLE_LEAD 秒静音 → film_full_titled.mp3
5. timing     sentence frames → 拍边界 → timeline.json
6. report     每段 narration.json + subtitles.json
```

### 5.1 合成

- 文本：所有 `vo` 按段/拍顺序直接拼接，**不加停顿标记、不加标题**；章节卡是画面，不是朗读内容。
- 请求参数（示例默认）：`voice-id zh_female_vv_uranus_bigtts`、`sample-rate 24000`、`format mp3`、`speech-rate 0`、`loudness-rate 0`、`emotion neutral`、`emotion-scale 4`、`language zh-cn`。
- 一次请求的文本有长度上限；超长时按叙事单元分段渲染，并在拼接前验证音色/语速一致。禁止按拍请求。
- sentence frame 必须带 `words[].startTime/endTime`；没有词级时间的响应不能用于拍边界。
- 代理环境：把 TTS 域名加入 `NO_PROXY`/`no_proxy`，否则 urllib3 可能报 `check_hostname requires server_hostname`。

### 5.2 归一化

- 两遍 `loudnorm`：`I=-16`, `TP=-1.5`, `LRA=11`。
- 第一遍后读 `measured_after.true_peak_dbtp`；若 > `TP + 0.01`，用 `--dynamic` 重跑。
- 报告落盘（JSON），后续混音/终检引用实测值，不引用目标值。
- 不要把归一化后的音频再次用 gain 调整；要改响度就重跑归一化。

### 5.3 章节卡静音拼接

- 在每段第一条拍的实际起点前插入 `TITLE_LEAD` 秒静音。
- 拼接点必须在两句旁白之间；由于拍边界已经落在静音里，直接用拍起点。
- 实现：`atrim` 分段 + `anullsrc` + `concat`；保持采样率/声道数与源一致。
- 拼接后所有拍/字幕时间整体后移；不重新合成 TTS。
- 卡片窗口：`segment.card = {t0: seg_t0, t1: seg_t0 + TITLE_LEAD}`。

### 5.4 拍边界算法

对每个拍，取其 sentence frames 的 `[firstWordStart, lastWordEnd]`：

```text
beat[0].start = 0
for i > 0:
    gap = span[i].start - span[i-1].end
    if gap < 0.2:
        beat[i].start = span[i-1].end + gap / 2      # 背靠背，取中点
    else:
        beat[i].start = max(span[i-1].end + MIN_GAP, span[i].start - ONSET)
beat[last].end = span[last].end + TAIL
beat[i].end   = beat[i+1].start
```

常量起点：

| 常量 | 值 | 含义 |
|---|---|---|
| `ONSET` | 0.33 s | 画面在第一个字之前多久切换 |
| `MIN_GAP` | 0.12 s | 切点离上一句结尾的最小距离 |
| `TAIL` | 1.2 s | 最后一拍在末字后的停留 |
| `TITLE_LEAD` | 1.6 s | 章节卡静音时长 |
| `END_CARD` | 3.4 s | 片尾 logo 卡时长 |
| `CHAR_RATE` | 4.2 字/s | 字数预算/统计，不参与切点 |

- 如果 `gap < 0`（引擎时间戳重叠），按 0 处理并告警；不要生成负时长。
- 拍边界递增校验失败直接退出，不写半成品 timeline。
- 段边界 = 该段第一拍 `t0`；章节卡占用 `[t0-lead, t0]`。
- 最后一拍的 `t1` 之后可以接片尾卡；片尾卡不进旁白时长统计。

### 5.5 关键词与舞台绑定重映射

编辑稿的 `keywords[].at` / `stage[].at` 是相对拍首的秒数；拍长变化后按比例缩放：

```text
new_at = clamp(at / authored_dur * new_dur, 0, new_dur - 0.05)
absolute_t = beat.t0 + new_at
```

- 同一拍内多个舞台按 `at` 排序；页面取最后一个已到点的。
- 关键词徽标可取 `t <= now` 的最后一个；段内保持，直到下一个关键词。
- 不在页面里写死 `at`；只读 timeline。

### 5.6 字幕生成

- 对每个拍，取分配给它的 sentence frames；反向还原读音层。
- `t0 = firstWord.start + card_shift`；`t1 = lastWord.end + card_shift`。
- 停留延长：`hold_end = t1 + 0.35`，再夹到下一 cue 的 `t0` 与段末。
- 结果按 `t0` 排序写 `subtitles.json`。
- 段末最后一句不得伸进下一段的章节卡；`check_film.py` 会报越段。

### 5.7 画面返工不重录旁白

只改面包屑、关键词、版式、素材时，旁白文本没变，就不要重新合成：

```bash
python make_film_narration.py --root <task_root>   # 不加 --force-synth，复用缓存 mp3
python build_scenes.py --root <task_root>          # 重出 web/data/scenes.json
```

- 重跑后 `meta.duration` 与 cue 数应完全不变；变了说明文本被动过，回头查读数层，不要继续渲染。
- 之后只重录画面；音乐与终混不用重跑。
- 改画面之前先停掉在跑的渲染任务（见 `pitfalls.md` 8.6）。

## 6. 播放页架构

### 6.1 目录

```text
post-production/web/
├── src/
│   ├── App.tsx                 # 全片时钟、段切换、覆盖层、字幕
│   ├── data/film.ts            # Timeline 类型 + segmentAt/beatAt/activeKeyword/stageLayers
│   ├── data/packs.ts           # elements.json 汇总 + import.meta.glob 图层 URL
│   ├── data/subtitles.ts       # cue 查询
│   ├── data/audioTracks.ts     # 旁白/终混轨
│   ├── lib/usePlayback.ts      # rAF 主时钟、键盘、?t 起始
│   ├── lib/useAudioSync.ts     # 音频跟时钟（单侧 250 ms 校正）
│   ├── scenes/                 # S1 / PackScene / 复盘场景
│   └── components/             # Stage、TitleCard、EndCard、Breadcrumb、KeywordBadge、BrandMark、SubtitleBand、SafeGuides、Transport
├── vite.config.ts              # avatar host/port、fs.allow、@film/@pack/@brand 别名
└── package.json
```

### 6.2 时钟与播放

- `usePlayback`：`performance.now()` + rAF 计算 `now`；循环播放；Space 播放/暂停，←/→ ±1 s，Home 回段首。
- `?t=SEC`：设置起始时间并暂停，用于定帧评审。
- `?autoplay=1`：自动播放；浏览器可能禁止无手势有声播放，需按一次 Space。
- `?record=1`：隐藏控制条与时间码，录屏用。
- `?badge=KEY`：强制显示某个关键词徽标，评审用。
- `?safe=1`：叠加安全区参考框，评审用。

### 6.3 音频同步

- 全片一条音轨（终混或旁白）；`audio.currentTime` 跟随主时钟。
- 只在 `|audio.currentTime - now| > 0.25` 时 seek，且**单侧**：音频落后才追，不反复双向拉扯。
- 当 `now` 超过音轨时长（片尾卡），暂停音频，不 seek 到越界位置。
- 页面加载后 `decodeAudioData` 校验实际时长；MP3 容器时长可能有编码器 padding，以浏览器解码为准（见 `pitfalls.md`）。

### 6.4 舞台与内容居中

- 一个固定 1080×1920 舞台，CSS transform 等比缩放到视口；不要用响应式重排改变构图。
- `PackScene` 每拍测量可见元素（`.stage-panel`、`.stage-image`、`.text-layer > *`）的包围盒，把整拍平移到内容中心（如 y=900），并夹在 `[332, 1410]`。
- 同一拍内元素一起移动，避免分步出现时抖动。
- 跳过 SVG 与非 HTMLElement（没有 `offsetTop/offsetHeight`）；跳过整帧图层（宽度接近画布），否则包围盒永远等于全屏。
- 文本层与图片层用同一坐标基准；舞台局部坐标要加舞台原点。

### 6.5 覆盖层与卡片

- 面包屑、关键词徽标、品牌标常驻；章节卡/片尾卡期间隐藏。
- 面包屑内容是**精炼章节关键词**（`flit`、`router`、`路由`），不是章节标题；整条常显，`beat.crumb` 指向的那一节用正文色，其余压暗，`/` 分隔符用发丝色。参考版式：28 px、18 px 间距、`opacity 0.95`，x 对齐页面安全边（本页 120），一条 9 节约 1240 px。
- 品牌已经由右上标承担时，面包屑不再加"品牌 / 项目"前缀，只讲位置。
- 章节卡：不透明底清屏，只留段标题、朱红短线、品牌标；淡出 0.28 s 接回舞台。
- 片尾卡：清屏后 logo 从 0.58 倍放大到 1.0（约 1.2 s，easeOutCubic）后停住。
- 字幕：底部 1434–1542，最多两行，英文词高亮。
- 安全区参考框只在 `?safe=1` 显示，不参与录屏。

### 6.6 构建与别名

- Vite `server.fs.allow` 放到任务根，允许直接引用 `production/.../layers`，不复制素材。
- 别名：`@film` → `post-production`，`@pack` → `production/<version>`，`@brand` → 品牌资产目录。
- `assetsInlineLimit: 0`，避免大图被内联进 JS。
- `npm run build` = `tsc --noEmit && vite build`；交付前必须过类型检查。

快速预览（不装 Vite）用一个静态服务器，文档根设成根绝对路径的公共父目录（通常是任务根）：

```bash
python -m http.server 5191 --bind 127.0.0.1 --directory <task_root>
```

端口自选并用 curl 验证本任务独有的文件（HTTP 200 不代表是你的服务）；`http.server` 无 Range，大音频首拖会等整段下载。细节见 `pitfalls.md` 4.11 / 4.12。

## 7. 音乐与终混

### 7.1 方案选择

1. **本地合成铺底**（首选，若没有可靠授权素材）：可精确对齐时间轴、无授权风险、可复现。
2. **免版权音乐**：确认许可覆盖商用/平台分发，保留授权页与下载日期。
3. **不用音乐**：必须取得用户明确同意，并在 brief 记录。

### 7.2 合成铺底参考

- 长度 = `timeline.meta.duration`，采样率 48 kHz，立体声。
- 和弦循环按段落推进；章节卡前加 riser；片尾用终止和弦收束并淡出。
- 循环不能在片尾卡前提前停止；最后一个循环和弦要能与终止和弦衔接（避免半音冲突）。
- 所有包络/延迟以采样数计算，避免浮点秒数取整造成的一声爆音或空隙。

### 7.3 混音参数（起点）

| 参数 | 值 |
|---|---|
| 音乐铺底 | −29 LUFS |
| ducking 深度 | 8 dB（6–10 dB 可调） |
| attack | 40 ms |
| release | 700 ms |
| 旁白/终混 | −16 LUFS |
| true peak | ≤ −1.5 dBTP |
| EQ | HP 32 Hz, LP 6500 Hz, 3 kHz −3 dB (Q=1.0) |

流程：

1. 用旁白做 20 ms RMS / 10 ms hop 包络，阈值 −48…−30 dBFS。
2. 包络经一阶 attack/release 平滑，得到逐采样增益。
3. 音乐乘增益后与旁白相加。
4. 终混两遍归一化到 −16 LUFS；真峰超标先修动态，不硬限幅。
5. 输出 `film_full_scored.mp3` + JSON（实测响度/峰值/时长）。

### 7.4 分轨保留

- `film_full.mp3`：原始 TTS
- `film_full_norm.mp3`：归一化旁白
- `film_full_titled.mp3`：拼入章节卡静音
- `music_bed.wav`：音乐铺底
- `film_full_scored.mp3`：终混

改音乐只重跑 3–5；改旁白才重跑 1–3。

## 8. 验证方法

### 8.1 结构与时长

```bash
python <skill>/scripts/check_film.py --root <task_root> --audio <master.mp3>
```

检查段/拍连续性、卡片窗口、cue 越段、`crumb` 越界、音频与 `meta.duration` 偏差。`--strict` 把警告当错误。

### 8.2 响度

```bash
ffmpeg -hide_banner -nostats -i <master.mp3> \
  -af loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json -f null -
```

解析 stderr 的 JSON，核对 `input_i`、`input_tp`、`input_lra`。不要只看编码器标签。

终混 mp3 达标后，再对**交付的 MP4**跑同一测量：AAC 封装会让读数漂 0.1–0.3 LU，报告里两个都写。

### 8.3 浏览器解码

MP3 容器时长与解码时长可能差几十毫秒；用页面里的 `decodeAudioData` 得到实际可播放时长：

```js
const buf = await new AudioContext().decodeAudioData(arrayBuffer);
console.log(buf.duration);
```

以这个值作为页面时钟的边界；ffprobe 用于容器层检查。

### 8.4 CDP 定帧

```bash
# 先启动 Chrome（示例）
chrome --remote-debugging-port=9222 --window-size=1080,1920 about:blank

node scripts/cdp_capture.mjs \
  --url http://127.0.0.1:5180/ \
  --times 0,25.48,26.3,61.38,281.35,284.5 \
  --out .tmp/shots --selectors ".stage,.sub-band,.crumb"
```

- `Emulation.setDeviceMetricsOverride` 固定 1080×1920。
- 每个时间点 `?t=SEC&record=1` 导航，等字体/资源就绪后截图。
- 同时输出 `captures.json`，含每个 selector 的 `x/y/w/h` 与视口尺寸。
- 用截图检查：安全区、卡片、字幕、元素是否越界；用 JSON 检查数值，不靠目测。

### 8.5 页面自检清单

- `npm run build` 通过。
- `?t=` 定帧在刷新后一致。
- 段边界前后各 0.2 s 音画同点。
- 章节卡期间无字幕/面包屑/关键词。
- 片尾卡放大后停住，不循环、不闪回。
- 控制条在 `?record=1` 下完全隐藏。

## 9. 交付编码

```bash
ffmpeg -y -i recording.mkv \
  -vf "scale=1080:1920:flags=lanczos,fps=30" \
  -c:v libx264 -profile:v high -pix_fmt yuv420p -crf 18 -maxrate 12M -bufsize 24M \
  -c:a aac -b:a 192k -ar 48000 \
  -movflags +faststart master.mp4
```

- 竖屏：1080×1920 / 30 fps；横屏按 brief。
- 录屏源分辨率必须等于目标；缩放只做兜底，不靠放大补细节。
- 交付前检查首帧、尾帧、黑帧、静音、章节卡、片尾卡。
- 封面单独出：竖屏 1080×1920，主体在中部，文字在信息流缩略图下可读。

### 9.1 发布元数据

标题、简介、标签、章节时间戳属于交付物，不是发布当天的即兴写作。落一份
`post-production/publish/metadata.json`，作为这些文案的唯一来源；平台后台、封面文案、
README 与发布清单都从它取，不要各写一套（写两套就会漂移）。

| 字段 | 内容 | 来源 |
|---|---|---|
| `title` | 主标题，含一个能复述的钩子 | brief / 片名卡 |
| `title_alternatives` | 1–2 个备选，按平台调性替换 | 编辑 |
| `short_description` | 约 100 字，含 5 个 `#` 话题 | 正文摘要 + `hashtags` |
| `long_description` | 平台正文，含事实口径说明 | 脚本 + 事实表 |
| `hashtags` | 3–8 个 `#` 话题，上屏用 | 选题关键词 |
| `tags` | 检索标签，可与话题不同 | 选题关键词 |
| `cover` | 横竖封面路径 | `covers/` |
| `media` | 母版路径、时长、分辨率、帧率、实测响度 | `timeline.json` / ffprobe |
| `chapters` | `mm:ss` 起点 + 章节标题 | `timeline.json` 各段 `t0` |
| `credits` | 旁白音色、来源表、素材许可出处 | research / resource |

- 时长与章节起点**派生**，不手抄；成片返工导致时长或分段变化时重算。
- 简介里的每个数字都要能回到事实表；口径边界（"参考实现指标"还是"硅测量"）在长简介里写明。
- 只改文案不触发重录；文案改完不必重出画面。
- 校验：`python <skill>/scripts/check_publish.py --root <task_root>`，可加 `--video` 核对 MP4 实际时长。

## 10. 凭证与隐私

- TTS/API key 只从环境变量或项目 `.env` 读取，例如 `DOUBAO_SPEECH_API_KEY`（变量名可换，值绝不入仓）。
- 共享客户端负责加载 `.env`；业务脚本不打印 key，不把 key 写进请求日志/异常。
- `run.bat`、`timeline.json`、`subtitles.json`、`review.md`、截图里都不得出现 key。
- 交付前跑：

```bash
python <skill>/scripts/check_secrets.py <task_root>
python <skill>/scripts/check_ascii.py <task_root>
```

- 原始素材中的水印/隐私信息按作者授权处理；不要默认"裁掉就行"，先确认。
