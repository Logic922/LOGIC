#!/usr/bin/env python3
"""安全编辑：字面替换 / 区域替换，带计数断言 + 自动备份 + 回读校验。

存在的理由：用「find/index 切片」改代码时，切多一行就会留下残骸
（语法错误、整页白屏），而切少一行则静默什么都没改。本脚本把
「替我数一遍」变成机器断言。

用法
----
# A. 字面替换（默认要求恰好出现 1 次）
safe_replace.py FILE --old-file OLD.txt --new-file NEW.txt [--count N]
safe_replace.py FILE --old 'foo' --new 'bar' [--count N]

# B. 区域替换（含两端锚点），两个锚点都必须各出现恰好 1 次
safe_replace.py FILE --region-start 'function a(){' --region-end '});' \
                    --new-file NEW.txt

# C. 只检查不改（预演）
safe_replace.py FILE --old 'foo' --new 'bar' --dry-run

约定
----
* OLD / NEW 内容从文件读（--old-file / --new-file）最稳，避免 shell 引号地狱。
* `\\n` 在 --old/--new 里会被还原成换行；--old-file/--new-file 不做任何转义。
* 每次真正写入前自动备份到 FILE.bak.<时间戳>（或 --backup-dir）。
* 结果以 JSON 输出，含 before/after 计数与增删行数，便于贴进对话自证。
退出码：0 成功；1 断言失败（文件未被修改）；2 用法错误。
"""
import argparse
import difflib
import json
import os
import sys
import time

BAK_SUFFIX = ".bak."


def die(msg, code=1):
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False, indent=2))
    sys.exit(code)


def read_text(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def unescape(s):
    return s.replace("\\n", "\n").replace("\\t", "\t")


def get_snippet(args, which):
    """取 --{which} 与 --{which}-file；返回 (text, source)"""
    inline = getattr(args, which)
    fpath = getattr(args, which + "_file")
    if inline is not None and fpath is not None:
        die("--%s 与 --%s-file 只能给一个，避免歧义" % (which, which), 2)
    if fpath is not None:
        if not os.path.isfile(fpath):
            die("文件不存在：%s" % fpath, 2)
        return read_text(fpath), fpath
    if inline is not None:
        return unescape(inline), "inline"
    die("缺少 --%s 或 --%s-file" % (which, which), 2)


def count_occurrences(hay, needle):
    if needle == "":
        return 0
    n, i = 0, hay.find(needle)
    while i != -1:
        n += 1
        i = hay.find(needle, i + len(needle))
    return n


def line_stats(before, after):
    b = before.splitlines()
    a = after.splitlines()
    add = dele = 0
    for ln in difflib.unified_diff(b, a, n=0):
        if ln.startswith("+++") or ln.startswith("---") or ln.startswith("@@"):
            continue
        if ln.startswith("+"):
            add += 1
        elif ln.startswith("-"):
            dele += 1
    return {"lines_before": len(b), "lines_after": len(a),
            "lines_added": add, "lines_removed": dele}


def backup(path, backup_dir):
    d = backup_dir or os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(d, exist_ok=True)
    dst = os.path.join(d, os.path.basename(path) + BAK_SUFFIX + str(int(time.time())))
    with open(dst, "w", encoding="utf-8", newline="") as f:
        f.write(read_text(path))
    return dst


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("file")
    ap.add_argument("--old")
    ap.add_argument("--old-file")
    ap.add_argument("--new")
    ap.add_argument("--new-file")
    ap.add_argument("--region-start")
    ap.add_argument("--region-end")
    ap.add_argument("--count", type=int, default=1,
                    help="--old 期望出现次数（默认 1）。填 0 表示不限制。")
    ap.add_argument("--backup-dir")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    if not os.path.isfile(args.file):
        die("目标文件不存在：%s" % args.file, 2)
    src = read_text(args.file)
    region_mode = args.region_start is not None or args.region_end is not None
    if region_mode and (args.region_start is None or args.region_end is None):
        die("区域替换必须同时给 --region-start 与 --region-end", 2)
    if region_mode and (args.old is not None or args.old_file is not None):
        die("区域替换与字面替换互斥", 2)

    new_text, new_src = get_snippet(args, "new")

    if region_mode:
        start_a = unescape(args.region_start)
        end_a = unescape(args.region_end)
        cs, ce = count_occurrences(src, start_a), count_occurrences(src, end_a)
        if cs != 1:
            die("起点锚点出现 %d 次（必须恰好 1 次）：%r —— 换个更长的锚点。" % (cs, start_a[:60]), 1)
        if ce != 1:
            die("终点锚点出现 %d 次（必须恰好 1 次）：%r —— 换个更长的锚点。" % (ce, end_a[:60]), 1)
        i = src.index(start_a)
        j = src.index(end_a, i + len(start_a)) + len(end_a)
        if j <= i:
            die("终点锚点在起点锚点之前", 1)
        removed = src[i:j]
        out = src[:i] + new_text + src[j:]
        info = {"mode": "region", "removed_chars": len(removed),
                "removed_lines": removed.count("\n")}
    else:
        old_text, old_src = get_snippet(args, "old")
        if old_text == "":
            die("--old 不能为空", 2)
        if old_text == new_text:
            die("old 与 new 完全相同 —— 这是 no-op，不会有任何行为变化。"
                "（换成真正的目标文本，或确认本次改动其实不需要）", 1)
        n = count_occurrences(src, old_text)
        if n == 0:
            die("old 在文件中找不到（0 次）。注意：锚点必须逐字符一致，"
                "含缩进与换行；先 grep 确认它真的存在。", 1)
        if args.count and n != args.count:
            die("old 实际出现 %d 次，期望 %d 次。改 --count 或换唯一锚点。" % (n, args.count), 1)
        out = src.replace(old_text, new_text)
        after_n = count_occurrences(out, new_text)
        info = {"mode": "literal", "replacements": n, "new_count_after": after_n}
        if n > 1:
            info["warning"] = "替换了 %d 处，请确认每一处都该改" % n

    if out == src:
        die("结果与原文完全相同，未做任何改动。", 1)

    info.update(line_stats(src, out))
    info["old_src"] = new_src
    if args.dry_run:
        info["dry_run"] = True
        info["ok"] = True
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return

    if not args.no_backup:
        info["backup"] = backup(args.file, args.backup_dir)
    with open(args.file, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    back = read_text(args.file)
    if back != out:
        die("写入后回读不一致 —— 文件可能被别的进程同时改了，请重做。", 1)
    info["ok"] = True
    print(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
