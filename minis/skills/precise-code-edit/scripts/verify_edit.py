#!/usr/bin/env python3
"""改完代码立刻自检：语法 / 顶层标识符清单 / 导出对象悬空引用。

用途（都是真实踩过的坑）
------------------------
1. `--syntax`      用 `node --check` 查语法错误。整页白屏通常就是这一步没过。
2. `--inventory`   列出全部顶层标识符；配合 `--baseline` 可对比「有没有多删/多写」。
   删除函数时最容易漏掉的是别处的引用。
3. `--exports`     找 `window.X = { ... }` / `module.exports = { ... }` / `export {...}`
   里的每个标识符，逐个检查是否真有定义。**这是最致命的一类机械损伤**：
   删掉一个函数后导出表还引用它 → ReferenceError → 整个导出失败，
   但页面照常显示、编译也过，只有 `typeof window.X` 才暴露。
4. `--unused`      列出「顶层定义了但全文只出现一次」的标识符，提示可能是死代码
   （删除前请人工确认，别被同名/字符串误伤）。

用法
----
verify_edit.py FILE [--syntax] [--exports] [--inventory] [--unused] [--all]
verify_edit.py FILE --all --baseline /tmp/inv_before.json --save-baseline /tmp/inv_after.json

输出 JSON；`ok` 为 false 时退出码 1。
"""
import argparse
import json
import os
import re
import subprocess
import sys

DECL_RE = re.compile(
    r"^(?:export\s+)?(?:async\s+)?"
    r"(?:function\s+|class\s+|const\s+|let\s+|var\s+)"
    r"([A-Za-z_$][\w$]*)")
FUNC_RE = re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)")
VAR_KINDS = {"const", "let", "var"}

BUILTINS = set("""
window document console globalThis self this arguments undefined null true false NaN Infinity
Math Object Array JSON String Number Boolean Symbol BigInt Promise Proxy Reflect
Map Set WeakMap WeakSet Date RegExp Error TypeError RangeError SyntaxError URIError
Uint8Array Int8Array Uint16Array Int16Array Uint32Array Int32Array Float32Array Float64Array
Uint8ClampedArray ArrayBuffer DataView TextEncoder TextDecoder Blob File FileReader URL
AudioContext OfflineAudioContext webkitAudioContext Audio GainNode OscillatorNode
navigator performance location localStorage sessionStorage history screen
setTimeout setInterval clearTimeout clearInterval setImmediate requestAnimationFrame
cancelAnimationFrame queueMicrotask structuredClone fetch crypto indexedDB IDBKeyRange
atob btoa parseInt parseFloat isNaN isFinite encodeURIComponent decodeURIComponent
encodeURI decodeURI alert confirm prompt getComputedStyle addEventListener
removeEventListener dispatchEvent CustomEvent Event MutationObserver ResizeObserver
HTMLElement Element Node NodeList Image Audio Option FormData Headers Request Response
MatchMedia matchMedia Intl escape unescape Function eval
as of in typeof instanceof new void delete return if else for while do switch case default
break continue try catch finally throw yield await async static get set class extends super
import export from let var const function
""".split())


REGEX_PREV = set("(,=:[!&|?{};+-*%~^<>")
REGEX_KEYWORDS = {"return", "typeof", "instanceof", "in", "of", "new", "delete",
                  "void", "case", "do", "else", "yield", "await", "throw"}


def looks_like_regex(src, i, last_sig):
    """判断位置 i 的 `/` 是正则字面量开头还是除号。

    启发式：`/` 前面是运算符/括号/逗号 → 正则；前面是标识符、数字、`)`、`]` → 除号。
    必须支持这一条，因为正则里可以出现引号（`/[&<>"]/g`），
    不识别就会把那个引号当成字符串开头，一路吞掉几十 KB 的代码。
    """
    if last_sig is None:
        return True
    if last_sig in REGEX_PREV:
        return True
    m = re.search(r"([A-Za-z_$][\w$]*)\s*$", src[:i])
    return bool(m and m.group(1) in REGEX_KEYWORDS)


def skip_regex(src, i):
    """从 i（指向起始 `/`）跳过整个正则字面量；失败返回 -1。"""
    n = len(src)
    j = i + 1
    in_class = False
    while j < n:
        ch = src[j]
        if ch == "\\":
            j += 2; continue
        if ch == "\n":                      # 正则不能跨行 → 判定失败
            return -1
        if in_class:
            if ch == "]":
                in_class = False
        elif ch == "[":
            in_class = True
        elif ch == "/":
            j += 1
            while j < n and src[j].isalpha():      # flags
                j += 1
            return j
        j += 1
    return -1


def strip_strings_and_comments(src):
    """把字符串/模板串/正则/注释替换成等长空白，保持偏移与括号结构。

    `last_sig` 跟踪「上一个有意义的字符」；已被当作操作数的字符串/正则视为
    标识符字符，这样 `"a".replace(/x/g)` 里的 `/` 不会被误判成正则。
    """
    out = []
    i, n = 0, len(src)
    last_sig = None
    while i < n:
        c = src[i]
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            j = n if j == -1 else j
            out.append(" " * (j - i)); i = j
        elif c == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            j = n if j == -1 else j + 2
            out.append(" " * (j - i)); i = j
        elif c in "\"'`":
            q = c
            j = i + 1
            while j < n:
                if src[j] == "\\":
                    j += 2; continue
                if src[j] == q:
                    j += 1; break
                j += 1
            out.append(" " * (j - i)); i = j; last_sig = "x"
        elif c == "/" and looks_like_regex(src, i, last_sig):
            j = skip_regex(src, i)
            if j == -1:                     # 不是正则（跨行/未闭合）→ 按除号处理
                out.append(c); i += 1; last_sig = c
            else:
                out.append(" " * (j - i)); i = j; last_sig = "x"
        else:
            out.append(c)
            if not c.isspace():
                last_sig = c
            i += 1
    return "".join(out)


def top_level_decls(src):
    """按行扫描出顶层声明（粗粒度但够用：只看第 0 列）。"""
    decls = {}
    for line in src.splitlines():
        if not line or line[0] in " \t}/*":
            continue
        m = DECL_RE.match(line)
        if m:
            if line.lstrip().startswith("class"):
                kind = "class"
            elif FUNC_RE.match(line):
                kind = "function"
            else:
                k = re.match(r"^(?:export\s+)?(const|let|var)\s+", line.lstrip())
                kind = k.group(1) if k else "var"
            decls.setdefault(m.group(1), kind)
        # 支持 `const a = 1, b = 2;` 与解构
        dm = re.match(r"^(?:export\s+)?(const|let|var)\s+(.*)$", line)
        if dm:
            body = dm.group(2)
            head = body.split("=")[0].strip()
            if head.startswith("{") or head.startswith("["):
                for nm in re.findall(r"[A-Za-z_$][\w$]*", head.split("}")[0].split("]")[0]):
                    if nm not in ("let", "var", "const"):
                        decls.setdefault(nm, "destructured")
            for part in re.findall(r"[,\s]([A-Za-z_$][\w$]*)\s*=(?!=)", body):
                decls.setdefault(part, dm.group(1))
    return decls


def find_export_bodies(src):
    """返回 [(label, start, end)] —— {} 内容区间的起止偏移。"""
    spans = []
    pats = [
        re.compile(r"window\s*\.\s*[A-Za-z_$][\w$]*\s*=\s*\{"),
        re.compile(r"module\s*\.\s*exports\s*=\s*\{"),
        re.compile(r"(?:^|\n)\s*export\s+default\s*\{"),
        re.compile(r"(?:^|\n)\s*export\s*\{"),
    ]
    clean = strip_strings_and_comments(src)
    for p in pats:
        for m in p.finditer(clean):
            brace = clean.find("{", m.start())
            depth, i = 0, brace
            while i < len(clean):
                if clean[i] == "{":
                    depth += 1
                elif clean[i] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                i += 1
            if i >= len(clean):
                continue
            label = src[m.start():brace].strip().replace("\n", " ")
            spans.append((label or "export", brace + 1, i))
    return spans


def _matching(clean, open_idx, op, cl):
    depth = 0
    for k in range(open_idx, len(clean)):
        if clean[k] == op:
            depth += 1
        elif clean[k] == cl:
            depth -= 1
            if depth == 0:
                return k
    return -1


def _param_ranges(clean):
    """找出所有「形参表」的 (起,止) 区间，用于跳过参数名（catch(e) / foo(a) / (a)=>）。"""
    toks = [(m.start(), m.group(0)) for m in re.finditer(r"[A-Za-z_$][\w$]*", clean)]
    ranges = []
    for m in re.finditer(r"\(", clean):
        p = m.start()
        close = _matching(clean, p, "(", ")")
        if close == -1:
            continue
        prev = None                       # 前一个标识符 token
        for s, t in toks:
            if s < p:
                prev = (s, t)
            else:
                break
        prev_prev_ch = ""
        if prev:
            before = clean[:prev[0]].rstrip()
            prev_prev_ch = before[-1:] if before else ""
        nxt = clean[close + 1:].lstrip()[:2]
        is_param = (
            (prev and prev[1] in ("function", "catch")) or
            nxt == "=>" or
            (prev and prev[1] not in BUILTINS and prev_prev_ch in ("{", ",", ""))
        )
        if is_param:
            ranges.append((p, close + 1))
    return ranges


def identifiers_in_export(src, start, end):
    """取出该区间内**被引用**的标识符（跳过对象键、属性名、形参、关键字）。"""
    body = src[start:end]
    clean = strip_strings_and_comments(body)
    pranges = _param_ranges(clean)
    toks = [(m.start(), m.end()) for m in re.finditer(r"[A-Za-z_$][\w$]*", clean)]
    refs = []
    for m in re.finditer(r"[A-Za-z_$][\w$]*", clean):
        tok = m.group(0)
        if tok in BUILTINS:
            continue
        s, e = m.start(), m.end()
        if any(a <= s < b for a, b in pranges):
            continue                                  # 形参
        prefix = clean[:s].rstrip()
        prev = prefix[-1:] if prefix else ""
        nxt = clean[e:].lstrip()[:1]
        prev_token = ""
        for ps, pe in toks:
            if pe <= s:
                prev_token = clean[ps:pe]
            else:
                break
        if prev == "." and not prefix.endswith(".."):
            continue                                  # 属性访问 a.b（排除展开 ...a）
        if prev_token in ("get", "set") and nxt == "(":
            continue                                  # get PLAYER(){}
        if nxt == ":" and prev in ("{", ",", ""):
            continue                                  # 对象键
        if nxt == ":" and re.match(r"\w", clean[e:].lstrip()[1:] or ""):
            continue
        refs.append(tok)
    return refs


def unused_globals(raw, decls):
    """保守判据：在**原文**（含注释/字符串）里数出现次数，≤1 才算疑似未使用。

    方向刻意偏保守 —— 宁可漏报，也不要把活着的函数报成死代码。
    （历史事故：旧版在"剥离后的文本"上计数，而剥离器遇到含引号的正则字面量
    会跑飞、吞掉几十 KB 代码，于是 startRender / storeMaster 这类明显到处
    引用的函数全被报成"只出现一次"。工具的结论本身也要能自证。）
    """
    out = []
    for name in decls:
        pat = r"(?<![\w$])" + re.escape(name) + r"(?![\w$])"
        n = len(re.findall(pat, raw))
        if n <= 1:
            out.append(name)
    return sorted(out)


def strip_ratio(src, clean):
    a = sum(1 for c in src if not c.isspace())
    b = sum(1 for c in clean if not c.isspace())
    return (b / a) if a else 1.0


def extract_html_scripts(html):
    """抽出 <script> 无 src 的块，拼成一份可被 node --check 的 JS。"""
    blocks = []
    for m in re.finditer(r"<script\b([^>]*)>(.*?)</script\s*>", html,
                         re.S | re.I):
        attrs, body = m.group(1), m.group(2)
        if re.search(r"\bsrc\s*=", attrs, re.I):
            continue
        if re.search(r'type\s*=\s*["\']?(?!text/javascript|application/javascript|module)',
                     attrs, re.I):
            continue
        blocks.append(body)
    return "\n;\n".join(blocks)


def prepare(path):
    """返回 (用于分析的源码, 用于语法检查的临时 js 路径或 None)。"""
    ext = os.path.splitext(path)[1].lower()
    raw = open(path, encoding="utf-8").read()
    if ext in (".html", ".htm"):
        js = extract_html_scripts(raw)
        tmp = "/tmp/.verify_edit_extract.js"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(js)
        return js, tmp
    return raw, (path if ext in (".js", ".mjs", ".cjs") else None)


def syntax_check(path, target):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".py":
        cmd = [sys.executable, "-m", "py_compile", target or path]
    elif target:
        cmd = ["node", "--check", target]
    else:
        return "skipped (unsupported extension)"
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if p.returncode == 0:
            return "ok"
        return "FAIL: " + (p.stderr or p.stdout)[-1500:]
    except FileNotFoundError as e:
        return "skipped (%s)" % e
    except subprocess.TimeoutExpired:
        return "timeout"


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("file")
    ap.add_argument("--syntax", action="store_true")
    ap.add_argument("--exports", action="store_true")
    ap.add_argument("--inventory", action="store_true")
    ap.add_argument("--unused", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--baseline")
    ap.add_argument("--save-baseline")
    args = ap.parse_args()
    do = lambda f: args.all or getattr(args, f)

    if not os.path.isfile(args.file):
        print(json.dumps({"ok": False, "error": "文件不存在：%s" % args.file}, ensure_ascii=False))
        return 2
    src, syntax_target = prepare(args.file)
    res = {"file": args.file, "bytes": os.path.getsize(args.file), "problems": []}
    if os.path.splitext(args.file)[1].lower() in (".html", ".htm"):
        res["analyzed"] = "内联 <script> 块（%d 字节）" % len(src)

    if args.save_baseline:
        inv = sorted(top_level_decls(src))
        with open(args.save_baseline, "w", encoding="utf-8") as f:
            json.dump({"file": args.file, "decls": inv}, f, ensure_ascii=False, indent=2)
        res["baseline_saved"] = args.save_baseline

    if do("syntax"):
        s = syntax_check(args.file, syntax_target)
        res["syntax"] = "ok" if s == "ok" else s
        if s.startswith("FAIL") or s == "timeout":
            res["problems"].append({"kind": "syntax", "detail": s})

    decls = top_level_decls(src)
    if do("exports") or do("unused"):
        ratio = strip_ratio(src, strip_strings_and_comments(src))
        res["strip_ratio"] = round(ratio, 3)
        if ratio < 0.15:
            res["problems"].append({
                "kind": "stripper-suspicious",
                "detail": "代码剥离后只剩 %.1f%% 的非空白字符（正常 JS 通常 >30%%）——"
                          "剥离器可能跑飞了（历史上是含引号的正则字面量导致），"
                          "本次 --exports / --unused 的结果不可信。" % (ratio * 100)})
    if do("inventory"):
        res["decls_count"] = len(decls)
        res["decls"] = sorted(decls)
        if args.baseline and os.path.isfile(args.baseline):
            base = set(json.load(open(args.baseline, encoding="utf-8"))["decls"])
            cur = set(decls)
            res["removed"] = sorted(base - cur)
            res["added"] = sorted(cur - base)
            if res["removed"]:
                res["problems"].append({
                    "kind": "decls-removed",
                    "detail": "这些顶层标识符消失了：%s —— 确认引用都清理干净了" % res["removed"]})

    if do("exports"):
        spans = find_export_bodies(src)
        res["export_tables"] = [s[0] for s in spans]
        dangling = {}
        for label, s, e in spans:
            refs = set(identifiers_in_export(src, s, e))
            bad = sorted(r for r in refs if r not in decls)
            if bad:
                dangling[label] = bad
        res["dangling_refs"] = dangling
        if dangling:
            res["problems"].append({
                "kind": "dangling-export-ref",
                "detail": "导出对象引用了不存在的标识符 %s —— 会抛 ReferenceError，"
                          "整个导出会变成 undefined" % dangling})

    if do("unused"):
        res["possibly_unused"] = unused_globals(src, decls)
        if res["possibly_unused"]:
            res["unused_note"] = ("启发式提示，非结论：判据是「在原文里出现次数 <= 1」。"
                                  "删除任何一条前必须人工确认（同名变量、字符串引用会干扰）。")

    res["ok"] = not res["problems"]
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
