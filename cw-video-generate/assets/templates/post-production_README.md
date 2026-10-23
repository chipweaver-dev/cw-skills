# Post-production - {{TITLE}} ({{VERSION}})

本目录是**播出时钟与成片渲染**，不是剪辑工程。

## 文件

| 文件 | 说明 |
|---|---|
| `timeline.json` | 唯一播出时钟；由 `make_film_narration.py` 生成 |
| `timeline.lock.json` | 锁画快照；冻结后不再改画面 |
| `subtitles.json` | 行级字幕 cue；一条对应一个 TTS sentence frame |
| `audio/film/film_full.mp3` | 原始 TTS |
| `audio/film/film_full_norm.mp3` | 归一化旁白 |
| `audio/film/film_full_titled.mp3` | 拼入章节卡静音 |
| `audio/film/music_bed.wav` | 音乐铺底 |
| `audio/film/film_full_scored.mp3` | 终混 |
| `web/` | Vite + React + TS 播放页 |

## 播放页

```bat
cd web
npm install
npm run dev
```

打开 `http://127.0.0.1:5180/`。录屏前设 1080x1920、30 fps，使用 `?record=1` 隐藏控制条。

## 评审参数

| 参数 | 作用 |
|---|---|
| `?record=1` | 隐藏控制条与时间码 |
| `?autoplay=1` | 自动播放（可能需一次手势才有声） |
| `?t=SEC` | 冻结在指定秒 |
| `?badge=KEY` | 强制显示关键词徽标 |
| `?safe=1` | 显示安全区参考框 |

键盘：Space 播放/暂停，左右方向键 ±1 s，Home 回段首。

## 生成顺序

```text
make_film_narration.py  -> timeline.json + subtitles.json + 旁白
make_music_bed.py       -> music_bed.wav
mix_film_music.py       -> film_full_scored.mp3
```

只跑 `make_timeline.py` 会退回编稿时钟；改完文稿必须重跑 `make_film_narration.py`。

## 交付前

- `npm run build` 通过
- `check_film.py --root .. --audio audio/film/film_full_scored.mp3`
- 全片过一遍：段边界、章节卡、片尾卡、字幕、安全区、响度
- 录屏 -> H.264/AAC MP4 -> 封面 -> 字幕 -> 元数据
