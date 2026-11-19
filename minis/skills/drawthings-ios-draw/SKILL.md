---
name: drawthings-ios-draw
version: 1.0.0
description: 用 iOS 上的 Draw Things 本地 API 出图（Stable Diffusion / Illustrious SDXL）。当用户说"画一张/出张图/AI绘图/用 Draw Things 生成/生成插画/头像素材/改 prompt 再出一张"，且本机 Draw Things 已开 API Server 时使用。内含探活判据、同步请求语义、耗时基线、以及"绝不重发/绝不提前断连"的操作纪律。
---

# Draw Things (iOS) 本地出图

在 iSH 里用 `curl`/python 直接打 Draw Things 的 A1111 兼容 HTTP 接口，拿 base64 PNG。
**iSH 的 `127.0.0.1` 就是设备 loopback**，能直连 app 起的服务，不需要绕浏览器。

## 0. 一次性前置（用户手动，做错就走不通）

Draw Things → 设置 → API Server：

| 项 | 值 | 说明 |
|---|---|---|
| Server Online | 开 | |
| **协议** | **HTTP** | gRPC 模式不可用，见下 |
| IP | 0.0.0.0 | |
| **传输层安全协议** | **关** | 开 TLS 会和 gRPC 绑一起 |
| 端口 | 7860 | HTTP 模式用 7860；gRPC 模式是 7859 |

**为什么不走 gRPC**：`GenerateImage` 的 `configuration` 字段是 FlatBuffer 二进制，要 flatc 编译整套 schema，代价远大于收益。需要细节时读 `references/grpc-mode.md`。

## 1. 探活（每次出图前必做，10 秒）

```bash
curl -s -m 8 -o /dev/null -w 'code=%{http_code} t=%{time_total}\n' http://127.0.0.1:7860/sdapi/v1/options
```

| 结果 | 含义 | 动作 |
|---|---|---|
| `code=200 t=0.0x` | 空闲，可发 | 直接出图 |
| `code=200 t>` 几秒 | 正在生成 | 等它结束，**不要发新请求** |
| `code=000` | Draw Things 被 iOS 挂起（端口 closed） | 让用户切一下 Draw Things 再切回来，然后重测 |

**空闲被挂起是常态，不是配置错误。** 但**一旦开始生成，它自己会保活到任务结束**（实测 245 秒的生成全程 Minis 在前台，照样返回了图），所以不需要任何"保活"方案，只要发请求那一刻它是活的。

## 2. 出图

```bash
python3 scripts/dtgen.py "masterpiece, best quality, 1girl, cat ears, ..." \
  --out /var/minis/attachments/cat_01.png --size 1024 --steps 16 --wait-idle
```

成功输出 `OK <path> <bytes> <秒> <尺寸> ...`，退出码 0。
失败退出码：`2`=没收到响应（连接断了），`3`=服务端回空 images（忙）。

## 3. 操作纪律（血泪，违反就白跑一张 4 分钟的图）

1. **必须收到完整 HTTP 响应才停**。中途 `Ctrl-C`/超时断开 → 服务端继续算，图直接丢。所以 timeout 给 900 秒起步，别用 150 秒试探。
2. **一次只发一个请求**。上一个没结束时发第二个，会立刻返回 `{"images":[]}`，两个都白跑。
3. **`{"images":[]}` 不是报错，是"忙"**。不要据此改 prompt 或换端点；先探活，等空了再发。
4. **不要自动重试**。重试只会把队列堆起来，让局面更糟。
5. 长任务（>3 分钟）期间不要切 app 做别的事，Minis 必须留在前台等结果。

## 4. 耗时基线（实测，同一台设备）

| 尺寸 / 步数 | 耗时 | 备注 |
|---|---|---|
| 256² / 2 步 | 19 s | 大头是模型首次加载，不是采样 |
| 1024² / 16 步 | 245 s | 正式出图常用档位 |

模型加载后同尺寸会明显变快；判断"卡住"别用固定秒数，看端口是否还在、请求是否还在挂。

## 5. Prompt 惯例

当前 checkpoint 是 `wainsfwillustrious_v90_q8p.ckpt`（Illustrious 系 SDXL，动漫向）。质量词放最前：

```
masterpiece, best quality, amazing quality, very aesthetic, absurdres, 1girl, solo, ...
```

负面用脚本默认那串（worst quality / bad anatomy / watermark / text …）。
换模型先看 `GET /sdapi/v1/options` 里的 `model`、`sampler`（默认 `DPM++ 2M AYS`）、`cfg_scale`（5）、`clip_skip`（2）。
非动漫模型把质量词换掉，别硬套。

## 6. 拿到图之后

- 图存 `/var/minis/attachments/`，聊天里用 `![desc](minis://attachments/x.png)` 直接显示。
- 设成头像：`minis-config set soul.icon '"minis://attachments/x.png"'`
  **不要自己裁剪**——app 会中心裁方 + 缩到 96×96 再存，圆形显示。整图缩进圆形时脸会很小，想要大头就另出一张上身特写当源图。

## 7. 端点现状（实测 2026-10-25）

| 端点 | 结果 |
|---|---|
| `GET /sdapi/v1/options` | 200，返回完整生成配置 JSON（最有用） |
| `POST /sdapi/v1/txt2img` | 200，同步返回 `{"images":[base64]}` |
| `GET /` | 200，同 options 内容 |
| `sd-models` / `samplers` / `progress` / `queue` / `interrupt` / `png-info` | 全 404 |

没有模型列表端点 → 模型名只能从 options 里读。

## 8. 用户机器上的现状备注

- 用户明确要求：**不要连续请求**。一次一张，等结果，再问要不要下一张。
- 若用户抱怨"图没出来"，第一反应是查是不是自己断了连接，而不是重发。
