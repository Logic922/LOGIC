#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup_font.py —— 准备一份 reportlab 能用的中文字体（TrueType 轮廓）。

为什么需要：
    reportlab 不支持 CFF/PostScript 轮廓的字体，`apk add font-noto-cjk` 装出来的
    NotoSansCJK-*.ttc 会直接报 "postscript outlines are not supported"。
    文泉驿正黑（font-wqy-zenhei）是 TrueType 轮廓，可用；它虽然是 .ttc，
    但用 fontTools 拆出单体 .ttf 即可。

用法：
    python3 setup_font.py [--target /root/wqy.ttf] [--force]
"""
import argparse, os, subprocess, sys

TTC = '/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc'
PKG = 'font-wqy-zenhei'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--target', default=os.environ.get('CJK_TTF', '/root/wqy.ttf'))
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()

    if os.path.exists(a.target) and not a.force:
        print('已存在：%s' % a.target)
        return

    if not os.path.exists(TTC):
        print('安装 %s …' % PKG)
        subprocess.run(['apk', 'add', '--no-cache', PKG], check=True)
    if not os.path.exists(TTC):
        sys.exit('找不到 %s' % TTC)

    try:
        from fontTools.ttLib import TTCollection
    except ImportError:
        print('安装 fonttools …')
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'fonttools'], check=True)
        from fontTools.ttLib import TTCollection

    tc = TTCollection(TTC)
    for i, f in enumerate(tc.fonts):
        if f.sfntVersion == '\x00\x01\x00\x00':      # TrueType（glyf）轮廓
            f.save(a.target)
            print('已导出：%s（index %d，%s）' % (a.target, i, f['name'].getDebugName(4)))
            return
    sys.exit('该 .ttc 中没有 TrueType 轮廓的字体，无法用于 reportlab')


if __name__ == '__main__':
    main()
