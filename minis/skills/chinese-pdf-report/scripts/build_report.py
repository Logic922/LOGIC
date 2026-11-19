#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_report.py —— 用 JSON 规格生成中文 PDF（iSH / reportlab）。

用法：
    python3 build_report.py spec.json out.pdf

规格结构：
{
  "title": "主标题",
  "subtitle": "副标题（可省）",
  "footer": "页脚文字（可省）",
  "blocks": [ ...见下方 block 类型... ]
}

block 类型：
  {"t":"h2","text":"一、xxx"}
  {"t":"h3","text":"小标题"}
  {"t":"p","text":"正文，支持 <b> 与 <font color='#B4232A'>"}
  {"t":"note","text":"灰色小字"}
  {"t":"banner","text":"深色通栏标题"}
  {"t":"bar","left":"第 2 题","right":"题型/考点标签"}          # 每题标题条
  {"t":"kv","pairs":[["你的答案","C"],["正确答案","B"]],
              "colors":["#B4232A","#1B6B3A"]}                    # 两列对照表
  {"t":"ul","title":"【错因分析】","title_color":"#B4232A",
              "marker":"•","items":["...","..."]}
  {"t":"table","header":["a","b"],"rows":[["1","2"]],
              "widths":[60,40],"center_cols":[1,2],"last_row_bg":"#E8F0F8"}
  {"t":"group","blocks":[...]}                                  # 同页不拆开
  {"t":"hr"} / {"t":"space","h":10} / {"t":"pagebreak"}
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))

DEFAULT_THEME = {
    'font': os.environ.get('CJK_TTF', '/root/wqy.ttf'),
    'dark': '#17324F', 'blue': '#2E5C8A', 'lblue': '#E8F0F8',
    'gray': '#5A5A5A', 'lgray': '#F4F6F8', 'grid': '#B9C6D4',
    'body_size': 9.5, 'body_leading': 16.5, 'margin_mm': 17, 'footer': True,
}


def ensure_font(path):
    if os.path.exists(path):
        return
    sys.stderr.write('字体缺失，调用 setup_font.py 准备…\n')
    subprocess.run([sys.executable, os.path.join(HERE, 'setup_font.py'),
                    '--target', path], check=True)


def esc(s):
    """只转义裸 &，保留用户写的 <b>/<font> 标签。"""
    return str(s).replace('&', '&amp;')


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    spec = json.load(open(sys.argv[1], encoding='utf-8'))
    out = sys.argv[2] if len(sys.argv) > 2 else spec.get('out', 'report.pdf')

    th = dict(DEFAULT_THEME)
    th.update(spec.get('theme', {}))
    ensure_font(th['font'])

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                    Spacer, Table, TableStyle, KeepTogether, HRFlowable)

    pdfmetrics.registerFont(TTFont('CJK', th['font']))
    pdfmetrics.registerFontFamily('CJK', normal='CJK', bold='CJK',
                                  italic='CJK', boldItalic='CJK')

    C = {k: colors.HexColor(v) for k, v in th.items()
         if k in ('dark', 'blue', 'lblue', 'gray', 'lgray', 'grid')}

    def S(**kw):
        base = dict(fontName='CJK', fontSize=th['body_size'],
                    leading=th['body_leading'], textColor=colors.black,
                    alignment=TA_LEFT, wordWrap='CJK')
        base.update(kw)
        return ParagraphStyle('s%d' % len(kw), **base)

    M = th['margin_mm'] * mm
    story = []

    if spec.get('title'):
        story.append(Paragraph(esc(spec['title']),
                               S(fontSize=19, leading=26, textColor=C['dark'],
                                 alignment=TA_CENTER)))
    if spec.get('subtitle'):
        story.append(Spacer(1, 3))
        story.append(Paragraph(esc(spec['subtitle']),
                               S(fontSize=10.5, leading=17, textColor=C['gray'],
                                 alignment=TA_CENTER)))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width='100%', thickness=1.2, color=C['blue'], spaceAfter=10))

    def build(b):
        t = b.get('t', 'p')
        if t == 'h2':
            return [Paragraph(esc(b['text']), S(fontSize=13, leading=20,
                             textColor=C['dark'], spaceBefore=12, spaceAfter=5))]
        if t == 'h3':
            return [Paragraph(esc(b['text']), S(fontSize=10.5, leading=17,
                             textColor=C['blue'], spaceBefore=6, spaceAfter=2))]
        if t == 'p':
            return [Paragraph(esc(b['text']), S(spaceAfter=2.5))]
        if t == 'note':
            return [Paragraph(esc(b['text']), S(fontSize=9, leading=15, textColor=C['gray']))]
        if t == 'banner':
            tb = Table([[Paragraph(esc(b['text']), S(fontSize=12, leading=18,
                          textColor=colors.white))]],
                       colWidths=[A4[0] - 2 * M], hAlign='LEFT')
            tb.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), C['dark']),
                                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5)]))
            return [Spacer(1, 8), tb]
        if t == 'bar':
            w = A4[0] - 2 * M
            lw = b.get('left_w', 26) * mm
            tb = Table([[Paragraph('<b>%s</b>' % esc(b.get('left', '')),
                                   S(fontSize=11, leading=17, textColor=colors.white)),
                         Paragraph(esc(b.get('right', '')),
                                   S(fontSize=9.5, leading=16, textColor=C['lblue']))]],
                       colWidths=[lw, w - lw], hAlign='LEFT')
            tb.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), C['blue']),
                                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
            return [Spacer(1, 6), tb, Spacer(1, 5)]
        if t == 'kv':
            pairs = b['pairs']
            cols = b.get('colors', [None] * len(pairs))
            row1 = [Paragraph(str(k), S(fontSize=9, leading=14, textColor=C['gray']))
                    for k, v in pairs]
            row2 = []
            for (k, v), col in zip(pairs, cols):
                txt = esc(v)
                if col:
                    txt = "<font color='%s'>%s</font>" % (col, txt)
                row2.append(Paragraph(txt, S(fontSize=10, leading=15)))
            w = A4[0] - 2 * M
            cw = [w / len(pairs)] * len(pairs)
            tb = Table([row1, row2], colWidths=cw, hAlign='LEFT')
            tb.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), C['lblue']),
                                    ('GRID', (0, 0), (-1, -1), 0.5, C['grid']),
                                    ('LEFTPADDING', (0, 0), (-1, -1), 7),
                                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
            return [Spacer(1, 2), tb, Spacer(1, 6)]
        if t == 'ul':
            out_ = []
            if b.get('title'):
                out_.append(Paragraph(esc(b['title']),
                                      S(fontSize=9.5, leading=15, spaceAfter=2,
                                        textColor=colors.HexColor(b.get('title_color', th['blue'])))))
            ind = b.get('indent', 12)
            mk = b.get('marker', '•')
            for i in b['items']:
                out_.append(Paragraph(esc(i), S(leftIndent=ind, bulletIndent=2,
                                                spaceAfter=2.5), bulletText=mk))
            return out_
        if t == 'table':
            w = A4[0] - 2 * M
            widths = b.get('widths')
            cw = [x * mm for x in widths] if widths else [w / len(b['header'])] * len(b['header'])
            ctr = set(b.get('center_cols', []))
            rows = []
            for ri, row in enumerate([b['header']] + b['rows']):
                cells = []
                for ci, cell in enumerate(row):
                    st = S(fontSize=9, leading=14, alignment=TA_CENTER if (ri == 0 or ci in ctr) else TA_LEFT)
                    cells.append(Paragraph(esc(cell), st))
                rows.append(cells)
            tb = Table(rows, colWidths=cw, hAlign='LEFT')
            st = [('BACKGROUND', (0, 0), (-1, 0), C['blue']),
                  ('GRID', (0, 0), (-1, -1), 0.5, C['grid']),
                  ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                  ('TOPPADDING', (0, 0), (-1, -1), 5),
                  ('BOTTOMPADDING', (0, 0), (-1, -1), 5)]
            if b.get('stripe', True):
                for i in range(1, len(rows)):
                    if i % 2 == 0:
                        st.append(('BACKGROUND', (0, i), (-1, i), C['lgray']))
            if b.get('last_row_bg'):
                st.append(('BACKGROUND', (0, len(rows) - 1), (-1, len(rows) - 1),
                           colors.HexColor(b['last_row_bg'])))
            tb.setStyle(TableStyle(st))
            return [tb]
        if t == 'group':
            inner = []
            for x in b['blocks']:
                inner.extend(build(x))
            return [KeepTogether(inner)]
        if t == 'hr':
            return [Spacer(1, 4), HRFlowable(width='100%', thickness=0.5,
                                             color=C['grid'], spaceAfter=2)]
        if t == 'space':
            return [Spacer(1, b.get('h', 10))]
        if t == 'pagebreak':
            from reportlab.platypus import PageBreak
            return [PageBreak()]
        sys.stderr.write('[warn] 未知 block 类型：%s\n' % t)
        return []

    for b in spec.get('blocks', []):
        story.extend(build(b))

    def on_page(canvas, doc):
        if not th.get('footer'):
            return
        canvas.saveState()
        canvas.setFont('CJK', 8)
        canvas.setFillColor(C['gray'])
        canvas.drawString(M, 10 * mm, spec.get('footer', spec.get('title', '')))
        canvas.drawRightString(A4[0] - M, 10 * mm, '第 %d 页' % doc.page)
        canvas.setStrokeColor(C['grid'])
        canvas.setLineWidth(0.5)
        canvas.line(M, 13 * mm, A4[0] - M, 13 * mm)
        canvas.restoreState()

    doc = BaseDocTemplate(out, pagesize=A4, leftMargin=M, rightMargin=M,
                          topMargin=15 * mm, bottomMargin=18 * mm,
                          title=spec.get('title', 'report'))
    doc.addPageTemplates([PageTemplate(id='main', onPage=on_page,
                                       frames=[Frame(M, doc.bottomMargin, doc.width, doc.height, id='n')])])
    doc.build(story)
    print('OK ->', out)


if __name__ == '__main__':
    main()
