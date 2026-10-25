---
name: cw-video-generate
description: 端到端制作知识讲解类视频（默认竖屏 1080x1920，中文旁白 + 字幕 + 低存在感背景音乐）：从选题与资料核实、pre-production 文档、透明素材与机制示意图、整片 TTS、音频主导时间轴、Vite/React 播放页与录屏，到混音、终检和平台交付。当用户要求制作、继续、返工、拆解或评审一个知识视频/科普视频/技术讲解视频，或需要设计旁白、分镜、字幕、时间轴、动态信息图、播放页，或排查音画不同步、字幕漂移、响度/音乐、素材坐标与竖屏安全区问题时使用。也用于把已有视频项目沉淀成可复用流程。不用于纯 NLE 手动剪辑、无旁白的素材集锦、纯 3D 动画或真人出镜口播。
---

# cw-video-generate：知识讲解视频生成

## 1. 目标与验收标准

把"一个知识点 + 一批可溯源素材"变成可发布的知识讲解视频：旁白、画面、字幕、音乐共用一条时钟，所有事实可回溯，所有素材可授权，整个工程可重建。

六条硬指标（缺一不可）：

1. **音画同源**：画面与字幕只读 `timeline.json`，不存在第二套时钟；任意 `?t=` 定帧与同秒音轨一致。
2. **时长由声音决定**：拍长来自实际 TTS 渲染的 sentence frame 与静音间隙，不来自文稿估算；成片时长写入 `meta.duration`。
3. **字幕逐句对齐**：每条 cue 来自一个 TTS sentence frame，行级高亮，不越段、不伸进章节卡，数字与画面完全一致。
4. **事实可溯源**：每个上屏数字都能在 research 事实表中找到来源；查不到就写 N/A 或删除，不用模型记忆填空。
5. **素材可交付**：真实图有 URL 与许可记录，示意图与图表为自绘，页面合成层为透明底；无 AI 伪造历史影像。
6. **响度与音乐达标**：旁白 −16 LUFS、TP ≤ −1.5 dBTP；音乐在旁白下有 ducking，响度不压过旁白；无音乐必须取得用户明确同意。

## 2. 适用 / 不适用

**适用**：

- 技术、器件、架构、原理、历史演进类知识视频（横屏或竖屏均可）。
- 需要中文旁白 + 字幕 + 背景音乐 + 动态信息图 + 录屏交付的完整工程。
- 已有项目需要继续做、改版、返工、评审，或把流程沉淀给下一个任务。
- 需要诊断音画不同步、字幕漂移、素材坐标错位、响度异常、页面定帧不稳等问题。

**不适用**（改用相应工具）：

- 纯 NLE 手动剪辑、调色、特效合成 → Premiere / DaVinci / After Effects。
- 无旁白的素材集锦、MV、纯音乐视频 → 直接剪辑，不需要本 skill 的音频主导时钟。
- 真人出镜口播 → 摄像机 + 提词器流程，本 skill 只借用其中的事实与字幕规范。
- 纯 3D 动画或游戏引擎过场 → Blender / Unreal 流程。

## 3. 核心心智模型

### 3.1 声音拥有时钟

先合成旁白，再让画面服从旁白。TTS 返回的 sentence frame 给出每句的起止时间；拍边界放在两句之间的静音里，而不是按文稿字数硬切。文稿阶段只给预算，不给最终秒数。

这条规则的价值在于：改写一句旁白不会让后面所有镜头错位，因为时间轴是从新音频重新推导的，而不是手工平移。

### 3.2 单一事实源，逐层收窄

```text
pre-production.md（意图、脚本、分镜、视觉规范）
        ↓ 只提取，不二次创作
timeline_source.json（段/拍/旁白/关键词/舞台绑定）
        ↓ 整片 TTS + 静音拼接 + 边界推导
timeline.json（唯一播出时钟）+ subtitles.json
        ↓ 只读
Vite/React 播放页 → 录屏 → 成片
```

- 数字只从 research 事实表进入脚本；script / storyboard / 页面不得二次转述或"顺手改一个数"。
- 坐标只从 spec JSON 进入合成脚本；页面不得再维护一套手调偏移。
- 任何一层发现上游错误，回到上游改，不在下游打补丁。

### 3.3 素材是零件，页面是舞台

真实图片、芯片/器件抠图、机制示意图以透明底元素交付；背景、面板、排版、红色标记、光晕、面包屑、关键词徽标、字幕由页面统一绘制。这样换背景、改字号、加安全区参考框都不必重做素材，也不会出现"文字烘焙进图里、页面又画一遍"的重影。

预览静帧（`previews/*.png`、contact sheet）只用于评审，不是交付素材。最终静帧只保留 `_plate.png` 这类不含页面覆盖层的底板。

### 3.4 一次成型，版本返工

- 整片只发一次 TTS 请求（或每个叙事单元一次并验证音色一致），避免逐拍请求造成的音色、语速、情绪漂移。
- 整片只做一次终混；改音乐不重录旁白，改旁白不重做音乐。
- 返工开新版本目录（`v0.2`、`v0.3`），不覆盖已批准版本；`review_log.md` 记录每次批准与返工原因。
- **版本号跨阶段对齐**：版本号属于成片，不属于阶段。`pre-production` 是 v0.2，`production`、`post-production` 就都是 v0.2；后面的阶段允许没有 v0.1，从前一阶段批准的号直接起步。

### 3.5 门禁评审，不一次性跑完

17 个制作步骤分三阶段，每阶段一个正式 Gate；对不可逆或返工昂贵的产物再加内部检查点（brief、script、storyboard、asset list、page clock、mix）。没有 `Approved` 不进入下一阶段。

## 4. 工作流总览

| 阶段 | 步骤 | 正式门 | 主产物 | 详细规则 |
|---|---|---|---|---|
| P0 立项 | 确认 brief、建任务目录、核对素材 | — | `pre-production/<version>/`、`production/<version>/` | `references/workflow.md` §2 |
| P1 前期 | 1 选题 → 2 大纲 → 3 脚本 → 4 分镜 → 5 视觉风格 → 6 素材清单 | **Gate 1** | `pre-production.md`、`research/`、`resource/` | `references/workflow.md` §3；`references/authoring.md` |
| P2 制作 | 7 素材生成 → 8 配音 → 9 音乐音效 → 10 图形动画 | **Gate 2** | 透明素材包、整片旁白、`timeline.json`、页面 | `references/pipeline.md` |
| P3 后期 | 11 粗剪 → 12 锁画 → 13 调色 → 14 混音 → 15 字幕 → 16 母版 → 17 平台版本 | **Gate 3** | 成片 MP4、封面、字幕、元数据 | `references/pipeline.md` §7 |
| 交付 | 平台适配、发布清单、归档 | 发布前检查 | 交付包 | `references/checklists.md` §7 |

**内部检查点**（建议全部保留，可按项目删减但要在 brief 说明）：

- C1 brief 批准（总时长、受众、平台、画幅、预算表）
- C2 script 批准（事实表核对完成、字数按实测语速反写）
- C3 storyboard / asset list 批准（每个型号有合规配图，找不到就换条目）
- C4 page clock 批准（`?t=` 定帧、段边界、字幕、章节卡）
- C5 mix 批准（旁白、音乐、ducking、片尾）

## 5. 快速开始

```text
0. 读项目 CLAUDE.md 与既有 brief，确认受众/平台/时长/画幅/风格/凭证来源。
1. 新建任务骨架：
   python <skill>/scripts/new_task.py <task_root> --title "<标题>"
2. 写 pre-production；数字逐条进 research 事实表并附来源。
3. 用 check_ascii.py 扫工程文件；用 check_film.py 扫时间轴与字幕。
4. 建透明素材包（elements.json + layers/*.png）与预览 contact sheet。
5. 整片一次 TTS → EBU R128 归一化 → 音频边界 → timeline.json + subtitles.json。
6. 起播放页（Vite/React/TS），用 ?t= 定帧评审；CDP 截图与量框。
7. 合成/授权音乐 → ducking 混音 → 终混 −16 LUFS。
8. 录屏 1080x1920/30 fps，出 MP4、封面、字幕；发布元数据（标题/简介/标签/章节）写进 `post-production/publish/metadata.json`；跑交付检查表。
```

常用命令（在 skill 目录下执行；参数以实际项目为准）：

```bash
python scripts/new_task.py ./my_task --title "My Topic"
python scripts/check_ascii.py ./my_task
python scripts/check_film.py --root ./my_task --audio ./my_task/post-production/audio/film/film_full_scored.mp3
python scripts/check_publish.py --root ./my_task --video ./my_task/post-production/film/master.mp4
node scripts/cdp_capture.mjs --url http://127.0.0.1:5180/ --times 0,26.3,62.2 --out ./my_task/.tmp/shots
```

## 6. 硬性红线

1. **不猜需求**：受众、平台、画幅、总时长、风格、是否要音乐、凭证来源，任何一项不清先问。
2. **不编事实**：模型记忆中的年份、规格、制程、速率一律视为未核实；查不到写 N/A，不用"大约/可能"填充。
3. **不伪造历史**：真实照片、实物、人物只能来自可溯源图库/厂商资料室/博物馆；结构示意图和数据图表自绘；禁止 AI 生成"历史照片"。
4. **不泄露凭证**：TTS/API key 只从环境变量或项目 `.env` 读取；不写入脚本、`run.bat`、timeline、日志、截图、review 文档。交付前跑 `check_secrets.py`。
5. **不设第二套时钟**：画面、字幕、音乐、音效都从 `timeline.json` 推导；禁止在页面里写死秒数或用手工偏移补偿。
6. **不逐拍请求 TTS**：整片一次渲染；确需分段时每段独立渲染并做拼接听感验证，不得在拍级切分。
7. **不把覆盖层烘焙进素材**：文字、面包屑、关键词、字幕、安全框由页面绘制；素材只交透明元素或底板。
8. **不混淆预览与交付**：contact sheet、review still 只用于评审；交付素材必须是无覆盖层的透明 PNG / 底板。
9. **工程文件纯 ASCII**：`.py/.bat/.sh/.ts/.tsx/.css` 等不得含中文或全角标点；中文只进 `.md` 和 JSON 数据。
10. **不跳过评审**：每个 Gate 必须有 `review.md` + `review_log.md`；未 Approved 不进入下一阶段。
11. **不交付未验证的响度**：旁白/终混必须实测 −16 LUFS、TP ≤ −1.5 dBTP；真峰超标先重跑 `--dynamic`。
12. **不越过竖屏安全区**：顶部平台 UI、底部字幕/按钮区、右栏互动区都要留白；禁止横屏构图直接裁切。
13. **版本号跨阶段对齐**：`pre-production` / `production` / `post-production` 用同一个成片版本号；后段允许没有 v0.1，但不许各阶段各编一套号。

## 7. 参考索引

| 文件 | 何时读 |
|---|---|
| `references/workflow.md` | 开工、建目录、排期、过 Gate、版本返工 |
| `references/authoring.md` | 写 brief / 脚本 / 分镜 / 视觉规范 / 旁白 / 字幕 |
| `references/pipeline.md` | 搭 toolbox、写合成/TTS/时间轴/页面/混音脚本，查数据契约 |
| `references/pitfalls.md` | 遇到音画、字幕、素材、混音、页面、编码异常时先查这里 |
| `references/checklists.md` | 每次 Gate 评审与最终交付前逐项勾选 |
| `scripts/new_task.py` | 新建任务骨架（复制模板） |
| `scripts/check_ascii.py` | 扫非 ASCII 工程文件 |
| `scripts/check_film.py` | 校验 timeline / subtitles / 音频时长一致性 |
| `scripts/check_secrets.py` | 扫疑似凭证，交付前必跑 |
| `scripts/check_publish.py` | 校验发布元数据与成片是否一致（片长、章节、话题、封面） |
| `scripts/cdp_capture.mjs` | 通过 Chrome DevTools Protocol 定帧截图与量框 |
| `scripts/*.py` 源码 | 仅维护升级时阅读；日常使用看 `--help` |

## 8. 维护约定（面向维护者）

- **分层原则**：SKILL.md 只放目标、心智模型、流程与红线；方法在 `references/`；确定性检查在 `scripts/`；模板在 `assets/templates/`。改一层不牵连其他层。
- **新增制作环节**：先判断它属于哪个阶段与哪个 Gate → 在 `workflow.md` 加步骤与验收 → 在 `checklists.md` 加勾选项 → 必要时加脚本与模板。
- **新增踩坑**：只记录"症状 → 根因 → 修法"可复现的条目；一次性环境问题不进 `pitfalls.md`。
- **脚本升级**：保持 CLI 向后兼容；新增参数给默认值；错误信息必须指出文件与字段。
- **凭证**：任何示例、模板、脚本都不得出现真实 key、token、密码或私有 URL；只写环境变量名与占位符。
- **修改任何文件时更新下方版本表。**

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0.0 | 2026-10-17 | 初始版本：从 DRAM 子系统层次结构视频项目抽象出 17 步 / 3 Gate 流程、音频主导时钟、透明素材 + 页面合成、混音与踩坑库 |
| 1.0.1 | 2026-10-23 | 面包屑契约补全（精炼关键词 + 0-based 高亮，见 `pipeline.md` §4.1 / §6.5）；新增踩坑 2.12–2.13、4.11–4.12、5.11、6.6–6.7、7.14、8.6–8.7；新增 §5.7 画面返工不重录旁白；`workflow.md` 返工表补面包屑行；`check_ascii.py` 跳过 `.tmp`；`check_film.py` 校验 `crumb` 越界与"标题当关键词" |
| 1.0.2 | 2026-10-23 | 发布元数据成为交付物：新增 `pipeline.md` §9.1（`post-production/publish/metadata.json` 字段与派生规则）、`check_publish.py`、模板 `assets/templates/publish_metadata.json`（`new_task.py` 同步生成）；`workflow.md` 步骤 17 与返工表补元数据行；`checklists.md` §7 拆出 5 项；新增踩坑 8.8 与分诊行 |
| 1.0.3 | 2026-10-24 | 版本号跨阶段对齐：`pre-production` / `production` / `post-production` 共用一个成片版本号，后段允许缺 v0.1（`workflow.md` §1.2、§7 返工表；`pitfalls.md` 7.5；`checklists.md` §1；`new_task.py` 版本参数说明） |
