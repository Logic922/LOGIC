---
name: ish-multithread-download
description: 在 iSH / Minis 里多线程下载大文件（模型权重、数据集、GB 级附件）并做完整性校验。当用户说"下载这个模型""git clone 到挂载目录""加速下载/多线程下载""断点续传""下到 Models 目录"时使用。核心结论：aria2 在 iSH 上必崩（大文件 seek 失败），git lfs pull 只有 9 MB/s；正解是 curl Range 分片并发（16 路实测 28–35 MB/s），每片顺序写独立文件再 cat 合并，最后 sha256 比对。
---

# iSH 多线程分片下载

## 铁律（先看这个）

1. **不要用 aria2c**。在 iSH 上对大文件它一定失败，两条实测错误：
   - `Failed to seek the file ... cause: No error information`（lseek 到 GB 级偏移失败）
   - `Error when trying to flush write cache`
   `--disk-cache=0`、`--async-dns=false`（不去关它连 DNS 都解析不了）、`--file-allocation=none` 全都救不回来。本地盘和挂载目录**都**会崩，不是挂载的问题。
2. **不要用后台进程续命**。`nohup` / `setsid` 起的下载在下一次 `shell_execute` 之前就被杀了，日志停在某一百分比，`pgrep` 为 0。**必须在一条 `shell_execute` 里前台跑完**；下载超过工具时限就靠"分片已落盘 + 重跑同一条命令续传"来分批推进。
3. **GB 级文件先下到本地盘，再顺序 `cp` 到挂载目录**。`/var/minis/mounts/*` 写入不支持大偏移随机写（aria2 在那上面同样报 flush 错误）。`cp` 是顺序写，很快（6.9 GB 实测 12 秒）。
4. **校验用 sha256 而不是大小**（有上游哈希时）。实测 **87 秒/GB**（6.46 GB 用了 9 分 22 秒，满核）。先看 `ish-hash-verify` 技能：小文件/只需防截断时用大小判据或抽样哈希。

## 速度实测（2026-10-24，Alpine aarch64，modelscope CDN）

| 方式 | 速度 | 6.46 GB 耗时 |
|---|---|---|
| `git lfs pull`（单流） | ≈9 MB/s | ≈12 分钟 |
| aria2c 16 线程 | 32–35 MB/s，**但跑到 89% 崩** | 失败 |
| **curl Range × 16 分片** | **28–35 MB/s** | **4 分 09 秒** ✅ |
| 本地合并 `cat` + `sha256sum` | — | 9 分 22 秒（校验） |
| 本地 → 挂载目录 `cp` | — | 12 秒 |

DNS 在 iSH 里本身没问题（curl 正常），慢/失败都来自 seek 与进程存活。

## 用法

```sh
/var/minis/skills/ish-multithread-download/scripts/fetch.sh <url> <输出文件> [选项]

  -n N             并发分片数（默认 16，网络好可试 24）
  -e SHA256        期望 sha256（小写），下完自动比对
  -s SIZE          期望字节数；给了就直接按它分片，不等服务器 Content-Length
  --parts DIR      分片目录（默认 <输出>.parts，重跑即续传）
  --user-agent UA  默认 Mozilla/5.0
  --retries N      单片重试（默认 5）
  --keep-parts     合并后保留分片
  --force          目标已存在也重下
  --quiet          只输出结论
```

示例（本次任务的原型调用）：

```sh
sh fetch.sh "https://www.modelscope.cn/models/ModelE/WAI-NSFW-illustrious-SDXL/resolve/master/waiNSFWIllustrious_v90.safetensors" \
   /var/minis/workspace/dl/model.safetensors \
   -n 16 -e 178fc987b2fcfb6b08e8809f93d3eaa7d22fcfe93c9d65fd0ff1c5767fa201b1 -s 6938040682
```

然后送进挂载目录：

```sh
cp /var/minis/workspace/dl/model.safetensors "/var/minis/mounts/Models/<仓库>/<文件名>"
```

脚本行为：探测 `Range` 支持 → 不支持就自动退化成单流 `curl -C -` → 支持则按 N 片各起一个 curl（每片**从上次位置续传**，尾部用 `>>` 追加）→ 逐片核对长度 → `cat` 顺序合并 → sha256 比对 → `mv` 原子落位 → 清理分片。

## 各站直链

- **ModelScope**：`https://www.modelscope.cn/models/<ns>/<repo>/resolve/master/<file>`（302 到 `cdn-lfs-cn-1.modelscope.cn/...auth_key=...`，支持 `Range`，鉴权在跳转链接里自带）
- **HuggingFace**：`https://huggingface.co/<repo>/resolve/main/<file>?download=true`（国内慢时可换 `hf-mirror.com`）
- **GitHub Release**：`https://github.com/<o>/<r>/releases/download/<tag>/<file>`（走 objects CDN，支持 Range）
- 验证方法：`curl -s -D - -o /dev/null -L -r 0-1023 <url> | grep -i content-range`

## git 仓库形式的模型（LFS）

`git clone` 默认会拉 LFS 大文件，但 iSH 上 `git lfs pull` 又慢又容易中断。推荐流程：

```sh
cd /var/minis/mounts/Models
GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 <repo-url>      # 只拿指针与元数据，秒级
# 取到指针里的 oid 和 size
git -C <repo> cat-file -p HEAD:<file>                     # oid sha256:...  size ...
# 用 fetch.sh 下真文件（-e 用上面那个 oid），cp 到仓库目录
```

注意：真文件落位后 `git status` **会显示 ` M`**（索引里存的是指针，工作区是 6.9 GB 真文件）。这是索引状态记录，不是内容错误——**别为了它跑 `git add`**，那会触发 LFS clean 过滤器把整文件重算一遍（6.5 GB ≈ 9 分钟）。内容正确性以 `sha256 == oid` 为准。

## 挂载目录写入注意

- 目标目录可能是 File Provider 挂载，`du` 显示实际占用为 0 而 `ls` 有大小（稀疏/延迟落盘），别据此判断"没写进去"，看 `stat -c %s`。
- 抽查可用首/中/尾各 2 MiB 的 sha256 段落比对，代替整文件哈希：

```sh
for off in 0 $((SZ/2)) $((SZ-2097152)); do
  dd if="$f" bs=1M skip=$((off/1048576)) count=2 2>/dev/null | sha256sum
done
```

## 常见坑

- `disown` 在 BusyBox ash 里不存在；`(... &)` 子 shell 起的服务在**同一次调用内**可用，跨调用就没了。
- curl 的 `-C -` 只适合"从 0 恢复整文件"；分段续传要自己算 `start+已有字节`，用 `>>` 追加（脚本已实现）。
- 想要进度就别 `--quiet`，但要 `| tail` 限流，否则日志淹没上下文。
- 单片重试用尽时脚本按"缺哪些片"报错，直接重跑同一条命令即可续传，不会从头再来。
