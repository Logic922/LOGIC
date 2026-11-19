# -*- coding: utf-8 -*-
"""把牛津高阶10 MDX 建成 SQLite 索引，供生词表脚本秒查。只需跑一次。"""
import re, sqlite3, os, sys
from readmdict import MDX

P = "/var/minis/shared/最新版牛津高阶10英汉双解v14.3/牛津高阶（第10版 英汉双解） V14_3.mdx"
OUT = "/var/minis/shared/词典索引/oald.db"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
if os.path.exists(OUT) and '--force' not in sys.argv:
    print('exists:', OUT); sys.exit(0)

TAG = re.compile(r'<[^>]+>')
def plain(s):
    s = TAG.sub('', s).replace('&amp;', '&').replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>')
    return re.sub(r'\s+', ' ', s).strip()

con = sqlite3.connect(OUT)
con.execute("""CREATE TABLE IF NOT EXISTS w(
  key TEXT PRIMARY KEY, lv TEXT, pos TEXT, en TEXT, cn TEXT, ex TEXT, score INT)""")
con.execute("CREATE INDEX IF NOT EXISTS k ON w(key)")

m = MDX(P, encoding="utf-8")
rows = {}
for k, v in m.items():
    key = k.decode('utf-8', 'replace').strip().lower()
    if not key or len(key) > 40: continue
    s = v.decode('utf-8', 'replace')
    lv = re.search(r'cefr="([abc][12])"', s) or re.search(r'level=([abc][12])', s[:3000])
    head = re.search(r'<h1 class="headword"[^>]*>(.*?)</h1>', s)
    hp = plain(head.group(1)) if head else key
    d = re.search(r'<span class="def"[^>]*>(.*?)</span>', s)
    c = re.search(r'<span class="def"[^>]*>.*?</span>\s*<defT>\s*<chn>(.*?)</chn>', s, re.S) or re.search(r'<chn>(.*?)</chn>', s)
    pos = re.search(r'<span class="pos"[^>]*>(.*?)</span>', s)
    ex = []
    for mm in re.finditer(r'<span class="x">(.*?)</span>(.*?)(?=<span class="x">|</li>|$)', s, re.S):
        en = plain(mm.group(1)); cc = re.search(r'<chn>(.*?)</chn>', mm.group(2))
        if en: ex.append(en[:150] + '\t' + (plain(cc.group(1))[:110] if cc else ''))
        if len(ex) >= 2: break
    sc = (2 if lv else 0) + (1 if d else 0) + (1 if hp.lower() == key else 0)
    if key not in rows or sc > rows[key][-1]:
        rows[key] = (key, lv.group(1) if lv else '', plain(pos.group(1))[:24] if pos else '',
                     plain(d.group(1))[:200] if d else '', plain(c.group(1))[:80] if c else '',
                     '\n'.join(ex), sc)
con.executemany("INSERT OR REPLACE INTO w VALUES(?,?,?,?,?,?,?)", rows.values())
con.commit()
print('rows', len(rows))
