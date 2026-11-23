# Minis 助手配置备份（iOS）

Minis（iOS 上的 AI 助手，内置 iSH / Alpine Linux 环境）所用的人格、全局提示词与技能库备份。

## 目录结构

```
minis/
├── GLOBAL.md          # 全局提示词（硬性指令：思考纪律、编辑纪律、LaTeX 排版、检索偏好等）
├── SOUL.md            # 人格文件（猫娘人格：语气、习性、底线）
├── SOUL.icon.png      # 人格图标
└── skills/            # 技能库，每个子目录含 SKILL.md 及可选 scripts/ references/
```

## 技能清单

| 技能 | 用途 |
|---|---|
| `drawthings-ios-draw` | 调用 iOS 本机 Draw Things 的 HTTP API 出图（Illustrious SDXL），含探活判据与耗时基线 |
| `ish-multithread-download` | 在 iSH 里用 curl Range 分片并发下载 GB 级文件（aria2 在 iSH 上必崩） |
| `ish-hash-verify` | iSH 里校验文件完整性：大小判据 + 抽样哈希，避免对 GB 文件跑 sha256sum 烧设备 |
| `math-figure` | matplotlib 生成中文 + 数学公式混排的教学图，含 mathtext 报错对照与越界/重叠自检 |
| `chinese-pdf-report` | reportlab 生成中文 PDF 报告（JSON → A4 排版引擎） |
| `physics-sim-video` | 把物理题做成可交互的单文件 HTML 动画（Canvas 2D：播放/暂停/拖动/变速/关键帧跳转 + v-t 图） |
| `listening-audio-analysis` | 转写考试听力音频为中英对照原文，并结合试卷照片做逐题解析 |
| `precise-code-edit` | 精确编辑已有代码：计数断言替换 + 语法/悬空引用/清单 diff 四级自检 |
| `code-review-subagent` | 编辑后派子代理通读整文件复核并迭代到收敛的流程 |
| `dictation-sheet` | 把英语短文做成 Vim 风四档递进挖词默写单（单文件 HTML，可打印） |
| `exam-vocab` | 把英语试卷整理成按 CEFR 分级的生词表单文件 HTML（需牛津高阶词典索引） |
| `skill-creator` | 编写/更新技能的规范指南 |

## 使用

把 `skills/*` 放进 Minis 的 `/var/minis/skills/`，`GLOBAL.md`、`SOUL.md` 放进 `/var/minis/memory/`
（或在 Minis 设置 → Soul 里直接编辑）。技能在被需要时由 `SKILL.md` 加载。
