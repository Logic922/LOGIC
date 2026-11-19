#!/bin/sh
# iSH 多线程分片下载：curl Range 并发 + 每片顺序写 + 断点续传 + 校验 + 原子合并
# 用法: fetch.sh <url> <输出文件> [-n 并发数] [-e SHA256] [-s 字节数] [--parts DIR]
#                [--user-agent UA] [--retries N] [--keep-parts] [--force] [--quiet]
set -u

usage() {
  cat <<'EOF'
用法: fetch.sh <url> <输出文件> [选项]

  -n N             并发分片数（默认 16，网络好可到 24）
  -e SHA256        期望的 sha256（小写十六进制）
  -s SIZE          期望字节数；不给则用服务器 Content-Length
  --parts DIR      分片目录（默认 <输出>.parts，可重复运行续传）
  --user-agent UA  User-Agent（默认 Mozilla/5.0）
  --retries N      单片重试次数（默认 5）
  --keep-parts     合并后保留分片
  --force          目标文件已存在也重新下载
  --quiet          只输出最终结论
  -h, --help       显示本帮助

退出码: 0 成功 / 1 失败 / 2 参数错误
EOF
  exit 2
}

[ $# -lt 2 ] && usage
url="$1"; out="$2"; shift 2

N=16; sha_exp=""; size_exp=""; parts=""; ua="Mozilla/5.0"
retries=5; keep=0; force=0; quiet=0

while [ $# -gt 0 ]; do
  case "$1" in
    -n) N="$2"; shift 2 ;;
    -e) sha_exp=$(echo "$2" | tr 'A-Z' 'a-z'); shift 2 ;;
    -s) size_exp="$2"; shift 2 ;;
    --parts) parts="$2"; shift 2 ;;
    --user-agent) ua="$2"; shift 2 ;;
    --retries) retries="$2"; shift 2 ;;
    --keep-parts) keep=1; shift ;;
    --force) force=1; shift ;;
    --quiet) quiet=1; shift ;;
    -h|--help) usage ;;
    *) echo "未知参数: $1" >&2; usage ;;
  esac
done

log() { [ "$quiet" -eq 1 ] || echo "$@"; }
die() { echo "✗ $*" >&2; exit 1; }

command -v curl >/dev/null || die "缺少 curl"
[ -n "$parts" ] || parts="${out}.parts"

have_file() { [ -f "$1" ] && stat -c %s "$1" 2>/dev/null || echo -1; }

# ---------- 已完成且可确认 → 直接收工 ----------
if [ "$force" -eq 0 ] && [ -f "$out" ]; then
  cur=$(have_file "$out")
  if [ -n "$size_exp" ] && [ "$cur" = "$size_exp" ]; then
    log "✓ 目标文件已存在且大小匹配（$cur 字节），跳过下载"
    exit 0
  fi
  if [ -z "$size_exp" ] && [ -n "$sha_exp" ]; then
    est=$(awk -v s="$cur" 'BEGIN{printf "%d", s/1073741824*87}')
    log "目标文件已存在（$cur 字节），按期望 sha256 校验（约 ${est}s）…"
    if [ "$(sha256sum "$out" | cut -d' ' -f1)" = "$sha_exp" ]; then
      log "✓ 已有文件校验通过，跳过下载"
      exit 0
    fi
    log "✗ 已有文件校验不符，重新下载"
  fi
fi

# ---------- 探测服务器能力 ----------
hdr=$(curl -sS -L --max-time 60 -D - -o /dev/null -r 0-0 -H "User-Agent: $ua" "$url" 2>/dev/null)
code=$(printf '%s' "$hdr" | tr -d '\r' | grep -E '^HTTP/' | tail -1 | awk '{print $2}')
total=$(printf '%s' "$hdr" | tr -d '\r' | grep -i '^content-range:' | tail -1 | sed -n 's|.*/||p' | tr -d ' ')
ranges=$(printf '%s' "$hdr" | tr -d '\r' | grep -ci '^accept-ranges: *bytes')

if [ "$code" != "206" ] || [ -z "$total" ] || [ "$ranges" -eq 0 ]; then
  # ---------- 单流回退 ----------
  log "⚠ 服务器不支持 Range（HTTP $code），改用单流下载（不可并行）"
  for i in $(seq 1 "$retries"); do
    curl -fsSL -C - --retry 3 --max-time 86400 -H "User-Agent: $ua" -o "$out" "$url" && break
    log "  重试 $i/$retries"
    sleep 3
  done
  [ -f "$out" ] || die "单流下载失败"
  sz=$(have_file "$out")
  [ -n "$size_exp" ] && [ "$sz" != "$size_exp" ] && die "大小不符：$sz != $size_exp"
  log "✓ 完成：$out（$sz 字节）"
  exit 0
fi

TOTAL=${size_exp:-$total}
[ "$total" != "$TOTAL" ] && log "⚠ 服务器报告 $total 字节，与期望 $TOTAL 不同（以期望为准）"

[ "$N" -gt 64 ] && N=64
CH=$(( (TOTAL + N - 1) / N ))
mkdir -p "$parts" || die "无法创建分片目录 $parts"
log "目标: $out"
log "总大小: $TOTAL 字节 ($(awk -v s="$TOTAL" 'BEGIN{printf "%.2f", s/1073741824}') GiB)  分片: $N × ~$((CH/1048576)) MiB"

# ---------- 单片下载（支持续传） ----------
fetch_part() {
  i=$1; start=$2; end=$3; want=$4; f=$5
  h=$(have_file "$f"); [ "$h" -lt 0 ] && h=0
  [ "$h" -gt "$want" ] && { rm -f "$f"; h=0; }
  [ "$h" -eq "$want" ] && return 0
  from=$(( start + h ))
  t=0
  while [ "$t" -lt "$retries" ]; do
    curl -sS -fL --max-time 7200 -H "User-Agent: $ua" \
         -r "$from-$end" "$url" >> "$f" 2>/dev/null
    now=$(have_file "$f")
    [ "$now" -eq "$want" ] && return 0
    # 部分写入时从新位置续传，而不是整片重来
    if [ "$now" -gt "$h" ] && [ "$now" -lt "$want" ]; then
      h=$now; from=$(( start + h ))
    else
      t=$((t + 1)); sleep 2
    fi
  done
  return 1
}

# ---------- 并发下载：N 个分片同时起 ----------
start_epoch=$(date +%s)
i=0
while [ "$i" -lt "$N" ]; do
  start=$(( i * CH ))
  end=$(( start + CH - 1 ))
  [ "$end" -ge "$TOTAL" ] && end=$((TOTAL - 1))
  want=$(( end - start + 1 ))
  f=$(printf '%s/p%02d' "$parts" "$i")
  fetch_part "$i" "$start" "$end" "$want" "$f" &
  i=$((i + 1))
done
fail=0
for p in $(jobs -p); do wait "$p" || fail=1; done
[ "$fail" -eq 1 ] && log "⚠ 有分片未按预期完成，下面逐片核对"

# ---------- 逐片核对 ----------
bad=""
i=0
while [ "$i" -lt "$N" ]; do
  start=$(( i * CH )); end=$(( start + CH - 1 )); [ "$end" -ge "$TOTAL" ] && end=$((TOTAL-1))
  want=$(( end - start + 1 ))
  f=$(printf '%s/p%02d' "$parts" "$i")
  [ "$(have_file "$f")" = "$want" ] || bad="$bad $i"
  i=$((i + 1))
done
[ -n "$bad" ] && die "分片不完整，缺失:$bad（重跑同一命令即可续传）"

# ---------- 合并（顺序写，规避 iSH 大文件 seek 缺陷） ----------
cat "$parts"/p* > "${out}.tmp" || die "合并失败"
sz=$(have_file "${out}.tmp")

if [ "$sz" != "$TOTAL" ]; then
  rm -f "${out}.tmp"
  die "合并后大小 $sz != $TOTAL"
fi

# ---------- 校验 ----------
if [ -n "$sha_exp" ]; then
  gb=$(awk -v s="$TOTAL" 'BEGIN{printf "%.2f", s/1073741824}')
  est=$(awk -v s="$TOTAL" 'BEGIN{printf "%d", s/1073741824*87}')
  log "校验 sha256（约 ${est}s，${gb} GiB，模拟层满核）…"
  got=$(sha256sum "${out}.tmp" | cut -d' ' -f1)
  if [ "$got" != "$sha_exp" ]; then
    rm -f "${out}.tmp"
    die "sha256 不符：期望 $sha_exp 实际 $got"
  fi
  log "✓ sha256 匹配"
fi

mv -f "${out}.tmp" "$out" || die "无法写入 $out"
[ "$keep" -eq 1 ] || rm -rf "$parts"

dur=$(( $(date +%s) - start_epoch )); [ "$dur" -le 0 ] && dur=1
awk -v s="$TOTAL" -v d="$dur" 'BEGIN{printf "✓ 完成: %d 字节, %d 秒, 平均 %.1f MiB/s\n", s, d, s/1048576/d}'
