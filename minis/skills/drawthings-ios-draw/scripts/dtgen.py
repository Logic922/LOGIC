#!/usr/bin/env python3
"""Draw Things (iOS) 出图 —— 同步阻塞，必须收到完整响应才退出。

核心：/sdapi/v1/txt2img 是同步接口，生成完才返回 {"images":[base64...]}。
客户端提前断开 = 服务端继续跑但结果丢失；上一个请求没结束时发新请求 = 两个都白跑。
所以本脚本只发一次、长超时、失败明确报错，绝不自动重试。

退出码: 0 成功 / 2 未收到响应(连接断) / 3 服务端忙(空 images) / 4 探活失败
"""
import argparse, base64, json, sys, time, urllib.request, urllib.error

BASE = "http://127.0.0.1:7860"


def probe(timeout=8):
    """返回 (ok, 耗时秒, http_code)。ok 表示服务端空闲可发。"""
    t0 = time.time()
    try:
        with urllib.request.urlopen(BASE + "/sdapi/v1/options", timeout=timeout) as r:
            r.read()
        return True, time.time() - t0, 200
    except Exception:
        return False, time.time() - t0, 0


def wait_idle(max_wait=60.0):
    """等到服务端空闲(探测 <1s 返回)为止。"""
    t0 = time.time()
    while time.time() - t0 < max_wait:
        ok, dt, _ = probe(5)
        if ok and dt < 1.0:
            return True
        time.sleep(3)
    return False


def gen(prompt, neg, out, size, steps, cfg, seed, sampler, timeout):
    payload = {
        "prompt": prompt,
        "negative_prompt": neg,
        "width": size, "height": size,
        "steps": steps, "cfg_scale": cfg, "seed": seed,
        "sampler_name": sampler, "clip_skip": 2,
        "batch_size": 1, "n_iter": 1,
    }
    req = urllib.request.Request(
        BASE + "/sdapi/v1/txt2img",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:   # 一次读到底
            body = json.loads(r.read())
    except Exception as e:
        print("未收到响应(可能已提前断开, 图已丢失): %s" % e, file=sys.stderr)
        return 2
    dt = time.time() - t0
    imgs = body.get("images") or []
    if not imgs:
        print("服务端回空 images（服务端正忙，等它空了再发）: %s" % str(body)[:200], file=sys.stderr)
        return 3
    raw = imgs[0]
    if raw.startswith("data:"):
        raw = raw.split(",", 1)[1]
    blob = base64.b64decode(raw)
    with open(out, "wb") as f:
        f.write(blob)
    print("OK %s  %d bytes  %.1fs  %dx%d %d steps seed=%s" %
          (out, len(blob), dt, size, size, steps, seed))
    return 0


def main():
    p = argparse.ArgumentParser(description="Draw Things (iOS) txt2img，同步、不重试")
    p.add_argument("prompt")
    p.add_argument("--out", required=True)
    p.add_argument("--neg", default="worst quality, low quality, normal quality, lowres, blurry, "
                                  "jpeg artifacts, bad anatomy, bad hands, extra fingers, "
                                  "watermark, signature, text, logo, oversaturated, flat shading")
    p.add_argument("--size", type=int, default=1024)
    p.add_argument("--steps", type=int, default=16)
    p.add_argument("--cfg", type=float, default=5.0)
    p.add_argument("--seed", type=int, default=-1)
    p.add_argument("--sampler", default="DPM++ 2M AYS")
    p.add_argument("--timeout", type=int, default=900, help="单个请求等待上限(秒)，别调小")
    p.add_argument("--wait-idle", action="store_true", help="发送前先等服务端空闲")
    p.add_argument("--skip-probe", action="store_true", help="跳过发送前探活")
    a = p.parse_args()

    if not a.skip_probe:
        ok, dt, code = probe()
        if not ok:
            print("探活失败: 127.0.0.1:7860 无响应 —— Draw Things 被 iOS 挂起了。\n"
                  "请让用户切到 Draw Things 一秒再切回来，然后重跑（不要重发请求）。", file=sys.stderr)
            return 4
        if dt > 1.0:
            print("服务端正忙(探测耗时 %.1fs)" % dt, file=sys.stderr)
            if a.wait_idle:
                if not wait_idle():
                    print("等待超时，服务端仍未空闲，放弃发送。", file=sys.stderr)
                    return 3
            else:
                print("未加 --wait-idle，仍尝试发送（大概率回空 images）。", file=sys.stderr)

    sys.exit(gen(a.prompt, a.neg, a.out, a.size, a.steps, a.cfg, a.seed, a.sampler, a.timeout))


if __name__ == "__main__":
    main()
