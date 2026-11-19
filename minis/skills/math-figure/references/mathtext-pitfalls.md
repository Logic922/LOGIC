# mathtext 与排版坑清单（均来自 iSH / matplotlib 3.9.3 实测）

## 1. 会直接抛异常的写法

| 写法 | 报错 | 正确写法 |
|---|---|---|
| `r"$O'$"` | `ParseSyntaxException: Expected named_placeable, found end of text` | `r"$O^{\prime}$"`，或裸字符串 `'O′'` |
| `r"$\sqrt6$"` | `ParseSyntaxException: Expected \sqrt{value}, found '6'` | `r"$\sqrt{6}$"` |
| `r"$\frac32$"` | 同型报错 | `r"$\frac{3}{2}$"`、`r"$\dfrac{3}{2}$"` |
| `r"$x\le a$"` | `ParseFatalException: Unknown symbol: \le` | 写 `\leq`（同理 `\geq`，不要用 `\ge`） |
| 同一函数调用重复 kwarg | `SyntaxError: keyword argument repeated` | 改脚本后用 `python3 -c "compile(open(f).read(),f,'exec')"` 先校验 |

**通用规则：任何命令后紧跟的单个字符都必须写成花括号形式，永远加 `{}`。**

## 2. 中英数混排

- 中文**不要**放进 `$...$` 内。一个文本对象里可以混排：`r'椭圆 $\frac{x^2}{6}+\frac{y^2}{3}=1$'` —— 中文在 `$` 外，公式在 `$` 内，渲染正常。
- `mathtext.fontset='cm'` 与 Noto/文泉驿中文搭配观感最好（已设入 `figkit`）。
- 负号要关掉 Unicode minus，否则轴刻度与公式里的减号字形不一致：`axes.unicode_minus=False`。
- 字体注册：`fm.fontManager.addfont('/usr/share/fonts/noto/NotoSansCJK-Regular.ttc')`，再用 `FontProperties(fname=...).get_name()` 取名赋给 `font.family`。直接写文件名（如 `'Noto Sans CJK SC'`）不一定生效。

## 3. 几何元素

- **角弧** `Arc(center, width, height, theta1, theta2)` 的 `width/height` 是**直径**不是半径；角度是数学正角（逆时针，逆时针从 theta1 扫到 theta2）。用 `np.degrees(np.arctan2(dy, dx))` 算真实方向，别凭想象填。
- **点必须在曲线上**：画之前用解析式断言，例如 `assert abs(x**2/a**2 + y**2/b**2 - 1) < 1e-9`。构造实例时先算参数、再算点，最后才画。
- **截断曲线**：双曲线/抛物线用参数化（`cosh/sinh`、`t`）而不是解出 `y=±...` 再画，避免开根丢支。
- 圆环角弧、虚线用 `ls=(0,(2,3))` 控制节奏，比 `'--'` 在密集图里更轻。

## 4. 文字定位（最省事的防重叠办法）

- 点位标签一律 `ax.annotate(text, point, textcoords='offset points', xytext=(dx,dy))`：位移是**屏幕点**，缩放/改范围都不会跑偏。用数据坐标位移在不同纵横向比例下会飘。
- 分栏信息块用 `transAxes` 坐标（`bx.text(0, 0.9, ..., transform=bx.transAxes)`），右栏 `bx.axis('off')`。
- 长公式块（`\dfrac`）比文字行高得多，行距按"行"平均分配会撞车 —— 高公式行单独给固定 y。
- 图例压在曲线上时，往下调 `ylim` 腾出空白，不要用 `framealpha=0.5` 硬透。

## 5. 颜色约定（本 skill 统一，便于跨图阅读）

| 用途 | 颜色 |
|---|---|
| 主曲线 / 椭圆 | `#2f6fb0` |
| 次曲线 / 双曲线 | `#c0392b`（虚线） |
| 关键辅助线、焦点连线 | `#1f6f3f` |
| 第二条辅助线 | `#d35400` |
| 角度、标注强调 | `#8e44ad` |
| 结论/答案 | `#c0392b` + 浅底框 `#fff3f0` |
| 无关紧要的构造（外接圆等） | `#7f8c8d` 点线 |

## 6. 自检 `figkit.check(fig)`

- 报 `clip` = 文本越出画布，会被裁掉。
- 报 `overlap axN` = 两个 `ax.texts` 交叠超过 45%，几乎一定是真重叠。
- 只检查 `fig.texts`、`ax.texts`、标题、轴标签、图例文字；**刻度标签不查**（会大量误报）。
- 自检通过 ≠ 好看。仍要 `read_image` 亲眼看一遍：检查公式有没有被静默降级、箭头指向对不对、图例有没有压线。
