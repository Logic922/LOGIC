---
name: dictation-sheet
description: 把英语作文/课文/倡议书做成「Vim 编辑器风」递进挖词默写单（单文件 HTML，可打印）。用于「做默写单」「挖空默写」「递进式默写」「单词挖空练习」「把这篇作文做成默写」等请求。固定四档累计空数 12 → 20 → 30 → 49，只挖词、不放词库，末页全文绿色标出被挖的词。
---

# 英语递进挖词默写单（dictation-sheet）

输入一篇约 150–220 词的英语短文，产出**单文件 HTML**：4 档递增挖空 + 末页全文，
Vim 编辑器浅色风（tabline、行号栏、NORMAL 状态栏），A4 直接打印，一档一页。

**格式是定稿的，不要自己加花样。** 用户明确砍掉过：词块表、汉译英、中文提纲回译、
独立答案页、词库、干扰项、五级递进。只有：四档挖词 + 末页全文。

## 一、先拿文本

- 用户发图片/PDF：`apple-vision ocr` 或 `pdftotext -layout`，然后**逐句录入**成文本，
  不要保留硬换行（一句话一行）。
- 用户发文字：直接整理，保留原文用词与标点（破折号、分号照抄）。

## 二、标档位

一句话一行，两种标记：

```text
Knowing our school English newspaper is collecting opinions, I am most {eager|1} to {recommend|1} music.
*To begin with*, music offers a {much-needed|2} {escape|1} from {endless|2} papers and exams.
```

- `{word|n}`：这个词从**第 n 档**开始被挖掉（n = 1 最易 → 4 最难）。空数由标记决定，
  档位数字只是"从哪一档开始空"，所以第 4 档是累加最多的。
- `*...*`：连接词/逻辑词按 Vim 关键字蓝色高亮（`To begin with`、`More importantly`、
  `Last but not least`、`rather`、`However`）。

分档原则：

| 档 | 放什么 | 例 |
|---|---|---|
| 1 | 必会核心动词/形容词，情绪或主张落点 | eager, recommend, escape, precious, sharpens, confidence |
| 2 | 中档搭配、抽象名词 | much-needed, endless, concentration, creativity, all-round |
| 3 | 需要搭配才知道用法的词 | refresh, recharge, energy, focus, composing, strengthen |
| 4 | 一般实词、短语、虚用词 | best choice, provides, means, waste, qualities, long run |

目标累计空数 **12 → 20 → 30 → 49**（比例约 1 : 1.7 : 2.5 : 4）。
短语（`best choice`、`out of the box`）也算一个词条，空位会自动加宽。

## 三、生成

```sh
python3 /var/minis/skills/dictation-sheet/scripts/gen.py 文章.txt \
    --title "Music Class 建议信" --en-title "A Valuable Addition" \
    --slug music-class --expected 12,20,30,49
# 先看空数不改文件：加 --check
```

- 默认输出 `/var/minis/shared/默写单/<slug>/vim.html`（归档规矩：一项目一子目录）。
- 空数不符 `--expected` 会**直接报错退出**并列出差异 —— 这是最主要的自检，
  改完 `{...|n}` 重新跑，直到四档全对。
- 交付副本再 `cp` 到 `/var/minis/attachments/<卷名>_默写单.html`，方便点开/打印。
- 顺手在 `/var/minis/shared/默写单/README.md` 的索引表里加一行。

## 四、检查

1. `--check` 四档空数对得上（12/20/30/49，或用户指定别的数）。
2. `minis://shared/默写单/<slug>/vim.html` 打开看一眼：每档一页、空位没撑破行、
   蓝色逻辑词没漏、末页被挖词都是绿色。
3. 一档页不能把一句话拆到两页（`.buf` 已有 `page-break-after: always`，一档一块）。

## 五、改样式

`scripts/gen.py` 顶部 `CSS` 常量就是全部样式；`buf()` 是每个 Vim 窗口块的模板。
改配色/字体/空位宽度只动这两处，然后重跑脚本。空位宽度公式
`max(3.6, len(word)*0.62 + 1.9)em`，宽词的格子适合长短语。

## 六、经验（别踩）

- **只挖词**，不改原句、不做同义替换、不留中文对照（不是阅读课，是默写）。
- 一页 = 一档，四档 + 全文 = 5 页；文章长的可只出 3 档，但 `--expected` 要跟着改。
- `html, body { -webkit-text-size-adjust:100% }` 必须留着，否则 iOS WebKit 会把
  `p` 字号放大到 1.7 倍导致溢版（踩过）。
- 打印用浅色省墨配色；深色 Vim 风只用于「生词表」（那是另一个 skill：`exam-vocab`）。
- 不加 JavaScript：纯静态单文件，分享给别人也能打开。
