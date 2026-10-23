# Toolbox - {{TITLE}} ({{VERSION}})

本目录只放可重复执行的单功能脚本与 JSON spec。复杂流程由 `../run.bat` 组合。

## 约定

- 一个脚本只做一件事：抠图、合成、导出、生成时间轴、混音。
- 入口参数统一：`--root <task_root>`、`--spec <spec.json>`、`--id <item>`。
- 所有坐标/字号/文案进 spec JSON；脚本里不散落业务常量。
- 脚本幂等；缓存产物用 `--force` 显式重跑。
- 工程脚本纯 ASCII；中文只进 Markdown / JSON 数据。
- 预览图（`preview/`）只用于评审；交付图层必须是透明 PNG 或 `_plate.png` 底板。

## 需要按任务补齐的脚本

| 脚本 | 用途 | 输入 | 输出 |
|---|---|---|---|
| `make_<seg>_layers.py` | 生成该段透明图层 | spec JSON | `<seg>/assets/layers/*.png` |
| `compose_<seg>.py` | 合成预览静帧 | spec JSON | `<seg>/preview/stills/*.png` |
| `make_cutout.py` | 真实图抠图 | spec JSON + 原图 | 透明 PNG |
| `make_contact_sheet.py` | 拼评审图 | 图片列表 | `preview/contact_sheet.png` |
| `make_film_narration.py` | 整片 TTS + 时间轴 + 字幕 | `timeline_source.json` | `post-production/timeline.json`、`subtitles.json` |
| `make_music_bed.py` | 合成铺底 | `timeline.json` | `post-production/audio/film/music_bed.wav` |
| `mix_film_music.py` | ducking + 终混 | 旁白 + 铺底 | `film_full_scored.mp3` |

## 常用命令

```bat
python make_film_narration.py --root ..\..\..
python make_music_bed.py --root ..\..\.. --force
python mix_film_music.py --root ..\..\..
```

## 数据契约

见 skill 的 `references/pipeline.md` §4：`timeline_source.json`、spec JSON、`elements.json`、`timeline.json`、`subtitles.json`、`reading_text.json`。

## 交付前

```bat
python <skill>\scripts\check_ascii.py <task_root>
python <skill>\scripts\check_film.py --root <task_root> --audio <master.mp3>
python <skill>\scripts\check_secrets.py <task_root>
```
