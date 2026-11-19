---
name: chinese-pdf-report
description: 在 iSH 上用 reportlab 生成中文 PDF 报告（错题分析、学习总结、数据报告、说明文档等）。当用户要求"生成 PDF / 导出 PDF / 做成 PDF / 出个报告"且内容含中文时使用。内含中文字体处理方案与 JSON→PDF 渲染引擎，可直接产出带标题、对照表、色块标题、页脚的 A4 报告。
---

# 中文 PDF 报告生成

用 `reportlab` 把结构化内容渲染成 A4 中文 PDF。**不要自己从零写 reportlab 代码**——字体和版式的坑都在脚本里处理好了。

## 一、一键流程

```bash
# 1) 准备中文字体（幂等，只需一次；已存在会直接跳过）
python3 /var/minis/skills/chinese-pdf-report/scripts/setup_font.py

# 2) 写规格 JSON，然后渲染
python3 /var/minis/skills/chinese-pdf-report/scripts/build_report.py spec.json /var/minis/workspace/报告.pdf
```

规格可以**先用 Python 脚本生成 JSON**（数据与排版分离），再调用渲染——内容多时比手写 JSON 可靠。

## 二、规格速查

```json
{
  "title": "主标题", "subtitle": "副标题（可省）", "footer": "页脚文字",
  "blocks": [ ... ]
}
```

| block | 用途 | 关键字段 |
|---|---|---|
| `h2` / `h3` | 章节 / 小节标题 | `text` |
| `p` | 正文段落（支持 `<b>`、`<font color='#B4232A'>`） | `text` |
| `note` | 灰色小字（备注、结论） | `text` |
| `banner` | 深色通栏分区标题 | `text` |
| `bar` | 每题的深蓝标题条（左粗右细双栏） | `left`(给 `<b>`)、`right`、`left_w`(mm，默认26) |
| `kv` | 两列对照表（如"你的答案 / 正确答案"） | `pairs`、`colors` |
| `ul` | 带彩色小标题的条目列表 | `title`、`title_color`、`marker`、`items`、`indent` |
| `table` | 数据表 | `header`、`rows`、`widths`(mm)、`center_cols`、`stripe`、`last_row_bg` |
| `group` | 包成 `KeepTogether`，防止跨页断开 | `blocks` |
| `hr` / `space`(`h`) / `pagebreak` | 分隔线 / 留白 / 分页 | — |

题型/考点条 + 答案对照表建议用 `group` 包住，避免标题条和表格被分到两页。

## 三、必知的字体坑

`apk add font-noto-cjk` 装的 **NotoSansCJK 是 CFF/PostScript 轮廓，reportlab 直接拒绝**：

```
TTFError: postscript outlines are not supported
```

所以 `setup_font.py` 用的是**文泉驿正黑**（TrueType 轮廓），并把它从 `.ttc` 拆成单体 `.ttf`（产物默认 `/root/wqy.ttf`，可复用）。
另外：**文泉驿没有真粗体**，`build_report.py` 已把 bold 映射到同一字体——所以层级要靠**颜色、底色、字号**来体现，`<b>` 只是语义标记，视觉上不会变粗。

### 3.1 两个已内置/需注意的细节
- 引擎的 `S()` 基样式带 `wordWrap='CJK'`。若去掉，中文长段只能按空格断行，首行会留大片空白（表现为“一行只有几个字就换行”）。
- **文泉驿正黑缺字形**（会渲染成空白/方块）：`−`(U+2212 数学减号)、`•`(U+2022)、`⁻`(U+207B)、`✔`/`✘`、`⟺`(U+27FA，但 `⇔`U+21D4 有)。
  可用替代：减号用 `–`(U+2013) 或 `-`，圆点用 `·`(U+00B7)，对勾用【对】【错】，等价号用 `⇔`。
  下标的 `₁₂₃₄`、`²`、`≤ ≥ → Δ μ √ × ½ ⅓` 都在，放心用。
  写完后可用 `python3 -c "from fontTools.ttLib import TTFont; cm=TTFont('/root/wqy.ttf').getBestCmap(); print(ord(c) in cm)"` 逐个查。

## 四、交付前必须校验渲染效果

```bash
apk add poppler-utils                                  # 只需一次
pdftoppm -png -r 70 报告.pdf /root/pg && ls /root/pg*   # 再逐页 read_image 看
```

必看项：
- 有没有 Markdown 残留（`**加粗**` 忘了写 `<b>`）；
- 表格有没有溢出页宽（`widths` 之和别超过正文宽度 ≈ 176mm）；
- 题目块有没有被不合理地拆页；
- 中文有没有变方块/空白（字体没加载成功）。

## 五、故障表

| 现象 | 原因 | 处理 |
|---|---|---|
| `postscript outlines are not supported` | 误用了 Noto CJK | 改用 `setup_font.py` 导出的 `/root/wqy.ttf` |
| 中文显示为空白/方块 | 字体文件缺失或路径错 | 检查 `theme.font` 指向的文件是否存在 |
| `<b>` 报错 `Can't map determine family` | 没注册字体族 | 用本引擎（已 `registerFontFamily`） |
| 表格超出右边界 | `widths` 之和过大 | 正文宽 = A4(210mm) − 2×margin(17mm) ≈ 176mm |
| 页面底部被切 | `bottomMargin` 太小 | 引擎默认 18mm，页脚占 13mm |
