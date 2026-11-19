# 四类常用图形模板

每个模板都可直接跑（改参数即可）。统一以 `figkit` 起手：

```python
import sys; sys.path.insert(0, '/var/minis/skills/math-figure/scripts')
import figkit, numpy as np
import matplotlib.pyplot as plt
```

## 模板 A：解析几何曲线 + 焦点三角形（左图右式）

要点：先定参数并**断言公共点在曲线上**，再画；右栏用 `transAxes` 排公式链。

```python
c, a1, b1, a2, b2 = np.sqrt(3), np.sqrt(6), np.sqrt(3), np.sqrt(2), 1
M = np.array([2.0, 1.0])                      # 先算，不猜
assert abs(M[0]**2/a1**2 + M[1]**2/b1**2 - 1) < 1e-9     # 在椭圆上
assert abs(M[0]**2/a2**2 - M[1]**2/b2**2 - 1) < 1e-9     # 在双曲线上
F1, F2 = np.array([-c, 0]), np.array([c, 0])

figkit.setup()                                 # 不走 figkit.new 就必须显式 setup，否则中文变豆腐块
fig = plt.figure(figsize=(15, 8))
ax = fig.add_axes([0.045, 0.05, 0.56, 0.90])
bx = fig.add_axes([0.635, 0.06, 0.35, 0.88]); bx.axis('off')

t = np.linspace(0, 2*np.pi, 600)                      # 椭圆
ax.plot(a1*np.cos(t), b1*np.sin(t), color='#2f6fb0', lw=2.2)
tt = np.linspace(-2, 2, 500)                          # 双曲线两支（cosh/sinh 参数化）
for s in (1, -1):
    ax.plot(s*a2*np.cosh(tt), b2*np.sinh(tt), color='#c0392b', lw=2.0, ls='--')

ax.plot([F1[0], F2[0]], [0, 0], color='#111', lw=2.2)
ax.plot([F1[0], M[0]], [F1[1], M[1]], color='#1f6f3f', lw=2.6)   # r1
ax.plot([F2[0], M[0]], [F2[1], M[1]], color='#d35400', lw=2.6)   # r2
ax.plot(*M, 'o', ms=7, color='#111')
ax.annotate(r'$M$', M, textcoords='offset points', xytext=(12, 8), fontsize=16)

# 角弧：角度用 atan2 算真实方向
import matplotlib.patches as mp
th1 = np.degrees(np.arctan2(F1[1]-M[1], F1[0]-M[0]))
th2 = np.degrees(np.arctan2(F2[1]-M[1], F2[0]-M[0]))
ax.add_patch(mp.Arc(M, 1.2, 1.2, theta1=th1, theta2=th2, color='#8e44ad', lw=1.8))

ax.set_aspect('equal'); ax.set_xlim(-3.7, 4.2); ax.set_ylim(-3.2, 3.0)
ax.axhline(0, color='#999', lw=.8); ax.axvline(0, color='#999', lw=.8)

for i, s in enumerate([r'① 公共焦点：$c=\sqrt{3}$',
                       r'② 正弦定理：$\dfrac{2\sqrt{3}}{\sin\theta}=2R$',
                       r'③ 双定义 + 余弦定理 $\Rightarrow\ a_1^2+3a_2^2=12$']):
    bx.text(0, 0.95 - i*0.09, s, fontsize=16, va='top', transform=bx.transAxes)

figkit.save(fig, 'geom_demo'); figkit.check(fig)
```

## 模板 B：函数图像（渐近线 + 断点 + 定义域裁剪）

```python
fig, ax = figkit.new(10, 6.5, 130)
x = np.linspace(-6, 6, 1200)
y = 1/(x-1) + 0.5
y[np.abs(x-1) < 0.06] = np.nan                 # 断点：置 nan，别用 clip 硬连
ax.plot(x, y, color='#2f6fb0', lw=2.2)
ax.axhline(0.5, color='#7f8c8d', ls='--', lw=1.2)
ax.axvline(1, color='#7f8c8d', ls='--', lw=1.2)
ax.annotate(r'$x=1$', (1, 3.4), textcoords='offset points', xytext=(8, 0), color='#7f8c8d')
ax.annotate(r'$y=\frac{1}{x-1}+\frac{1}{2}$', (-5.6, 3.9), fontsize=17, color='#2f6fb0')
ax.set_ylim(-4, 5); ax.set_xlim(-6, 6)
figkit.save(fig, 'func_demo'); figkit.check(fig)
```

## 模板 C：立体几何示意（斜二测手绘，不用 3d 轴）

`mpl_toolkits.mplot3d` 在 iSH 上透视与标注都很别扭；示意图形优先手画投影坐标。

```python
fig, ax = figkit.new(8, 7, 130)
k = 0.5 / np.sqrt(2)                            # 斜二测：45°、长度减半
P = lambda x, y, z: (x + y*k*np.cos(np.pi/4), z + y*k*np.sin(np.pi/4))
A, B, C, D = P(0,0,0), P(4,0,0), P(4,3,0), P(0,3,0)
A1, B1, C1, D1 = P(0,0,3), P(4,0,3), P(4,3,3), P(0,3,3)
def edge(p, q, hidden=False):
    ax.plot([p[0], q[0]], [p[1], q[1]], color='#7f8c8d' if hidden else '#111',
            lw=1.6, ls='--' if hidden else '-')
for p, q in [(A,B),(B,C),(C,D),(D,A),(A,A1),(B,B1),(C,C1),(D,D1),
             (A1,B1),(B1,C1),(C1,D1),(D1,A1)]:
    edge(p, q)                                   # 12 条可见棱
edge(D1, A, True); edge(D1, C, True); edge(D1, D, True)   # 被挡住的 3 条 → 虚线
ax.set_aspect('equal'); ax.axis('off')
figkit.save(fig, 'solid_demo'); figkit.check(fig)
```

## 模板 D：数据图（中文标签 + 数值直标）

```python
fig, ax = figkit.new(11, 6, 130)
labels = ['选择', '填空', '解答', '压轴']
vals = [42, 30, 55, 18]
bars = ax.bar(labels, vals, color=['#2f6fb0', '#5b8fc9', '#8fb7d9', '#c0392b'], width=0.58)
for b, v in zip(bars, vals):
    ax.annotate(f'{v} 分', (b.get_x()+b.get_width()/2, v), textcoords='offset points',
                xytext=(0, 4), ha='center', fontsize=13)
ax.set_ylim(0, max(vals)*1.18)
ax.spines[['top', 'right']].set_visible(False)
ax.set_title('各题型失分分布')
figkit.save(fig, 'data_demo'); figkit.check(fig)
```
