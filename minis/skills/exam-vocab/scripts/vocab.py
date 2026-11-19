#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PDF -> 生词表 HTML（牛津高阶 CEFR 分级 + 原文对照 + 打印）
用法: python3 vocab.py 试卷.pdf [--b1] [--out 目录]
"""
import re, sys, os, json, sqlite3, subprocess, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("OALD_DB", "/var/minis/shared/词典索引/oald.db")
TPL = os.path.join(HERE, "..", "assets", "template.html")
if not os.path.exists(TPL):
    TPL = os.path.join(HERE, "template.html")

STOP = set("""a an the i you he she it we they me him her them us my your his its our their this that these those
is am are was were be been being do does did done have has had having will would can could may might must shall should
and or but if so as than then there here what which who whom whose when where why how not no nor too very also just
only even still yet about above after again against all any both each few more most other some such own same
of in on at to for from by with without into onto over under between among through during before after up down out off
one two three four five six seven eight nine ten first second next last
yes oh ok ok mr mrs ms dr etc""".split())

IRR = {'mice':'mouse','teeth':'tooth','feet':'foot','children':'child','men':'man','women':'woman',
 'people':'people','does':'do','did':'do','done':'do','was':'be','were':'be','been':'be','is':'be','are':'be','am':'be',
 'has':'have','had':'have','went':'go','gone':'go','came':'come','came':'come','took':'take','taken':'take',
 'made':'make','said':'say','saw':'see','seen':'see','knew':'know','known':'know','thought':'think',
 'found':'find','gave':'give','given':'give','told':'tell','became':'become','left':'leave','felt':'feel',
 'brought':'bring','began':'begin','begun':'begin','kept':'keep','held':'hold','wrote':'write','written':'write',
 'stood':'stand','heard':'hear','let':'let','meant':'mean','met':'meet','ran':'run','paid':'pay','sat':'sit',
 'spoke':'speak','spoken':'speak','lay':'lie','led':'lead','grew':'grow','grown':'grow','lost':'lose',
 'fell':'fall','fallen':'fall','sent':'send','built':'build','understood':'understand','drew':'draw',
 'drawn':'draw','broke':'break','broken':'break','spent':'spend','cut':'cut','rose':'rise','risen':'rise',
 'drove':'drive','drawn':'draw','chose':'choose','chosen':'choose','wore':'wear','worn':'wear',
 'won':'win','sold':'sell','taught':'teach','caught':'catch','fought':'fight','sought':'seek','bought':'buy',
 'thought':'think','brought':'bring','strove':'strive','striven':'strive','arose':'arise','awoke':'awake',
 'froze':'freeze','frozen':'freeze','stole':'steal','stolen':'steal','hid':'hide','hidden':'hide',
 'threw':'throw','thrown':'throw','flew':'fly','flown':'fly','blew':'blow','blown':'blow',
 'swam':'swim','swum':'swim','sang':'sing','sung':'sing','rang':'ring','rung':'ring','drank':'drink','drunk':'drink',
 'ate':'eat','eaten':'eat','got':'get','gotten':'get','forgot':'forget','forgotten':'forget'}

def lemmas(w):
    out = [w]
    if w in IRR: out.insert(0, IRR[w])
    if w.endswith("'s"): out.append(w[:-2])
    if w.endswith("ies") and len(w) > 4: out.append(w[:-3] + "y")
    if w.endswith("es") and len(w) > 3: out += [w[:-1], w[:-2]]
    if w.endswith("s") and len(w) > 3 and not w.endswith("ss"): out.append(w[:-1])
    if w.endswith("ied") and len(w) > 4: out.append(w[:-3] + "y")
    if w.endswith("ed") and len(w) > 3:
        out += [w[:-2], w[:-1]]
        if len(w) > 4 and w[-3] == w[-4]: out.append(w[:-3])
    if w.endswith("ing") and len(w) > 4:
        out += [w[:-3], w[:-3] + "e"]
        if len(w) > 5 and w[-4] == w[-5]: out.append(w[:-4])
    if w.endswith("ly") and len(w) > 3: out += [w[:-2], w[:-2] + "e"]
    if w.endswith("er") and len(w) > 3: out += [w[:-2], w[:-2] + "e"]
    if w.endswith("est") and len(w) > 4: out += [w[:-3], w[:-3] + "e"]
    return out

def pdf_text(path):
    if path.lower().endswith(".pdf"):
        r = subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", path, "-"],
                           capture_output=True, text=True)
        if r.returncode != 0: sys.exit("pdftotext 失败: " + r.stderr[:300])
        return r.stdout
    return open(path, encoding="utf-8", errors="replace").read()

HEAD = re.compile(r'^\s*(第[一二三四五六七]部分|第[一二三四五]节|[A-D]\s*$|[A-D][.、]\s|PART\s+[IVX]+|Section\s+[A-D])')

def build_sections(raw):
    """按 页/标题 切块，返回 [(title, [(lineno, text)])]"""
    pages = raw.split('\f')
    secs, cur, title, ln = [], [], None, 0
    for pi, page in enumerate(pages):
        for line in page.split('\n'):
            ln += 1
            t = line.strip()
            if not t: continue
            if HEAD.match(t) and len(t) < 40 and cur:
                secs.append((title, cur)); cur, title = [], t
                continue
            if title is None:
                title = t[:28]
            cur.append((ln, t))
        if cur:
            secs.append((title, cur)); cur, title = [], None
    return [(t or f'第{i+1}段', c) for i, (t, c) in enumerate(secs) if c]

def main():
    args = sys.argv[1:]
    if not args: sys.exit(__doc__)
    path = args[0]
    min_lv = 'b2'
    for a in args:
        if a == '--b1': min_lv = 'b1'
    name = os.path.splitext(os.path.basename(path))[0]
    name = re.sub(r'^(shared-[0-9A-F]+_)?', '', name)

    raw = pdf_text(path)
    secs = build_sections(raw)
    con = sqlite3.connect(DB)
    cache = {}
    def look(key):
        if key in cache: return cache[key]
        r = con.execute("SELECT lv,pos,en,cn,ex,score FROM w WHERE key=?", (key,)).fetchone()
        cache[key] = r
        return r

    out_secs = []
    for si, (title, lines) in enumerate(secs):
        seg = ' '.join(x[1] for x in lines)
        sents = [s.strip() for s in re.split(r'(?<=[.!?。])\s+', seg) if s.strip()]
        words, seen = [], set()
        for _, t in lines:
            for m in re.finditer(r"[A-Za-z][A-Za-z'\-]*", t):
                tok = m.group(0); w = tok.lower()
                if w in STOP or len(w) < 3 or w in seen: continue
                best, src = None, None
                for v in lemmas(w):
                    r = look(v)
                    if r and (best is None or r[5] > best[5]):
                        best, src = r, v
                capitalized = tok[0].isupper()
                # 词典里无 CEFR 等级的大写词 = 人名/地名/机构名，整词大写缩写（PFAS/STEM）保留
                if best and not best[0] and capitalized and not tok.isupper():
                    continue
                if not best:
                    # 未收录：可能是超纲词/缩写，排除人名式首字母大写
                    if capitalized or not w.isalpha() or len(w) < 4: continue
                    lv = 'x'; pos = ''; en = ''; cn = ''; ex = []
                else:
                    lv = best[0] or 'x'
                    if lv in ('a1', 'a2'): continue
                    if lv == 'b1' and min_lv == 'b2': continue
                    pos, en, cn = best[1], best[2], best[3]
                    ex = [x.split('\t') for x in (best[4] or '').split('\n') if x]
                seen.add(w)
                base = w if w in (src, tok.lower()) else (src or w)
                stem = base[:-1] if len(base) > 4 and base.endswith('e') else base
                cands = [s for s in sents if re.search(r'(?<![A-Za-z])' + re.escape(stem), s, re.I)]
                cands.sort(key=len)
                ctx = cands[0][:200] if cands else t[:160]
                words.append(dict(w=src or w, pos=pos, cn=cn or '—', note='', lv=lv,
                                  en=en, dex='', ex=ex, ctx=ctx))
        if words:
            out_secs.append(dict(id=f's{si}', title=title[:34], text=seg,
                                 lines=[[n, t] for n, t in lines], words=words))

    data = dict(sections=out_secs)
    tpl = open(TPL, encoding='utf-8').read()
    html = tpl.replace('__DATA__', json.dumps(data, ensure_ascii=False, separators=(',', ':')))
    html = html.replace('__TITLE__', name)
    outdir = '/var/minis/attachments'
    for i, a in enumerate(args):
        if a == '--out' and i + 1 < len(args): outdir = args[i + 1]
    out = os.path.join(outdir, f"{name}_生词表.html")
    os.makedirs(outdir, exist_ok=True)
    open(out, 'w', encoding='utf-8').write(html)
    n = sum(len(s['words']) for s in out_secs)
    print(f'OK  {out}   {n} 词 / {len(out_secs)} 段   {os.path.getsize(out)//1024} KB')

if __name__ == '__main__':
    main()
