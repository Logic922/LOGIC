---
name: math-figure
description: 在 iSH 上用 matplotlib 生成中文 + 数学公式混排的教学图（PNG）。当用户要求"配图/画个图/画出来讲/示意图"讲解数学题，或需要画圆锥曲线与焦点三角形、函数图像、立体几何示意、统计图，或要把解题步骤做成一张带公式的图时使用。内含中文字体注册、mathtext 报错对照表、标签防重叠规则，以及越界/重叠自动自检 check()。
---

# 数学制图（matplotlib · iSH）

目标：一张图讲清一件事。左边画图、右边排推导是默认版式。

## 流程

1. **先把数值算出来再画。** 参数、交点、角度、边长全部用 python 算，然后断言点在曲线上：
   ```python
   assert abs(M[0]**2/a**2 + M[1]**2/b**2 - 1) < 1e-9
   ```
   不要"看着差不多"地把点摆在曲线上 —— 一张数值错的图比没有图更糟。
2. **选版式。** 单图 → `figkit.new()`；图 + 推导 → `add_gridspec(1,2,width_ratios=[1.1,1])`，右栏 `axis('off')`，公式用 `transAxes` 坐标逐行排。
3. **渲染并自检。** `figkit.save(fig, name)` 后跑 `figkit.check(fig)`：`clip` = 文字被裁掉，`overlap` = 两个标注真撞了。改完再跑，直到输出 `check: ok`。
4. **亲眼看一遍。** 用 `read_image` 打开 PNG。自检抓不到"公式被静默降级""虚线指错对象""图例压线"这类问题。通常 2–3 轮收敛。
5. **清理。** 绘图脚本写 `/tmp/*.py`，成品写 `/var/minis/attachments/`，交付后删脚本。

## 硬规则

- **中文字体只在 `figkit.setup()` 之后生效。** 用 `figkit.new()` 会自动调用；自己 `plt.figure(...)` 建图必须先显式 `figkit.setup()`，否则中文全变豆腐块（报 `Font 'default' does not have a glyph for '\u516c'`，此时图已经存好，很容易没注意）。
- **命令参数一律带花括号**：`\sqrt{6}` 不是 `\sqrt6`，`\frac{3}{2}` 不是 `\frac32`。写错会直接抛 `ParseSyntaxException`。
- **撇号写成 `^{\prime}`**：`$O'$` 会报 `Expected named_placeable`，或干脆用裸字符串 `O′`。
- **中文放在 `$...$` 外**：`r'椭圆 $\frac{x^2}{6}+\frac{y^2}{3}=1$'` 正常；中文塞进公式里会出问题。
- **点位标签用 `offset points`**，不要用数据坐标位移：
  `ax.annotate(txt, pt, textcoords='offset points', xytext=(12,8))`
- **角弧的 width/height 是直径**，角度用 `arctan2` 算真实方向，不要凭想象填 `theta1/theta2`。
- **曲线用参数化截断**（`cosh/sinh`、`t`），解出 `y=±√…` 再画容易丢支或越界。
- 改完脚本先 `python3 -c "compile(open('f').read(),'f','exec')"` 校验，避免重复 kwarg 这类低级语法错。

## figkit（省掉字体与设置的重复劳动）

```python
import sys; sys.path.insert(0, '/var/minis/skills/math-figure/scripts')
import figkit
fig, ax = figkit.new(15, 9)        # 中文字体已注册，mathtext 走 cm
figkit.save(fig, 'q9_triangle')    # → /var/minis/attachments/q9_triangle.png
figkit.check(fig)                  # 打印越界/重叠问题，空 = ok
```

`figkit.setup(style='serif')` 可换衬线中文字体；`figkit.check(fig, overlap=0.6)` 放宽重叠阈值。

## 配色约定

主曲线 `#2f6fb0`｜次曲线虚线 `#c0392b`｜关键辅助线 `#1f6f3f`｜角度标注 `#8e44ad`｜构造/无关元素 `#7f8c8d` 点线。答案用 `#c0392b` + 浅底框。

## 参考

- 报错对照表、字体与排版细节：`references/mathtext-pitfalls.md`
- 四类可直接改的模板（解析几何+焦点三角形 / 函数图像 / 立体几何斜二测 / 统计柱状图）：`references/templates.md`
