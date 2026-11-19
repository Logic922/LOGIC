"""模板：等质量物块 + 轻弹簧（只固定在 Q 上）的"接触 → 最大压缩 → 分离"全过程模拟。

物理设定（取 m=1, v=1, k=2, 弹簧原长 L0=4）：
    P 质量 m，初速 +v 向右；Q 质量 m，左端固定轻弹簧，初速 -2v 向左。
    ω = sqrt(2k/m) = 2
    最大压缩 t1 = π/(2ω) = 0.785s，此时 vP = vQ = -0.5v（共同速度，动量守恒）
    分离   t2 = π/ω      = 1.571s，此时 vP = -2v, vQ = +v（等质量速度交换）
    此后弹簧恢复原长、P 与弹簧脱离，不再有力 —— 弹簧绝不能被画成一直挂在 P 上。

输出：/var/minis/workspace/collision_q5.mp4
"""
import sys, math
sys.path.insert(0, "/var/minis/skills/physics-sim-video/scripts")
from simkit import *

L0, k, m, BW = 4.0, 2.0, 1.0, 0.5
om = math.sqrt(2 * k / m)
T_MAX, T_SEP = math.pi / (2 * om), math.pi / om
GROUND, W, H = 252, 960, 620


def state(t):
    """返回 (xP, xQ, vP, vQ)，单位 m 与 m/s。"""
    if t <= T_SEP:
        xcm = 2.0 - 0.5 * t
        s = L0 - 1.5 * math.sin(om * t)          # 中心距（压缩量 1.5sin ωt）
        xP, xQ = xcm - s / 2, xcm + s / 2
        vP = -0.5 + 1.5 * math.cos(om * t)
        vQ = -0.5 - 1.5 * math.cos(om * t)
    else:                                         # 分离后各自匀速，弹簧不再受拉
        xcm = 2.0 - 0.5 * T_SEP
        xP = xcm - L0 / 2 - 2.0 * (t - T_SEP)
        xQ = xcm + L0 / 2 + 1.0 * (t - T_SEP)
        vP, vQ = -2.0, 1.0
    return xP, xQ, vP, vQ


def draw(t, cam):
    xP, xQ, vP, vQ = state(t)
    img = new_frame(W, H)
    dr = ImageDraw.Draw(img)
    title_bar(dr, W, "第5题模拟：P(m, v→) 与 Q(m, 2v←) + 轻弹簧（只固定在 Q 上）")
    ground_line(dr, GROUND, W)

    # —— 弹簧：左端是自由端，长度 = min(原长, 实际间隙)；分离后停在原长被 P 甩开 ——
    xa = cam.x(xQ - BW / 2)                       # 附着点：Q 的左端
    gap = (xQ - BW / 2) - (xP + BW / 2)
    Ls = min(L0 - BW, max(gap, 0.15))
    spring(dr, xa, xa - cam.d(Ls), GROUND - 31)

    block(dr, cam, xP, BW, GROUND, "P", (52, 120, 220), "m")
    block(dr, cam, xQ, BW, GROUND, "Q", (214, 72, 72), "m")
    arrow(dr, cam.x(xP), GROUND - 92, vP, color=BLUE)
    arrow(dr, cam.x(xQ), GROUND - 92, vQ, color=RED)
    caption(dr, cam.x(xP), GROUND - 112, "vP=%+.2fv" % vP, 16, BLUE, "mm")
    caption(dr, cam.x(xQ), GROUND - 112, "vQ=%+.2fv" % vQ, 16, RED, "mm")

    if t < 1e-9:
        msg, col = "t=0：P 刚接触弹簧，系统开始相互作用", INK
    elif t < T_MAX - 1e-9:
        msg, col = "阶段①：弹簧被压缩 —— 两者都在减速", (170, 110, 0)
    elif abs(t - T_MAX) < 1e-9:
        msg, col = "t₁ 最大压缩：vP = vQ = -0.5v（共同速度）", (200, 30, 30)
    elif t < T_SEP - 1e-9:
        msg, col = "阶段②：弹簧回弹，把两者向相反方向推开", OK_GREEN
    elif abs(t - T_SEP) < 1e-9:
        msg, col = "t₂ 分离：vP = -2v, vQ = +v（速度交换完成）", (200, 30, 30)
    else:
        msg, col = "分离后：弹簧已恢复原长并与 P 脱离，此后无相互作用", (120, 60, 160)
    caption(dr, 18, 62, msg, 20, col)
    caption(dr, 18, 96, "t = %.2f s" % t, 16, GREY)

    comp = max(L0 - (xQ - xP), 0.0)
    caption(dr, W - 18, 62, "弹簧压缩量 = %.2f m" % comp, 16, GREY, "rm")
    caption(dr, W - 18, 92, "弹性势能 Ep = %.2f mv²" % (0.5 * k * comp ** 2), 14, GREY, "rm")

    vt_panel(dr, (70, 370, 600, 570), 2.6, -2.35, 1.45,
             [(lambda tt: state(tt)[2], BLUE, "P 的速度"),
              (lambda tt: state(tt)[3], RED, "Q 的速度")],
             t_cursor=t, marks=[(T_MAX, "t₁ 最大压缩"), (T_SEP, "t₂ 分离")],
             title="速度—时间图  (取 v = 1)")
    note_lines(dr, 630, 380, [
        ("初态", "vP=+1v,  vQ=-2v", INK),
        ("t₁ 最大压缩", "动量守恒 → vP=vQ=-0.5v", (200, 30, 30)),
        ("", "弹簧对 P 冲量 = -1.5mv  【对】", OK_GREEN),
        ("", "对 Q 冲量 = +1.5mv（等大反向）", INK),
        ("", "|ΔxP|=0.36m, |ΔxQ|=1.14m   【错】", BAD_RED),
        ("", "W对P=-0.375mv², W对Q=-1.875mv² 【错】", BAD_RED),
        ("", "vP=0 时 Ep=2.0 < 2.25(=最大)  【错】", BAD_RED),
        ("t₂ 分离", "vP=-2v, vQ=+1v —— 速度交换", INK),
    ])
    return img


if __name__ == "__main__":
    cam = Cam(-3.7, 5.7, 40, W - 40)
    vid = Video(fps=30)
    SLOW, T_END = 0.5, 2.6               # 0.5 倍速播放
    n = int(T_END / (SLOW / vid.fps))
    for i in range(n + 1):
        t = min(i * (SLOW / vid.fps), T_END)
        img = draw(round(t, 4), cam)
        hold = 0.45 if any(abs(t - e) < SLOW / vid.fps / 2 for e in (T_MAX, T_SEP)) else 0.0
        vid.add(img, hold=hold)
    out = vid.encode("/var/minis/workspace/collision_q5.mp4")
    print("done:", out, "frames:", vid.n)
