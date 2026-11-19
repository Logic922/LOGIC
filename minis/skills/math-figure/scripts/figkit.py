"""figkit — iSH 上中文 + 数学混排制图的公共设置与自检。

用法：
    import sys; sys.path.insert(0, '/var/minis/skills/math-figure/scripts')
    import figkit
    fig, ax = figkit.new(15, 9)          # 建图（附中文字体已就绪）
    ...
    figkit.save(fig, 'q9_triangle')      # 存到 /var/minis/attachments/，打印尺寸
    figkit.check(fig)                    # 打印越界/严重重叠的文本，空列表=通过
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

CJK = {
    'sans': '/usr/share/fonts/noto/NotoSansCJK-Regular.ttc',
    'serif': '/usr/share/fonts/noto/NotoSerifCJK-Regular.ttc',
}
OUT = '/var/minis/attachments'


def setup(style='sans', base=14):
    """注册中文字体并设置全局 rcParams。必须在建图前调用一次。"""
    path = CJK[style]
    fm.fontManager.addfont(path)
    name = fm.FontProperties(fname=path).get_name()
    plt.rcParams.update({
        'font.family': name,
        'axes.unicode_minus': False,
        'mathtext.fontset': 'cm',   # 公式用 Computer Modern，与中文搭配最稳
        'font.size': base,
        'figure.facecolor': 'white',
        'savefig.facecolor': 'white',
    })
    return name


def new(w=15, h=9, dpi=140):
    """建一张图 + 一个坐标轴。"""
    setup()
    fig = plt.figure(figsize=(w, h), dpi=dpi)
    return fig, fig.add_subplot(111)


def save(fig, name, dpi=None):
    """存 PNG 到共享目录，返回路径。name 不带扩展名。缺中文字体时会告警。"""
    import warnings, os
    if not name.endswith('.png'):
        name += '.png'
    path = f'{OUT}/{name}'
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        fig.savefig(path, dpi=dpi or fig.dpi)
        msgs = [str(x.message) for x in w]
    bad = [m for m in msgs if 'missing from font' in m or 'Glyph' in m]
    if bad:
        print(f'!! 缺字形 {len(bad)} 处（中文会变豆腐块）：先调用 figkit.setup() 再建图')
    print(f'{path}  {os.path.getsize(path)//1024} KB  {int(fig.get_figwidth()*(dpi or fig.dpi))}x{int(fig.get_figheight()*(dpi or fig.dpi))}')
    return path if not bad else (path, 'MISSING_GLYPH')


def _box(t, renderer):
    try:
        b = t.get_window_extent(renderer)
    except Exception:
        return None
    return b


def check(fig, tol=3, overlap=0.45):
    """自检：返回问题列表（空 = 无明显问题）。

    - 文本越出画布（被裁掉）→ 报 'clip'
    - 两个 ax.texts 交叠面积 / 较小者面积 > overlap → 报 'overlap'
    - 有缺字形（中文变豆腐块）→ 报 'glyph'
    标题、图例、刻度不参与重叠比较（会误报）。
    """
    import warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        fig.canvas.draw()
        msgs = [str(x.message) for x in w]
    r = fig.canvas.get_renderer()
    fb = fig.bbox
    issues = []

    bad = [m for m in msgs if 'missing from font' in m or 'Glyph' in m]
    if bad:
        issues.append(f'glyph  {len(bad)} 处字符无字形（中文会变豆腐块）：确认已调用 figkit.setup()')

    groups = [('fig', fig.texts)]
    for i, ax in enumerate(fig.axes):
        groups.append((f'ax{i}', list(ax.texts)))
        groups.append((f'ax{i}', [ax.title] + ([ax.xaxis.label] if ax.get_xlabel() else []) + ([ax.yaxis.label] if ax.get_ylabel() else [])))
        leg = ax.get_legend()
        if leg is not None:
            groups.append((f'ax{i}.legend', list(leg.get_texts())))

    for gname, texts in groups:
        for t in texts:
            b = _box(t, r)
            if b is None:
                continue
            s = t.get_text().strip()
            if not s:
                continue
            if b.x0 < -tol or b.y0 < -tol or b.x1 > fb.x1 + tol or b.y1 > fb.y1 + tol:
                issues.append(f'clip  {gname}: {s[:40]!r}')

    for i, ax in enumerate(fig.axes):
        ts = [t for t in ax.texts if t.get_text().strip()]
        for a in range(len(ts)):
            for b_ in range(a + 1, len(ts)):
                A, B = _box(ts[a], r), _box(ts[b_], r)
                if A is None or B is None:
                    continue
                dx = min(A.x1, B.x1) - max(A.x0, B.x0)
                dy = min(A.y1, B.y1) - max(A.y0, B.y0)
                if dx <= 0 or dy <= 0:
                    continue
                inter = dx * dy
                small = min(A.width * A.height, B.width * B.height)
                if small > 0 and inter / small > overlap:
                    issues.append(f'overlap ax{i}: {ts[a].get_text()[:24]!r} <-> {ts[b_].get_text()[:24]!r} ({inter/small:.0%})')

    print('\n'.join(issues) if issues else 'check: ok')
    return issues
