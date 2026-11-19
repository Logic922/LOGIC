# LOGIC

**🌐 在线作品集：[logic922.github.io/LOGIC](https://logic922.github.io/LOGIC/)**

一个 iOS 上的个人仓库：AI 助手的配置、自己做的教学演示，还有一些奇怪小东西。
全部是**纯前端 / 单文件 / 无构建**的东西——丢进浏览器就能跑，不需要 npm、不需要联网（除了调外部 API 的那几个）。

```
LOGIC/
├── minis/              Minis 助手配置：人格、全局提示词、技能库
├── projects/
│   └── 教学模拟/        物理 / 化学课堂演示与动画
└── 奇怪小制作/          Chat.html — 单文件聊天界面
```

---

## minis/ — AI 助手配置

Minis 是 iOS 上的 AI 助手，内置 iSH / Alpine Linux 环境，可以跑真实 shell 命令。
这里备份它的人格文件、全局提示词和自建技能库。

| 文件 | 说明 |
|---|---|
| `GLOBAL.md` | 全局提示词：思考纪律、精确编辑、收尾清理、LaTeX 排版、联网检索偏好 |
| `SOUL.md` + `SOUL.icon.png` | 人格（语气、习性、底线）与图标 |
| `skills/` | 12 个技能，每个含 `SKILL.md`（+ 可选 `scripts/`、`references/`） |

### 技能清单

**iOS / iSH 环境**

| 技能 | 用途 |
|---|---|
| `drawthings-ios-draw` | 调 iOS 本机 Draw Things 的 HTTP API 出图（Illustrious SDXL），含探活判据与耗时基线 |
| `ish-multithread-download` | iSH 里用 curl Range 分片并发下载 GB 级文件（aria2 在 iSH 上必崩） |
| `ish-hash-verify` | iSH 里校验完整性：大小判据 + 抽样哈希，避免对 GB 文件跑 sha256sum 把设备烤了 |

**生成与排版**

| 技能 | 用途 |
|---|---|
| `math-figure` | matplotlib 中文 + 数学公式混排教学图，带 mathtext 报错对照与越界/重叠自检 |
| `chinese-pdf-report` | reportlab 中文 PDF 报告（JSON → A4 排版引擎） |
| `physics-sim-video` | 把物理题做成带中文标注的模拟视频（离屏渲染 + 编码流程） |

**教学工具**

| 技能 | 用途 |
|---|---|
| `dictation-sheet` | 英语短文 → Vim 风四档递进挖词默写单（单文件 HTML，可打印） |
| `exam-vocab` | 英语试卷 → 按 CEFR 分级的生词表 HTML（需牛津高阶词典索引） |
| `listening-audio-analysis` | 听力音频转写成中英对照原文，结合试卷照片做逐题解析 |

**工程纪律**

| 技能 | 用途 |
|---|---|
| `precise-code-edit` | 精确编辑已有代码：计数断言替换 + 语法/悬空引用/清单 diff 四级自检 |
| `code-review-subagent` | 编辑后派子代理通读整文件复核，迭代到收敛 |
| `skill-creator` | 编写 / 更新技能的规范指南 |

**还原方法**：`skills/*` 放进 `/var/minis/skills/`，`GLOBAL.md`、`SOUL.md` 放进 `/var/minis/memory/`。

---

## MIDI8BIT — 独立项目

在线版：[logic922.github.io/MIDI8BIT](https://logic922.github.io/MIDI8BIT/) · 源码：[Logic922/MIDI8BIT](https://github.com/Logic922/MIDI8BIT)

单文件 8-bit MIDI 播放器（Web Audio，示波器 / 音符卷帘 / 播放列表 / 后台预渲染 / 四档位深导出），
带 manifest + service worker，可装到桌面当 PWA 用。源码与构建流程在本仓库之外单独维护。

---

## projects/教学模拟/ — 课堂演示

单文件 HTML / 纯前端，双击即开，无需联网。

| 条目 | 知识点 | 形态 |
|---|---|---|
| [CO2制甲醇演示](projects/教学模拟/CO2制甲醇演示/) | CO₂ 加氢制甲醇的分流机制与速率 | 双页 HTML |
| [凹槽传送带动画](projects/教学模拟/凹槽传送带动画/) | 相对运动 / 传送带模型 | HTML + CSS + JS |
| [圆环三球](projects/教学模拟/圆环三球/) | 圆周运动、约束与能量 | 动画 + 解法页 |
| [波沙盒](projects/教学模拟/波沙盒/) | 波的干涉、衍射（惠更斯） | Three.js 3D 沙盒 |
| [圆环碰撞.html](projects/教学模拟/圆环碰撞.html) | 三球圆环 · 运动动画 | 单文件 |
| [摆的沙盒.html](projects/教学模拟/摆的沙盒.html) | 单摆 / 动铰摆 | 单文件 |
| [斜面圆弧动铰摆.html](projects/教学模拟/斜面圆弧动铰摆.html) | 斜面 + 圆弧 + 动铰摆复合运动 | 单文件 |

---

## 奇怪小制作/ — Chat.html「月见 · 私语」

40 KB 单文件聊天界面，深色玻璃拟态，手机端优先。

- 可填任意 OpenAI 兼容的 `baseUrl`（默认 DeepSeek）+ API Key，流式输出
- Key 只存 `localStorage`，页面里没有硬编码密钥
- 背景图走 `api.waifu.best` 随机图接口，可调标签 / 分级 / 方向
- 零依赖，打开即用

---

## 说明

- 代码以实用为主，注释是给自己看的，不保证对外可读性。
- 教学模拟里的 `.html` 多为一次性作品，数值与题意对齐某个具体题目，泛用性有限。
- `minis/skills` 里的经验条目多来自实际踩坑，换环境未必复现。
