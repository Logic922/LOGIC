"""simkit — iSH 物理模拟视频工具包（Pillow 离屏渲染 + ffmpeg 编码）

典型用法：
    import sys; sys.path.insert(0, "/var/minis/skills/physics-sim-video/scripts")
    from simkit import *

    vid = Video(fps=30)
    for t in times:                     # t 为"物理时间"
        img = new_frame(960, 620)
        dr = ImageDraw.Draw(img)
        title_bar(dr, img.width, "标题")
        ground_line(dr, 252, img.width)
        cam = Cam(-3.7, 5.7, 40, img.width-40)
        block(dr, cam, xP, 0.5, 252, "P", (52,120,220), "m")
        arrow(dr, cam.x(xP), 160, vP, scale=58, color=BLUE)
        spring(dr, cam.x(xQ-0.25), cam.x(xQ-0.25-3.5), 221)   # 只挂在 Q 上
        vid.add(img, hold=0.4)          # hold：该帧停顿秒数
    vid.encode("/var/minis/workspace/xxx.mp4")   # 自动清理临时帧
"""
import math, os, shutil, subprocess
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = "/root/wqy.ttf"
BLUE = (30, 90, 200)
RED = (200, 60, 60)
INK = (60, 60, 70)
GREY = (130, 130, 140)
OK_GREEN = (20, 130, 80)
BAD_RED = (200, 60, 60)


def ensure_font():
    """确保 /root/wqy.ttf（文泉驿正黑，TrueType 轮廓，reportlab/Pillow 都认）存在。"""
    if os.path.exists(FONT_PATH):
        return FONT_PATH
    os.system("apk add -q font-wqy-zenhei fonttools py3-fonttools")
    from fontTools.ttLib import TTCollection
    TTCollection("/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc").fonts[0].save(FONT_PATH)
    return FONT_PATH


def ft(size):
    ensure_font()
    return ImageFont.truetype(FONT_PATH, size)


class Cam:
    """世界坐标(米) → 屏幕像素 线性映射。"""

    def __init__(self, x0, x1, px0, px1):
        self.x0, self.x1, self.px0, self.px1 = x0, x1, px0, px1
        self.scale = (px1 - px0) / float(x1 - x0)

    def x(self, xm):
        return self.px0 + (xm - self.x0) * self.scale

    def d(self, dm):
        return dm * self.scale


def new_frame(w=960, h=620, bg=(250, 250, 252)):
    return Image.new("RGB", (w, h), bg)


def title_bar(dr, W, text, font_size=18, fill=(38, 52, 80)):
    dr.rectangle([0, 0, W, 44], fill=fill)
    dr.text((18, 22), text, font=ft(font_size), fill="white", anchor="lm")


def ground_line(dr, y, W, hatch=True):
    dr.line([(0, y), (W, y)], fill=(60, 60, 70), width=4)
    if hatch:
        for x in range(0, W, 26):
            dr.line([(x, y + 1), (x + 12, y + 13)], fill=(200, 202, 210), width=1)


def arrow(dr, x, y, val, scale=58, color=BLUE, width=5, head=13):
    """速度/力矢量箭头，val 为带符号大小（px = val*scale）。"""
    if abs(val) < 0.02:
        return
    ex = x + val * scale
    dr.line([(x, y), (ex, y)], fill=color, width=width)
    d = 1 if val > 0 else -1
    dr.polygon([(ex, y), (ex - head * d, y - head * 0.7), (ex - head * d, y + head * 0.7)], fill=color)


def spring(dr, xa, xf, y, amp=14, color=(90, 100, 120), lead=14, width=3):
    """从附着点 xa 拉到自由端 xf 画螺旋弹簧；xa==xf 时自动压缩变短。
    注意：只画 xf..xa 这一段 —— 弹簧被拉脱/压缩后长度必须由调用者按物理量给出，
    不要无条件地连接两个物体。"""
    L = abs(xa - xf)
    if L < 4:
        return
    s = 1 if xa >= xf else -1
    lead = min(lead, L * 0.2)
    nz = L - 2 * lead
    n = max(3, int(nz / 28))
    x0 = xf + s * lead
    pts = [(xf, y), (x0, y)]
    for i in range(1, 2 * n):
        pts.append((x0 + s * nz * i / (2 * n), y + (amp if i % 2 else -amp)))
    pts += [(xf + s * (L - lead), y), (xa, y)]
    dr.line(pts, fill=color, width=width, joint="curve")


def block(dr, cam, xm, wm, ground_y, label, color, sub="", h=62, font_size=24):
    x1, x2 = cam.x(xm - wm / 2.0), cam.x(xm + wm / 2.0)
    dr.rounded_rectangle([x1, ground_y - h, x2, ground_y], radius=6,
                         fill=color, outline=(40, 40, 50), width=2)
    cx = (x1 + x2) / 2
    dr.text((cx, ground_y - h / 2), label, font=ft(font_size), fill="white", anchor="mm")
    if sub:
        dr.text((cx, ground_y + 16), sub, font=ft(14), fill=(80, 80, 90), anchor="mm")


def caption(dr, x, y, text, size=20, color=INK, anchor="lm"):
    dr.text((x, y), text, font=ft(size), fill=color, anchor=anchor)


def vt_panel(dr, box, tmax, vmin, vmax, curves, t_cursor=None, marks=(),
             xlabel="t", vfmt="{:.0f}v", title=None, npts=260):
    """速度—时间面板。curves=[(函数 t->v, 颜色, 图例名), ...]；marks=[(t, 标签), ...]。"""
    x0, y0, x1, y1 = box
    dr.rounded_rectangle([x0 - 50, y0 - 50, x1 + 40, y1 + 46], radius=10,
                         fill=(255, 255, 255), outline=(210, 214, 224), width=2)
    if title:
        dr.text((x0 - 34, y0 - 30), title, font=ft(16), fill=INK, anchor="lm")
    gx = lambda t: x0 + (t / float(tmax)) * (x1 - x0)
    gy = lambda v: y0 + (vmax - v) / float(vmax - vmin) * (y1 - y0)
    for v in range(int(math.ceil(vmin)), int(vmax) + 1):
        dr.line([(x0, gy(v)), (x1, gy(v))], fill=(225, 228, 236), width=1)
        dr.text((x0 - 8, gy(v)), vfmt.format(v), font=ft(12), fill=GREY, anchor="rm")
    dr.line([(x0, gy(0)), (x1, gy(0))], fill=(120, 120, 130), width=2)
    dr.line([(x0, y0 - 4), (x0, y1 + 4)], fill=(120, 120, 130), width=2)
    dr.text((x1, gy(0) + 16), xlabel, font=ft(14), fill=GREY, anchor="mm")
    for tm, lab in marks:
        xm = gx(tm)
        for yy in range(y0 - 46, y1 + 8, 10):
            dr.line([(xm, yy), (xm, yy + 5)], fill=(170, 170, 185), width=1)
        dr.text((xm + 4, y0 - 34), lab, font=ft(12), fill=(150, 150, 160), anchor="lm")
        dr.text((xm + 4, y0 - 16), "%.2fs" % tm, font=ft(12), fill=(180, 180, 190), anchor="lm")
    for fn, col, lab in curves:
        pts = [(gx(tmax * i / npts), gy(fn(tmax * i / npts))) for i in range(npts + 1)]
        dr.line(pts, fill=col, width=3)
    if t_cursor is not None:
        tc = min(max(t_cursor, 0.0), tmax)
        dr.line([(gx(tc), y0 - 4), (gx(tc), y1 + 8)], fill=(0, 0, 0), width=2)
        for fn, col, lab in curves:
            cy = gy(fn(tc))
            dr.ellipse([gx(tc) - 5, cy - 5, gx(tc) + 5, cy + 5], fill=col)
    lx = x0 - 30
    for fn, col, lab in curves:
        dr.line([(lx, y1 + 34), (lx + 30, y1 + 34)], fill=col, width=3)
        dr.text((lx + 36, y1 + 34), lab, font=ft(12), fill=col, anchor="lm")
        lx += 116


def note_lines(dr, x, y, lines, dy=26):
    """结论面板：lines=[(小标题, 正文, 颜色), ...]，小标题可空。"""
    for head, body, col in lines:
        if head:
            dr.text((x, y), head, font=ft(14), fill=(90, 90, 100), anchor="lm")
        dr.text((x + (78 if head else 16), y), body, font=ft(14), fill=col, anchor="lm")
        y += dy
    return y


class Video:
    """逐帧收集 + 一次性编码为 MP4（H.264/yuv420p，iOS 内置播放器可直接播）。"""

    def __init__(self, tmpdir="/tmp/simframes", fps=30):
        self.dir, self.fps, self.n = tmpdir, fps, 0
        shutil.rmtree(tmpdir, ignore_errors=True)
        os.makedirs(tmpdir)

    def add(self, img, hold=0.0):
        for _ in range(1 + int(round(hold * self.fps))):
            img.save(os.path.join(self.dir, "f_%05d.png" % self.n))
            self.n += 1

    def encode(self, out, crf=20, keep_frames=False):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(self.fps),
                        "-start_number", "0", "-i", os.path.join(self.dir, "f_%05d.png"),
                        "-vf", "format=yuv420p", "-c:v", "libx264", "-crf", str(crf), out],
                       check=True)
        if not keep_frames:
            shutil.rmtree(self.dir, ignore_errors=True)
        return out
