#!/bin/sh
# iSH 文件完整性校验：大小优先，哈希只做抽样或按需整文件
# 用法: verify.sh <文件> [--size N] [--md5 HEX] [--sample] [--full]

usage() {
  echo "用法: verify.sh <文件> [--size 字节] [--md5 HEX] [--sample|--full]"
  echo "  默认只报大小；--sample 抽样哈希（秒级）；--full 整文件 md5"
  exit 2
}

[ $# -lt 1 ] && usage
f="$1"; shift

size_exp=""; md5_exp=""; mode="size"
while [ $# -gt 0 ]; do
  case "$1" in
    --size)   [ -z "$2" ] && usage; size_exp="$2"; shift 2 ;;
    --md5)    [ -z "$2" ] && usage; md5_exp="$2"; mode="full"; shift 2 ;;
    --sample) mode="sample"; shift ;;
    --full)   mode="full"; shift ;;
    -h|--help) usage ;;
    *) echo "未知参数: $1"; usage ;;
  esac
done

[ -f "$f" ] || { echo "✗ 文件不存在: $f"; exit 1; }

sz=$(stat -c %s "$f" 2>/dev/null)
[ -z "$sz" ] && { echo "✗ 无法读取大小（文件可能正被写入）"; exit 1; }

echo "文件: $f"
awk -v s="$sz" 'BEGIN{printf "大小: %d 字节 (%.2f GiB)\n", s, s/1073741824}'

fail=0
if [ -n "$size_exp" ]; then
  if [ "$sz" = "$size_exp" ]; then
    echo "✓ 大小精确匹配"
  else
    echo "✗ 大小不符：期望 $size_exp，差 $((sz - size_exp)) 字节"
    fail=1
  fi
fi

chunk=4194304  # 4 MiB

case "$mode" in
  sample)
    echo "--- 抽样哈希（头/中/尾各 4 MiB）---"
    if [ "$sz" -le $((chunk * 3)) ]; then
      echo "文件较小（<=12 MiB），改为整文件 md5"
      time md5sum "$f"
    else
      printf 'head  %s\n' "$(head -c $chunk "$f" | md5sum | cut -d' ' -f1)"
      printf 'mid   %s\n' "$(dd if="$f" bs=1M skip=$((sz / 2 / 1048576)) count=4 2>/dev/null | md5sum | cut -d' ' -f1)"
      printf 'tail  %s\n' "$(tail -c $chunk "$f" | md5sum | cut -d' ' -f1)"
    fi
    ;;
  full)
    est=$((sz / 1048576 / 500 + 1))
    echo "--- 整文件 md5（预计约 ${est}s，冷盘更久）---"
    got=$(md5sum "$f" | cut -d' ' -f1)
    echo "md5: $got"
    if [ -n "$md5_exp" ]; then
      exp=$(printf '%s' "$md5_exp" | tr 'A-F' 'a-f')
      if [ "$got" = "$exp" ]; then echo "✓ md5 匹配"; else echo "✗ md5 不符（期望 $exp）"; fail=1; fi
    fi
    ;;
esac

[ "$fail" -eq 0 ] && echo "=== 结论: 通过 ===" || echo "=== 结论: 不通过 ==="
exit $fail
