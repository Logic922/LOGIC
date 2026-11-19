#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""英语递进挖词默写单生成器（Vim 浅色风，单文件 HTML，可直接打印）

用法:
  python3 gen.py article.txt --title "Music Class 建议信" [--slug music-class]
                 [--out 目录] [--expected 12,20,30,49] [--check]

article.txt 一行一句，两种标记:
  {word|2}   这个词从 Stage 2 开始被挖掉（1 最易 → 4 最难）
  *To begin with*   星号内按 Vim 关键字蓝色高亮（连接词/逻辑词）

默认输出：/var/minis/shared/默写单/<slug>/vim.html
"""
import re, sys, os, html, argparse

TOKEN = re.compile(r"\{([^}|]+)\|(\d)\}|\*([^*]+)\*")

CSS = """
* { box-sizing: border-box; }
body { margin:0; background:#ffffff; color:#24292f;
  font-family:"Liberation Mono","Noto Sans Mono CJK SC","Courier New",monospace;
  font-size:13.5px; line-height:1.85; -webkit-text-size-adjust:100%; text-size-adjust:100%; }
.wrap { max-width: 900px; margin: 0 auto; padding: 18px 14px 40px; }
h1 { font-size: 15px; font-weight: 400; color:#1f2328; margin:0 0 2px 0; letter-spacing:.5px; }
h1 .v { color:#2f7d32; }
.cmd { color:#6b7280; font-size:12px; margin:0 0 14px 0; }
.cmd i { color:#8a6d00; font-style:normal; }
.buf { border:1px solid #dcdfe4; border-radius:4px; margin:0 0 20px 0; overflow:hidden;
       background:#fdfdfd; page-break-inside: avoid; }
.tabline { display:flex; background:#eef0f3; border-bottom:1px solid #dcdfe4; font-size:11.5px; }
.tab { padding:5px 12px; color:#6b7280; border-right:1px solid #e1e4e8; }
.tab.act { background:#ffffff; color:#1f2328; box-shadow: inset 0 2px 0 #1a5fb4; }
.tab .dot { color:#8a6d00; }
.bufbody { padding:10px 0 6px 0; counter-reset: ln; }
.ln { display:flex; }
.ln::before { counter-increment: ln; content: counter(ln); flex:0 0 3.2em; text-align:right;
  padding-right:1.1em; color:#b9c0c8; font-size:12px; user-select:none; }
.tx { flex:1; padding-right:12px; text-align:left; }
.tx .kw { color:#1a5fb4; }
.tx .sol { color:#2f7d32; }
.hl { display:inline-block; height:1.02em; vertical-align:-0.16em; margin:0 1px;
  background:rgba(120,130,140,.13); border-bottom:1px solid #9aa0a6; border-radius:2px; }
.mk { color:#b3261e; font-size:9.5px; vertical-align:super; }
.status { display:flex; justify-content:space-between; background:#eef0f3; color:#57606a;
  font-size:11px; padding:3px 10px; border-top:1px solid #dcdfe4; }
.status .mode { background:#1a5fb4; color:#ffffff; padding:0 8px; font-weight:bold; }
.status .r { color:#8a6d00; }
.sec { color:#6b7280; font-size:12px; margin:0 0 8px 2px; }
@media print {
  @page { size:A4; margin:9mm; }
  body { background:#ffffff !important; font-size:12.5px; }
  .wrap { max-width:none; padding:0; }
  .buf { page-break-after: always; }
  .buf:last-child { page-break-after: auto; }
}
"""


def render(text, stage, full=False):
    out, n, pos = [], 0, 0
    for m in TOKEN.finditer(text):
        out.append(html.escape(text[pos:m.start()]))
        pos = m.end()
        if m.group(1):
            word, s = m.group(1), int(m.group(2))
            if full:
                out.append('<span class="sol">%s</span>' % html.escape(word))
            elif s <= stage:
                n += 1
                w = max(3.6, len(word) * 0.62 + 1.9)   # 空位宽度跟着词长走
                out.append('<span class="hl" style="width:%.1fem"></span><span class="mk">%d</span>' % (w, n))
            else:
                out.append(html.escape(word))
        else:
            out.append('<span class="kw">%s</span>' % html.escape(m.group(3)))
    out.append(html.escape(text[pos:]))
    return "".join(out), n


def buf(fname, title, lines, mode="NORMAL", right="", sub=""):
    return "\n".join([
        '<div class="buf">',
        '<div class="tabline"><span class="tab act"><span class="dot">●</span> %s</span>'
        '<span class="tab">%s</span></div>' % (html.escape(fname), html.escape(title)),
        '<div class="bufbody">',
        "".join('<div class="ln"><span class="tx">%s</span></div>' % L for L in lines),
        '</div>',
        '<div class="status"><span><span class="mode">%s</span> &nbsp;%s &nbsp;·&nbsp; %s</span>'
        '<span class="r">%s</span></div>' % (mode, html.escape(fname), html.escape(sub), right),
        '</div>',
    ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("article")
    ap.add_argument("--title", default=None, help="页眉中文说明，如「Music Class 建议信」")
    ap.add_argument("--en-title", default=None, help="英文副标题（默认取文件名）")
    ap.add_argument("--slug", default=None, help="目录名，默认取文件名")
    ap.add_argument("--out", default=None, help="输出根目录，默认 /var/minis/shared/默写单")
    ap.add_argument("--stages", default="1,2,3,4", help="要出的档位，逗号分隔")
    ap.add_argument("--expected", default="", help="每档期望空数，如 12,20,30,49；不符则报错退出")
    ap.add_argument("--check", action="store_true", help="只打印各档空数，不写文件")
    a = ap.parse_args()

    raw = open(a.article, encoding="utf-8").read()
    SENT = [L.strip() for L in raw.split("\n") if L.strip() and not L.strip().startswith("#")]
    if not SENT:
        sys.exit("文章为空")

    stages = [int(x) for x in a.stages.split(",")]
    counts = {st: sum(render(t, st)[1] for t in SENT) for st in stages}
    print("空数:", "  ".join("S%d=%d" % (k, v) for k, v in counts.items()))
    if a.expected:
        exp = [int(x) for x in a.expected.split(",")]
        bad = [(s, e, counts.get(s)) for s, e in zip(stages, exp) if counts.get(s) != e]
        if bad:
            sys.exit("期望不符: " + ", ".join("S%d 期望%d 实际%s" % b for b in bad))
    if a.check:
        return

    slug = a.slug or os.path.splitext(os.path.basename(a.article))[0]
    root = a.out or "/var/minis/shared/默写单"
    outdir = os.path.join(root, slug)
    os.makedirs(outdir, exist_ok=True)
    fname = slug + ".txt"
    words = len(re.sub(r"[{}|*\d]", "", raw).split())

    parts = ['<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">',
             '<title>%s — 递进挖词默写</title>' % html.escape(fname),
             '<style>%s</style></head><body><div class="wrap">' % CSS,
             '<h1><span class="v">"%s"</span> — %s <span style="color:#5c6370">[utf-8]</span></h1>'
             % (html.escape(fname), html.escape(a.en_title or a.title or "")),
             '<p class="cmd">":set number" &nbsp;挖词逐级递增 %s，最后一页为全文。&nbsp; '
             '填完再 <i>:set nonumber</i> 默一遍。</p>'
             % " → ".join(str(counts[s]) for s in stages)]

    for i, st in enumerate(stages):
        parts.append('<p class="sec">-- Stage %d / %d &nbsp;·&nbsp; %d blanks --</p>'
                     % (i + 1, len(stages), counts[st]))
        parts.append(buf(fname, "stage%d" % (i + 1), [render(t, st)[0] for t in SENT],
                         sub="Stage %d/%d · %d blanks" % (i + 1, len(stages), counts[st]),
                         right="%d%%" % int((i + 1) * 100 / len(stages))))
    parts.append('<p class="sec">-- EOF · 全文（绿色＝上面被挖掉的词） --</p>')
    parts.append(buf(fname, "full text", [render(t, 0, True)[0] for t in SENT],
                     mode="READ", sub="全文 · %d words" % words, right="100%"))
    parts.append('</div></body></html>')

    out = os.path.join(outdir, "vim.html")
    open(out, "w", encoding="utf-8").write("\n".join(parts))
    print("OK  %s  %d 句 / %d 页  %.1f KB" % (out, len(SENT), len(stages) + 1, os.path.getsize(out) / 1024))


if __name__ == "__main__":
    main()
