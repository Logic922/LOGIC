#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
listen2text.py —— 把「听力考试音频」转成中英对照文本。

原理：
  1. 用 ffmpeg silencedetect 在长停顿处把音频切成若干块（每块约一段材料）；
  2. 每块分别用 apple-speech 的 zh-CN 和 en-US 模型转写（单语言模型，必须各跑一次）；
  3. 两遍结果都带时间戳，按时间轴对齐：
       某英文段的时间区间若与「含汉字的 zh 段」重叠 → 判为中文指令；
       否则保留英文。
  4. 每段材料读两遍，用 difflib 找出重复并去重。

用法：
  python3 listen2text.py <audio> <out.md> [--target 100] [--gap 1.6] [--keep-dup]
"""
import argparse, difflib, json, os, re, subprocess, sys, tempfile

CJK = re.compile(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]')


def run(cmd, quiet=False):
    return subprocess.run(cmd, capture_output=True, text=True)


def duration_of(audio):
    r = run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=nw=1:nk=1', audio])
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def cut_points(audio, gap, noise='-35dB'):
    """返回切分点列表：取静音「开始」时刻（而非中点），避免把块尾单词切断。"""
    # 注意：本环境下 ffmpeg 必须显式带 -loglevel info，否则 stderr 会被丢弃
    r = run(['ffmpeg', '-loglevel', 'info', '-hide_banner', '-i', audio,
             '-af', 'silencedetect=noise=%s:d=%s' % (noise, gap), '-f', 'null', '-'])
    txt = r.stderr
    starts = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', txt)]
    ends = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', txt)]
    return [max(0.1, s - 0.05) for s, e in zip(starts, ends) if e > s]


def build_chunks(total, cuts, target):
    """按停顿点切分，并把过短的块合并到 >= target 秒。"""
    pts = [0.0] + [c for c in cuts if 0.5 < c < total - 0.5] + [total]
    raw = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    chunks, cur = [], None
    for a, b in raw:
        if cur is None:
            cur = [a, b]
        elif b - cur[0] <= target * 1.35:
            cur[1] = b
        else:
            chunks.append(tuple(cur)); cur = [a, b]
    if cur:
        chunks.append(tuple(cur))
    # 太短的尾块并回上一块（注意：取「上一块的起点 + 尾块的终点」，方向别写反）
    if len(chunks) >= 2 and chunks[-1][1] - chunks[-1][0] < target * 0.3:
        last = chunks.pop()
        prev = chunks.pop()
        chunks.append((prev[0], last[1]))
    # 兜底：丢掉任何残块（<2s），它们只会产出噪声
    return [c for c in chunks if c[1] - c[0] >= 2.0]


def asr(path, lang, retries=2):
    """调用 apple-speech，返回 [(t, duration, text), ...]；失败返回 None。"""
    for _ in range(retries + 1):
        r = run(['apple-speech', 'transcribe', '--source', path,
                 '--language', lang, '--compact'])
        try:
            d = json.loads(r.stdout)['data']
        except Exception:
            continue
        segs = [(s.get('timestamp', 0) or 0,
                 s.get('duration', 0) or 0,
                 (s.get('substring') or '').strip())
                for s in d.get('segments', [])]
        segs = [s for s in segs if s[2]]
        if segs or (d.get('text') or '').strip():
            return segs
    return None


def merge(zh_segs, en_segs):
    """按时间轴合并：中文块取 zh，其余取 en。返回 [(t, text, 'zh'|'en')]。

    判据要「保守」：只有当英文段的时间区间有 >50% 落在中文指令区间内，才判定它是
    中文被英文模型听歪的结果。否则宁可保留（多一个乱码词，好过整句英文被误删）。
    """
    spans = []
    for t, d, s in zh_segs:
        if CJK.search(s):
            spans.append((t, t + (d if d > 0.15 else max(1.2, len(s) * 0.25))))
    out = []
    for t, d, s in zh_segs:
        if CJK.search(s):
            out.append((t, s, 'zh'))
    for t, d, s in en_segs:
        ed = d if d > 0.15 else max(1.0, len(s) * 0.05)
        hit = 0.0
        for a, b in spans:
            hit += max(0.0, min(b, t + ed) - max(a, t))
        if ed > 0 and hit / ed > 0.5:
            continue
        out.append((t, s, 'en'))
    out.sort(key=lambda x: x[0])
    return out


def dedupe_repeat(text):
    """一段材料读两遍 → 找到最佳切分点，返回前半（保留更完整的一遍）。"""
    s = text.strip()
    if len(s) < 80:
        return s, False
    best, best_k = 0.0, None
    n = len(s)
    for k in range(int(n * 0.3), int(n * 0.7), max(1, n // 120)):
        a, b = s[:k], s[k:]
        if len(a) < 40 or len(b) < 40:
            continue
        r = difflib.SequenceMatcher(None, a, b).quick_ratio()
        if r > best:
            best, best_k = r, k
    if best_k and best >= 0.78:
        a, b = s[:best_k].strip(), s[best_k:].strip()
        # 取更长、更完整的一遍
        keep = a if len(a) >= len(b) * 0.9 else b
        return keep, True
    return s, False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('audio')
    ap.add_argument('out')
    ap.add_argument('--target', type=float, default=100, help='每块目标秒数（默认100）')
    ap.add_argument('--gap', type=float, default=2.0, help='静音判据秒数（默认2.0）')
    ap.add_argument('--keep-dup', action='store_true', help='不去重（保留两遍朗读）')
    args = ap.parse_args()

    total = duration_of(args.audio)
    cuts = cut_points(args.audio, args.gap)
    chunks = build_chunks(total, cuts, args.target)
    tmp = tempfile.mkdtemp(prefix='l2t_')

    blocks = []          # (lang, text)
    for i, (a, b) in enumerate(chunks, 1):
        wav = os.path.join(tmp, 'c%02d.wav' % i)
        a2 = max(0.0, a - 0.4)           # 起点前移 0.4s，兜住上一块被切掉的词尾
        run(['ffmpeg', '-loglevel', 'error', '-hide_banner', '-y', '-i', args.audio,
             '-ss', '%.2f' % a2, '-t', '%.2f' % (b - a2 + 0.5),
             '-ar', '16000', '-ac', '1', wav], quiet=True)
        zh = asr(wav, 'zh-CN')
        en = asr(wav, 'en-US')
        if zh is None and en is None:
            sys.stderr.write('[warn] 第%d块两种模型都失败，跳过\n' % i)
            continue
        merged = merge(zh or [], en or [])
        sys.stderr.write('[chunk %d/%d] %.0f-%.0fs  zh=%d segs  en=%d segs\n'
                         % (i, len(chunks), a, b, len(zh or []), len(en or [])))
        # 相邻同类合并成段
        for t, s, lang in merged:
            if blocks and blocks[-1][0] == lang:
                blocks[-1][1] += (' ' if lang == 'en' else '') + s
            else:
                blocks.append([lang, s])

    lines, stats = [], {'zh': 0, 'en': 0, 'dedup': 0}
    for lang, text in blocks:
        text = re.sub(r'\s+', ' ', text).strip()
        if not text:
            continue
        if lang == 'zh':
            lines.append('> %s' % text); stats['zh'] += 1
        else:
            if not args.keep_dup:
                text, dropped = dedupe_repeat(text)
                if dropped:
                    stats['dedup'] += 1
            lines.append(text); stats['en'] += 1

    head = ('# 听力原文（自动转写）\n\n'
            '> 来源：`%s`（时长 %.1f 分钟）\n'
            '> 方法：ffmpeg 静音切分 → apple-speech 双模型（zh-CN / en-US）转写 → 时间戳对齐合并'
            '%s\n> 中文指令以引用块（>）标出。专有名词与数字可能有误，请对照卷面核对。\n\n---\n\n'
            % (os.path.basename(args.audio), (total or 0) / 60,
               '→ 已自动去除"读两遍"的重复' if not args.keep_dup else ''))
    with open(args.out, 'w', encoding='utf-8') as f:
        f.write(head + '\n\n'.join(lines) + '\n')
    sys.stderr.write('完成：中文指令 %d 段，英文 %d 段，去重 %d 处 → %s\n'
                     % (stats['zh'], stats['en'], stats['dedup'], args.out))


if __name__ == '__main__':
    main()
