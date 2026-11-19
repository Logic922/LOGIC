---
name: exam-vocab
description: 把英语试卷（PDF/图片转出的文字）整理成按 CEFR 分级的生词表单文件 HTML。用于「做生词表」「试卷字词分析」「把这张卷子的生词整理出来」「词汇梳理/分级」「B2 以上难词」等请求。产出 Vim 风深色词表：搜单词或中文、板块/等级筛选、A→Z、原文对照点词查义、★标记、A4 打印。
---

# 试卷生词表（exam-vocab）

输入一份英语试卷，产出**单文件 HTML 生词表**：每段（听力/A/B/C/D/七选五/完形/语法/写作）
一组词，词条带 CEFR 等级、词性、中文释义、原文语境，能搜索、能筛选、能打印。

**只交付 HTML，不转 PDF**（渲染 PDF 又慢又不方便改，用户明确要求过）。

## 一、先取文本

```sh
pdftotext -layout -enc UTF-8 试卷.pdf /tmp/paper.txt   # 先用 pdfinfo 看页数
sed -n '1,80p' /tmp/paper.txt                          # 确认抽出来的是正常英文
```

- 抽出来是乱码/空/半角全丢 ⇒ 扫描件，先用 `apple-vision ocr` 或让用户发文字稿。
- 抽出来是图片型 PDF 时也可以直接用 `apple-vision document`，但**别**逐页截图读图。

## 二、跑脚本

```sh
python3 /var/minis/skills/exam-vocab/scripts/vocab.py /tmp/paper.txt --out /var/minis/attachments
# --b1 放宽到 B1（默认只收 B2/C1/C2 + 未收录的超纲词/短语）
```

实测 3 秒出结果，输出 `附件/<卷名>_生词表.html`（`shared-XXXX_` 前缀会自动去掉）。
脚本会打印 `OK 路径 N词 / M段 / KB`。

## 三、必须做的自检（不能省）

1. **看板块数对不对**：`M段` 应≈卷面板块数。切块靠 `第二部分 / A / B / C…` 这类行首，
   版面特殊时会多切或少切 —— 多了就在 `build_sections()` 的 `HEAD` 正则里加规则。
2. **抽查覆盖率**：把词表 dump 出来，对着原文扫一遍，看有没有明显漏掉的高难词：
   ```sh
   python3 - <<'EOF'
   import re,json
   h=open('/var/minis/attachments/XX_生词表.html',encoding='utf-8').read()
   d=json.loads(re.search(r'const DATA = (\{.*?\});',h,re.S).group(1))
   for s in d['sections']:
       print('##',s['title'],len(s['words']));print(', '.join(f"{w['w']}({w['lv']})" for w in s['words']))
   EOF
   ```
   漏的典型原因：词形还原没覆盖（`-ise/-ment/-ity` 派生词、不规则动词）、
   词被拆行/带连字符、首字母大写的专名被误滤。**难词宁多勿漏，熟悉词别堆**。
3. **浏览器看一眼**：`minis://attachments/XX_生词表.html`（或 workspace 副本），确认
   首屏、原文对照、中文搜索（输入「免疫」这类中文能命中）、A→Z 都正常。

## 四、能改什么

| 想改 | 改哪 |
|---|---|
| 收录门槛（B1/B2/C1） | `vocab.py` 里 `lv in ('a1','a2')` / `--b1` |
| 释义/例句字段 | `assets/template.html`（`rowHTML` / `detHTML`） |
| 配色、字体、打印页边距 | `assets/template.html` 顶部 `:root` 变量与 `@media print` |
| 顶栏标题 | 脚本用文件名替换 `__TITLE__`，或直接传改好的 `--out` 名 |
| 词形还原规则 | `vocab.py` 的 `lemmas()` 与 `IRR` 不定式表 |

`assets/template.html` 里 `const DATA = __DATA__;` 是唯一数据入口，脚本把 JSON 注入此处。

## 五、词典与依赖

- 释义库：`/var/minis/shared/词典索引/oald.db`（牛津高阶10 英汉双解 → SQLite，
  298866 词条，含 `lv`(CEFR)/`pos`/`en`/`cn`/`ex`/`score`）。缺失时用
  `scripts/build_index.py`（需要 `readmdict` + `python-lzo` + 原 MDX）重建，约 3 分钟。
- 只需要 `pdftotext`（poppler）和 Python 标准库，无需联网。

## 六、经验（别踩）

- **A1/A2 一律丢**，否则整页都是 the/get 这种；A2 里真正难的小词（如 `cope`）可在需求里点名放行。
- 无 CEFR 等级的**大写词**按人名/地名/机构名丢掉；全大写缩写（PFAS/STEM）保留原形。
- 未收录的小写词（`nonprofit`、`subsidize`、`harvested` 之类新词/派生词）标为「超纲」保留，
  这往往是学生最需要背的。
- 熟词僻义（`address v. 处理`、`observe v. 遵守`）自动释义只会给出首义，需在 `note` 里手写提示。
- prints: 打印媒体里必须把配色变量全部改成黑白/浅色，否则深色背景会印出来。
